# Integrations Codemap

**Last Updated:** 2026-04-29
**Entry Points:** `actas/services.py`, `actas/playwright_browser.py`, `dispositivos/views.py`, `core/management/commands/import_devices.py`

## External Services

| Service | Purpose | Library | Location |
|---------|---------|---------|----------|
| **PDF Generation** | Generación de actas legales en PDF | Playwright/Chromium | `actas/services.py`, `actas/playwright_browser.py` |
| **Digital Signature** | Firma digital de PDFs | pyHanko, pypdf | `actas/services.py` |
| **QR Code** | Códigos QR para equipos | qrcode | `dispositivos/views.py` (`dispositivo_qr`) |
| **Image Processing** | Thumbnails y procesamiento de fotos | django-imagekit, Pillow | `dispositivos/models.py` (`foto_equipo`) |
| **MCP Server** | Google SecOps integration (opcional) | django-mcp-server | `settings.py` |

## PDF Generation Flow

```
ActaService.crear_acta()
    │
    ├── 1. Generar folio correlativo
    │      └── Acta.objects.aggregate(Max('folio'))
    │
    ├── 2. Crear Acta en DB
    │      └── transaction.atomic()
    │
    ├── 3. Vincular HistorialAsignacion
    │      └── asignacion.acta = acta
    │
    └── 4. Vincular EntregaAccesorio (si aplica)
           └── accesorio.acta = acta

ActaPDFService.generar_pdf(acta)
    │
    ├── 1. Obtener datos del acta + relaciones
    │
    ├── 2. Renderizar template HTML
    │      └── render_to_string('actas/playwright/pdf_wrapper.html')
    │
    ├── 3. Convertir HTML → PDF (Playwright/Chromium)
    │      └── playwright_browser.get_browser()
    │          └── page.set_content(html)
    │              └── page.pdf(format='A4')
    │
    └── 4. Retornar bytes del PDF
```

### Playwright Browser Pool

`actas/playwright_browser.py` manages a singleton pool of headless Chromium browsers:

- `get_browser()` — Returns a shared browser instance (creates one if needed).
- `shutdown_pool()` — Gracefully closes the browser pool.
- Thread-isolated: Playwright calls run in a separate thread to avoid Django's `SyncOnlyOperation`.

## QR Code Generation

```python
# dispositivos/views.py:dispositivo_qr
dispositivo.get_absolute_url() → /dispositivos/{pk}/
    │
    └── qrcode.QRCode(version=1, box_size=10, border=5)
           │
           └── img.save(buffer, format="PNG")
                  │
                  └── FileResponse(buffer, content_type="image/png")
```

## CSV Import (`import_devices`)

```
python manage.py import_devices archivo.csv [--dry-run]
    │
    ├── 1. Leer CSV con csv.DictReader
    │      └── Detecta variantes de nombres de columna
    │
    ├── 2. Normalizar datos
    │      ├── Números de serie vacíos → AUTO-XXXXXXXX
    │      ├── Genera siglas para nuevos tipos
    │      └── Valida campos requeridos
    │
    ├── 3. Crear/actualizar dispositivos
    │      └── DispositivoFactory o bulk_create
    │
    └── 4. Reportar resumen
           └── Filas creadas, actualizadas, con error
```

## MCP Server (Opcional)

```python
# settings.py - Configuración opcional para Google SecOps
# MCP_SERVER_URL=https://chronicle.us.rep.googleapis.com/mcp
# MCP_AUTH_TOKEN=your-auth-token
# MCP_PROJECT_ID=your-project-id
```

Integrado vía `django-mcp-server` para posibles integraciones de seguridad y auditoría.

## Logging Integration

```python
# Loggers configurados por app → inventario.log
LOGGING = {
    'loggers': {
        'dispositivos': {'handlers': ['file'], 'level': 'INFO'},
        'actas': {'handlers': ['file'], 'level': 'INFO'},
        'colaboradores': {'handlers': ['file'], 'level': 'INFO'},
        'core': {'handlers': ['file'], 'level': 'INFO'},
    }
}
```

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| playwright | 1.58.0 | HTML → PDF via headless Chromium |
| pyHanko | 0.33.0 | Digital PDF signing |
| pypdf | 6.7.2 | PDF manipulation & signature verification |
| qrcode | 8.2 | QR code generation |
| pillow | 12.1.1 | Image processing |
| django-imagekit | 6.1.0 | Image thumbnails |
| django-mcp-server | 0.5.7 | MCP server integration |
| openpyxl | 3.1.5 | Excel import/export |
| django-import-export | 4.4.0 | Data import/export framework |

## Related Areas

- [Backend Codemap](backend.md) - Vistas que usan estas integraciones
- [Database Codemap](database.md) - Modelos almacenados
