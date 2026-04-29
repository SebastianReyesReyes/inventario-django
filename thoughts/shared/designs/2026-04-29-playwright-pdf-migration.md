# Plan: Migración xhtml2pdf → Playwright para PDFs de Actas

**Fecha:** 2026-04-29  
**Rama:** `features/playwright-pdf-migration`  
**Estado:** Diseño aprobado, pendiente implementación  
**Principios:** DRY, TDD, no romper funcionalidad existente, feature flag para revertir en segundos.

---

## 1. Problema

El motor actual `xhtml2pdf` (basado en ReportLab) tiene un parser CSS de ~2005. No soporta flexbox, grid, sombras, ni fuentes web modernas. El resultado son PDFs "cuadrados" con layout basado en `float` y tipografía rígida.

El preview HTML (`acta_preview_content.html`) ya existe y se ve excelente gracias a CSS moderno + navegador nativo. Queremos que el PDF sea idéntico a ese preview.

**Cita textual del stakeholder:**  
> *"El diseño de la acta en PDF que imprimí hoy me parece sobrecargado y no fui el único. El de la vista previa es más piola."*

---

## 2. Solución Propuesta

### 2.1 Motor: Playwright (Chromium headless)

Playwright arranca un navegador real, renderiza HTML+CSS exactamente como Chrome, y exporta a PDF vía `page.pdf()`. Soporta **todo** el CSS moderno: flexbox, grid, `box-shadow`, `border-radius`, fuentes web, SVG, `@page`, `@media print`.

### 2.2 Estrategia de Migración: Feature Flag

```
┌──────────────┐
│  ActaService  │
│  .generar_pdf()│
└──────┬───────┘
       │
       ├─ settings.PDF_ENGINE == "xhtml2pdf"  ──► _generar_pdf_xhtml2pdf()  (actual, no se toca)
       │
       └─ settings.PDF_ENGINE == "playwright" ──► _generar_pdf_playwright() (nuevo)
```

**Flag en `DJANGO_SETTINGS`:**
```python
# .env
PDF_ENGINE=xhtml2pdf  # "xhtml2pdf" | "playwright" | "both" (A/B testing)
PLAYWRIGHT_BROWSER_TIMEOUT=15000  # ms
PLAYWRIGHT_POOL_MAX_SIZE=3
```

**Ventajas del feature flag:**
- Revertir en 5 segundos cambiando la variable de entorno
- Coexistencia total: xhtml2pdf sigue funcionando como fallback
- A/B testing: `PDF_ENGINE="both"` genera ambos para comparación
- Cutover gradual: probar con un tipo de acta primero, luego todas

---

## 3. Arquitectura

### 3.1 Service Layer (`ActaPDFService`)

Nuevo servicio en `actas/services.py` (junto al `ActaService` existente):

```python
class ActaPDFService:
    """Generación de PDFs con soporte multi-engine."""

    @staticmethod
    def generar_pdf(acta, engine=None):
        """
        Punto de entrada único. Decide el motor según settings o parámetro.
        """
        engine = engine or settings.PDF_ENGINE
        if engine == "playwright":
            return ActaPDFService._generar_pdf_playwright(acta)
        elif engine == "both":
            xhtml2pdf_pdf = ActaPDFService._generar_pdf_xhtml2pdf(acta)
            playwright_pdf = ActaPDFService._generar_pdf_playwright(acta)
            return {"xhtml2pdf": xhtml2pdf_pdf, "playwright": playwright_pdf}
        else:
            return ActaPDFService._generar_pdf_xhtml2pdf(acta)

    @staticmethod
    def _generar_pdf_xhtml2pdf(acta):
        """Fallback: delega al método existente ActaService.generar_pdf()."""
        return ActaService.generar_pdf(acta)

    @staticmethod
    def _generar_pdf_playwright(acta):
        """Nuevo: genera PDF vía Playwright/Chromium."""
        from .playwright_browser import get_browser  # gestión del pool

        html = render_to_string("actas/playwright/pdf_shell.html", {
            "acta": acta,
            "asignaciones": ActaService.obtener_asignaciones_para_pdf(acta),
            "accesorios": acta.accesorios.all(),
        })
        browser = get_browser()           # pool o on-demand
        page = browser.new_page()
        page.set_content(html)
        pdf_bytes = page.pdf(
            format="Letter",
            margin={"top": "1.5cm", "bottom": "1.5cm", "left": "1.5cm", "right": "1.5cm"},
            print_background=True,         # respeta sombras y fondos
            display_header_footer=False,   # lo manejamos en el HTML
        )
        page.close()
        return pdf_bytes
```

**Observación:** `ActaPDFService` depende de `ActaService.generar_pdf()` para el fallback xhtml2pdf. No se modifica el método `generar_pdf()` existente, solo se encapsula la decisión en una capa superior.

### 3.2 Browser Pool (`actas/playwright_browser.py`)

Pool híbrido: on-demand con TTL y tamaño máximo:

```python
# actas/playwright_browser.py
import time
from playwright.sync_api import sync_playwright
from django.conf import settings

_browser_pool = []          # instancias activas
_last_used_timestamps = []  # timestamps para TTL

def get_browser():
    """Obtiene una instancia de Chromium del pool o crea una nueva."""
    TTL = getattr(settings, "PLAYWRIGHT_BROWSER_TTL", 60)  # segundos
    MAX_POOL = getattr(settings, "PLAYWRIGHT_POOL_MAX_SIZE", 3)

    # Limpiar instancias expiradas
    now = time.time()
    for i in reversed(range(len(_browser_pool))):
        if now - _last_used_timestamps[i] > TTL:
            _browser_pool[i].close()
            del _browser_pool[i]
            del _last_used_timestamps[i]

    # Reutilizar si hay disponible
    if _browser_pool:
        _last_used_timestamps[-1] = now
        return _browser_pool[-1]

    # Crear nueva
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-setuid-sandbox",
            "--font-render-hinting=none",
        ],
    )
    if len(_browser_pool) >= MAX_POOL:
        old = _browser_pool.pop(0)
        _last_used_timestamps.pop(0)
        try:
            old.close()
        except Exception:
            pass

    _browser_pool.append(browser)
    _last_used_timestamps.append(now)
    return browser
```

**Características del pool:**
- **TTL configurable**: si una instancia no se usa en N segundos, se cierra automáticamente
- **Tamaño máximo**: evita que N requests concurrentes lancen N Chromiums (memory bomb)
- **Sin estado compartido entre requests**: cada página es independiente
- **Fallback transparente**: si `get_browser()` falla, `ActaPDFService` revierte a xhtml2pdf

### 3.3 Template: Shared Body + PDF Shell

```
acta_pdf_body.html           ← contenido legal ÚNICO (ya existe)
       ├── acta_preview_content.html   ← preview HTML (ya existe, CSS responsive)
       └── playwright/pdf_shell.html   ← NUEVO: shell para Playwright PDF
```

**`playwright/pdf_shell.html`** (NUEVO):
```html
<!DOCTYPE html>
<html lang="es">
{% load acta_tags %}
{% load static %}
<head>
    <meta charset="UTF-8">
    <style>
        /* === Reset y base === */
        *, *::before, *::after { box-sizing: border-box; }

        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            font-size: 9pt;
            line-height: 1.3;
            color: #222;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }

        /* === Estilos heredados del preview (misma fuente de verdad) === */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #003594;
            padding-bottom: 12px;
            margin-bottom: 16px;
        }

        .logo { font-size: 18pt; font-weight: bold; color: #003594; }
        .logo img { max-width: 130px; }

        .acta-info { text-align: right; }
        .acta-info h1 {
            font-size: 14pt;
            margin: 0;
            color: #003594;
            text-transform: uppercase;
        }

        .clear { clear: both; }

        .section-title {
            background: #f1f3f8;
            padding: 6pt 10pt;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 8.5pt;
            margin: 14pt 0 6pt 0;
            border-left: 3pt solid #ED8B00;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10pt;
            font-size: 8pt;
        }

        table th {
            background: #003594;
            color: white;
            font-size: 7.5pt;
            padding: 6pt;
            text-transform: uppercase;
            text-align: left;
        }

        table td {
            border: 0.5pt solid #ddd;
            padding: 5pt;
            font-size: 8pt;
        }

        /* Signatures: flexbox para PDF (Playwright lo soporta) */
        .signatures {
            margin-top: 24pt;
            display: flex;
            justify-content: space-between;
            gap: 16pt;
            flex-wrap: wrap;
        }

        .signature-row {
            display: flex;
            justify-content: space-between;
            gap: 16pt;
            flex-wrap: wrap;
            width: 100%;
        }

        .signature-box {
            flex: 1;
            min-width: 120pt;
            text-align: center;
        }

        .signature-line {
            border-top: 0.5pt solid #333;
            margin-top: 28pt;
            padding-top: 4pt;
            font-size: 8pt;
        }

        /* Clauses */
        .clauses {
            font-size: 8.5pt;
            text-align: justify;
            margin-top: 12pt;
        }

        .clauses h3 {
            font-size: 9pt;
            margin-bottom: 4pt;
            color: #003594;
            border-bottom: 0.5pt solid #eee;
        }

        .clauses ol { margin-top: 3pt; padding-left: 14pt; }
        .clauses li { margin-bottom: 3pt; }

        /* Footer */
        .footer-legal {
            margin-top: 16pt;
            border-top: 0.5pt solid #ddd;
            padding-top: 8pt;
            font-size: 7pt;
            color: #888;
            text-align: center;
            font-style: italic;
        }

        .observation-box {
            font-size: 8pt;
            min-height: 30pt;
            padding: 5pt;
            border: 0.5pt solid #ccc;
            background: #fafafa;
        }

        /* Watermark (visible solo en preview, oculto en PDF) */
        .watermark { display: none; }
    </style>
</head>
<body>
    {% include "actas/partials/acta_pdf_body.html" %}
</body>
</html>
```

**Ventajas de este approach:**
- `acta_pdf_body.html` es el **único** template con contenido legal (single source of truth)
- `pdf_shell.html` define CSS pensado para impresión (flexbox, `@page`, `print-color-adjust`)
- `acta_preview_content.html` define CSS pensado para navegador (responsive, sombras, watermark)
- Ambos wrappers comparten el mismo body → misma estructura, mismas variables, mismas tablas
- Si cambiamos algo en `acta_pdf_body.html`, ambos (preview y PDF) se actualizan

---

## 4. Flujo de Datos (End-to-End)

```
Usuario click "Confirmar y Generar Acta"
        │
        ▼
POST /actas/crear/
        │
        ▼
ActaService.crear_acta()           ← persiste acta en BD
        │
        ▼
ActaPDFService.generar_pdf(acta)   ← punto de decisión
        │
    ┌───┴───┐
    │       │
xhtml2pdf  Playwright
(fallback)  │
            ▼
    get_browser() → Chromium
            │
            ▼
    render_to_string("playwright/pdf_shell.html", context)
            │
            ▼
    page.set_content(html)
    page.pdf(format="Letter", print_background=True)
            │
            ▼
        PDF bytes
    
    ┌───┴───┐
    │       │
Almacenar  Devolver como
en BD     HttpResponse
```

---

## 5. Plan de Implementación (TDD)

### Fase 1: Setup (sin tocar producción)
- [ ] Agregar `playwright` a `requirements.txt`
- [ ] Crear `actas/playwright_browser.py` con el pool
- [ ] Crear `actas/pdf_shell.html` template
- [ ] Agregar `PDF_ENGINE` setting (default `"xhtml2pdf"` para no romper nada)
- [ ] Tests unitarios de `ActaPDFService`

### Fase 2: Feature Flag (RED → GREEN)
- [ ] `test_acta_pdf_playwright_generates_pdf_content` (RED)
- [ ] `test_acta_pdf_playwright_handles_browser_crash` (RED)
- [ ] `test_acta_pdf_feature_flag_falls_back_to_xhtml2pdf` (RED)
- [ ] `ActaPDFService.generar_pdf()` con feature flag (GREEN)
- [ ] Commit checkpoint

### Fase 3: Browser Pool (RED → GREEN)
- [ ] `test_browser_pool_reuses_instance` (RED)
- [ ] `test_browser_pool_ttl_expires_instances` (RED)
- [ ] `test_browser_pool_caps_max_size` (RED)
- [ ] `get_browser()` con TTL y size cap (GREEN)
- [ ] Commit checkpoint

### Fase 4: Validación Visual
- [ ] Generar PDFs de prueba con `PDF_ENGINE="playwright"`
- [ ] Comparar con preview HTML
- [ ] Imprimir y validar contra PDF xhtml2pdf
- [ ] Ajustar CSS del shell si hay diferencias
- [ ] Commit de ajustes

### Fase 5: E2E Tests
- [ ] `test_pdf_via_playwright_matches_preview_visual`
- [ ] `test_pdf_via_playwright_persists_to_db`
- [ ] `test_pdf_feature_flag_toggle`

### Fase 6: Cleanup (opcional, post-validación)
- [ ] Cambiar `PDF_ENGINE` default a `"playwright"`
- [ ] Marcar `ActaService.generar_pdf()` como deprecated
- [ ] Eliminar `acta_pdf.html` (CSS float-based) si ya no se necesita

---

## 6. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| Playwright no disponible en entorno del usuario | Media | Alto (no genera PDF) | Feature flag revierte a xhtml2pdf automáticamente |
| Chromium consume mucha RAM | Alta | Medio (lentitud) | Pool con TTL y tamaño máximo configurable |
| Diferencias sutiles entre preview HTML y PDF | Media | Medio (legal) | Usar mismo `acta_pdf_body.html`; comparación visual con `PDF_ENGINE="both"` |
| Playwright no está en `requirements.txt` | Baja | Alto (crash al importar) | Import perezoso dentro del método, no al cargar el módulo |
| CSS de preview no funciona en `@media print` | Baja | Bajo | `pdf_shell.html` tiene estilos específicos para PDF, independientes del preview |

---

## 7. Dependencias

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `playwright` | ≥1.40 | Navegador headless para renderizar HTML → PDF |
| `chromium` (via `playwright install`) | Latest stable | Motor de renderizado |

**No se eliminan:** `xhtml2pdf`, `reportlab`, `pisa` (permanecen como fallback).

---

## 8. Configuración

```bash
# .env
PDF_ENGINE=xhtml2pdf               # "xhtml2pdf" | "playwright" | "both"
PLAYWRIGHT_BROWSER_TIMEOUT=15000   # ms timeout para page.pdf()
PLAYWRIGHT_BROWSER_TTL=120         # segundos de inactividad antes de cerrar Chromium
PLAYWRIGHT_POOL_MAX_SIZE=2         # máximo de instancias concurrentes
```

```bash
# Instalación local
pip install playwright>=1.40
playwright install chromium
```

```dockerfile
# Docker: agregar estas líneas
RUN pip install playwright>=1.40
RUN playwright install chromium --with-deps
```

---

## 9. Éxito

- [ ] Feature flag `PDF_ENGINE=playwright` genera PDFs visualmente idénticos al preview HTML
- [ ] Feature flag `PDF_ENGINE=xhtml2pdf` sigue funcionando (no rompimos nada)
- [ ] Todos los tests unitarios pasan (≥80% coverage en `actas/services.py`)
- [ ] Los tests E2E de generación de actas pasan con ambos engines
- [ ] El equipo legal valida que el nuevo PDF mantiene el contenido y estructura del anterior
- [ ] `PDF_ENGINE=both` permite comparación lado a lado para futuras iteraciones

---

*Documento generado tras brainstorming interactivo (4 ramas de exploración). Branch: `features/playwright-pdf-migration`.*
