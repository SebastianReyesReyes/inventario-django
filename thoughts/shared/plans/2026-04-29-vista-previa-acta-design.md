# Diseño: Vista Previa de Acta

**Fecha:** 29 de Abril, 2026
**Feature:** Vista previa del documento legal antes de persistir en BD
**App:** `actas/`
**Stack:** Django 6.0.2 + HTMX + Alpine.js + Tailwind CSS + django-cotton

---

## Problema

Actualmente el flujo de creación de acta es: **Formulario modal → POST → Persistencia inmediata en BD**. No existe un paso intermedio de revisión. El usuario llena los campos, hace clic en "Emitir Acta", y el documento legal se crea instantáneamente con folio correlativo. Si cometió un error (equipo equivocado, tipo de acta incorrecto, ministro de fe mal seleccionado), debe generar una nueva acta, desperdiciando folios y ensuciando la trazabilidad legal.

**Se necesita:** Un paso de vista previa que muestre el documento legal completo (equipos, cláusulas, firmas) antes de confirmar la creación definitiva, sin escribir en BD hasta que el usuario lo apruebe explícitamente.

---

## Hallazgos del Brainstorming (5 ramas)

### 1. UX Flow → Side-Over Panel

El formulario modal se mantiene abierto en el fondo. Al hacer clic en **"Previsualizar Acta"**, se abre un **side-over** (panel lateral derecho, mismo patrón que `acta_detail_sideover.html`) que muestra el documento renderizado. El side-over contiene dos acciones:

- **"Volver a Editar"** → cierra el side-over, el modal sigue abierto con los datos intactos
- **"Confirmar y Generar Acta"** → dispara el POST real que crea el acta en BD

**Razón:** Mantiene el contexto del formulario visible, evita navegaciones de página completa, y centraliza revisión + confirmación en un solo componente. Es el mismo patrón UX que ya usa el sistema para ver detalles de acta.

### 2. Renderizado de Preview → Reutilizar `acta_pdf.html`

La vista previa **reutiliza la misma plantilla `acta_pdf.html`** que genera el PDF final, pero renderizada como HTML parcial con un flag `preview=True`. Esto garantiza **fidelidad WYSIWYG total**: lo que el usuario ve en el side-over es exactamente lo que saldrá en el PDF. Se añade una marca de agua **"PRELIMINAR"** y se ajusta el CSS para que sea legible en el ancho del side-over (~600px).

**Razón:** Single source of truth. Si alguien modifica las cláusulas legales o el formato en `acta_pdf.html`, la vista previa se actualiza automáticamente. Cero divergencia entre preview y PDF.

### 3. Display de Equipos → Tabla con subfilas anidadas

Los equipos se muestran en formato tabla (columnas: N°, ID JMIE, Tipo, Fabricante/Modelo, N° Serie, Estado), idéntico al PDF. Los accesorios vinculados a cada dispositivo se renderizan como **subfilas anidadas** con indentación y estilo diferenciado (fondo más claro, texto más pequeño).

**Razón:** Formato legalmente válido que el usuario puede revisar de un vistazo. Las subfilas anidadas hacen obvia la relación dispositivo→accesorios sin sacrificar claridad.

### 4. PDF Preview → NO generar PDF temporal

**No se genera PDF durante la vista previa.** El usuario ve solo el HTML renderizado. El PDF se genera únicamente después de confirmar y persistir el acta en BD, usando el endpoint `/actas/<pk>/pdf/` existente.

**Razón:** Evita sobrecarga del servidor (xhtml2pdf es CPU-intensive), elimina el problema de limpiar PDFs temporales descartados, y la fidelidad HTML→PDF de xhtml2pdf es suficientemente alta como para confiar en la previsualización HTML.

### 5. Data Flow → HTMX POST dual-path

El formulario modal tendrá **dos rutas de submit** diferenciadas por el botón presionado:

| Botón | Método | Endpoint | Respuesta |
|-------|--------|----------|-----------|
| "Previsualizar Acta" | POST | `/actas/preview/` | HTML del side-over con el acta renderizada |
| "Confirmar y Generar Acta" | POST | `/actas/crear/` | 204 + `HX-Trigger: actaCreated` |

Ambos envían los mismos datos del formulario (colaborador, tipo_acta, asignaciones[], accesorios[], observaciones, ministro_de_fe). La diferencia es que `preview/` **no persiste en BD** — solo construye el contexto, consulta los equipos seleccionados, y renderiza el template.

**Razón:** Patrón HTMX natural. Sin estado en cliente ni sesión. Sin dependencias nuevas. El form sigue siendo un form HTML estándar con `hx-post`.

---

## Recomendación: Arquitectura Final

### Flujo completo

```
┌──────────────────────────────────────────────────────────────────┐
│  MODAL (acta_crear_modal.html)                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Formulario: Colaborador, Tipo, Equipos ✓, Observaciones   │  │
│  │                                                            │  │
│  │ [Cancelar]  [Previsualizar Acta]  ← NUEVO BOTÓN           │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─────────────── SIDE-OVER (acta_preview_sideover.html) ──────┐ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │              *** PRELIMINAR ***                         │ │ │
│  │  │  ACTA DE ENTREGA            Folio: ACT-2026-XXXX       │ │ │
│  │  │  ────────────────────────────────────────────────────  │ │ │
│  │  │  Colaborador: Juan Pérez R.   RUT: 12.345.678-9       │ │ │
│  │  │  Cargo: Operador              Obra: Faena Norte        │ │ │
│  │  │  ────────────────────────────────────────────────────  │ │ │
│  │  │  DETALLE DE ACTIVOS TI                                  │ │ │
│  │  │  ┌────┬──────────┬──────────┬──────────┬──────────┐    │ │ │
│  │  │  │ N° │ ID JMIE  │ Tipo     │ Fab/Mod  │ Serie    │    │ │ │
│  │  │  ├────┼──────────┼──────────┼──────────┼──────────┤    │ │ │
│  │  │  │ 1  │ JMIE-NB… │ Notebook │ Dell/Lat │ ABC123   │    │ │ │
│  │  │  │    │  └ Cargador 65W (accesorio)               │    │ │ │
│  │  │  │    │  └ Mouse Logitech (accesorio)             │    │ │ │
│  │  │  │ 2  │ JMIE-SM… │ Smartph. │ Samsung/…│ XYZ789   │    │ │ │
│  │  │  └────┴──────────┴──────────┴──────────┴──────────┘    │ │ │
│  │  │  ────────────────────────────────────────────────────  │ │ │
│  │  │  CLÁUSULAS LEGALES (Ley 21.663, prohibiciones...)      │ │ │
│  │  │  ────────────────────────────────────────────────────  │ │ │
│  │  │  FIRMAS: Responsable TI | Recibí Conforme | M. de Fe  │ │ │
│  │  │  ────────────────────────────────────────────────────  │ │ │
│  │  │  Folio: ACT-2026-XXXX                                  │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  │                                                              │ │
│  │  [⬅ Volver a Editar]    [✅ Confirmar y Generar Acta]       │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Archivos a crear/modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `actas/views.py` | **Modificar** | Agregar `acta_preview()`. Modificar `acta_create()` para aceptar flag de confirmación. |
| `actas/urls.py` | **Modificar** | Agregar `path('preview/', views.acta_preview, name='acta_preview')` |
| `actas/services.py` | **Modificar** | Agregar `ActaService.preparar_contexto_preview()` que construye el context dict sin guardar en BD |
| `actas/templates/actas/partials/acta_crear_modal.html` | **Modificar** | Reemplazar el botón "Emitir Acta" por "Previsualizar Acta" con `hx-post` a `/actas/preview/`. Agregar contenedor `#preview-sideover` para el side-over. |
| `actas/templates/actas/partials/acta_preview_sideover.html` | **Crear** | Side-over Alpine.js que recibe el HTML del preview. Contiene botones "Volver a Editar" y "Confirmar y Generar Acta". |
| `actas/templates/actas/partials/acta_pdf.html` | **Modificar** | Agregar bloque condicional `{% if preview %}` para: (1) watermark "PRELIMINAR", (2) folio pendiente, (3) CSS responsive para side-over |
| `actas/templates/actas/partials/acta_preview_content.html` | **Crear** | Wrapper que incluye `acta_pdf.html` con `preview=True` y adapta estilos para el side-over |

### Nuevo endpoint: `acta_preview`

```python
# actas/views.py

@login_required
@permission_required('actas.add_acta', raise_exception=True)
def acta_preview(request):
    """
    Genera la vista previa HTML de un acta sin persistir en BD.
    Recibe los mismos datos que acta_create pero solo renderiza.
    """
    if request.method != 'POST':
        return HttpResponse("Método no permitido", status=405)
    
    form = ActaCrearForm(request.POST)
    asignacion_ids = request.POST.getlist('asignaciones')
    accesorio_ids = request.POST.getlist('accesorios')
    
    if not form.is_valid():
        error_html = _render_acta_error("Corrija los errores del formulario antes de previsualizar.")
        return HttpResponse(error_html)
    
    try:
        preview_html = ActaService.generar_preview_html(
            colaborador=form.cleaned_data['colaborador'],
            tipo_acta=form.cleaned_data['tipo_acta'],
            asignacion_ids=asignacion_ids,
            accesorio_ids=accesorio_ids,
            creado_por=request.user,
            observaciones=form.cleaned_data.get('observaciones'),
            ministro_de_fe=form.cleaned_data.get('ministro_de_fe'),
        )
        
        return render(request, 'actas/partials/acta_preview_sideover.html', {
            'preview_html': preview_html,
            'form_data': request.POST,  # Para reenviar en la confirmación
        })
        
    except ValidationError as e:
        error_html = _render_acta_error(str(e))
        return HttpResponse(error_html)
```

### Nuevo método en `ActaService`

```python
# actas/services.py

@staticmethod
def generar_preview_html(colaborador, tipo_acta, asignacion_ids, creado_por, 
                          observaciones=None, accesorio_ids=None, ministro_de_fe=None):
    """
    Construye el contexto completo para renderizar la vista previa del acta
    SIN persistir en base de datos.
    
    Returns:
        str: HTML renderizado del acta en modo preview.
    """
    if not asignacion_ids:
        raise ValidationError("Debe seleccionar al menos una asignación.")
    
    # Consultar los equipos seleccionados (misma query que para PDF)
    from dispositivos.models import HistorialAsignacion, EntregaAccesorio
    
    asignaciones = HistorialAsignacion.objects.filter(
        pk__in=asignacion_ids,
        colaborador=colaborador,
        acta__isnull=True,
    ).select_related(
        'dispositivo__modelo__tipo_dispositivo',
        'dispositivo__modelo__fabricante',
        'dispositivo__modelo',
    )
    
    if not asignaciones.exists():
        raise ValidationError(
            "Las asignaciones seleccionadas ya no están disponibles "
            "o no pertenecen al colaborador."
        )
    
    accesorios = []
    if accesorio_ids:
        accesorios = list(EntregaAccesorio.objects.filter(
            pk__in=accesorio_ids,
            colaborador=colaborador,
            acta__isnull=True
        ))
    
    # Construir un "acta fantasma" (unsaved) para el template
    from .models import Acta
    acta_preview = Acta(
        colaborador=colaborador,
        tipo_acta=tipo_acta,
        creado_por=creado_por,
        observaciones=observaciones or '',
        ministro_de_fe=ministro_de_fe,
        fecha=timezone.now(),
    )
    # Folio tentativo (no es el real, solo para preview visual)
    acta_preview.folio = f"ACT-{timezone.now().year}-PENDIENTE"
    
    logo_path = finders.find('img/LogoColor.png')
    
    context = {
        'acta': acta_preview,
        'asignaciones': asignaciones,
        'accesorios': accesorios,
        'logo_path': logo_path,
        'fecha_actual': timezone.now(),
        'preview': True,  # Flag para el template
    }
    
    return render_to_string('actas/partials/acta_preview_content.html', context)
```

### Modificaciones en el template PDF

```django
{# actas/partials/acta_pdf.html — agregar al inicio del body #}
{% if preview %}
<div style="position: fixed; top: 40%; left: 0; width: 100%; text-align: center; 
            opacity: 0.06; font-size: 60pt; font-weight: bold; color: #999;
            transform: rotate(-15deg); z-index: 0; pointer-events: none;">
    PRELIMINAR
</div>
{% endif %}
```

### Template del side-over de preview

```django
{# actas/partials/acta_preview_sideover.html — NUEVO #}
<div x-data="{ open: true }"
     x-show="open"
     x-cloak
     @keydown.escape.window="open = false; setTimeout(() => $el.remove(), 300)"
     class="fixed inset-0 z-[60] flex justify-end">

    <!-- Backdrop -->
    <div class="absolute inset-0 bg-background/60 backdrop-blur-sm"
         @click="open = false; setTimeout(() => $el.remove(), 300)"></div>

    <!-- Side-Over Panel -->
    <div x-show="open"
         x-transition:enter="transition ease-out duration-300"
         x-transition:enter-start="translate-x-full"
         x-transition:enter-end="translate-x-0"
         class="relative w-full max-w-2xl h-full bg-surface-container border-l border-white/10 
                shadow-[-20px_0_50px_rgba(0,0,0,0.5)] overflow-y-auto custom-scrollbar">

        <!-- Header -->
        <div class="sticky top-0 z-10 bg-surface-container/95 backdrop-blur-md p-6 
                    border-b border-white/10 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-jmie-blue/10 flex items-center justify-center">
                    <span class="material-symbols-outlined text-jmie-blue">preview</span>
                </div>
                <div>
                    <h3 class="text-lg font-black uppercase tracking-tight">Vista Previa del Acta</h3>
                    <p class="text-[10px] text-amber-400 font-bold uppercase tracking-widest">
                        ⚠ Documento Preliminar — No tiene validez legal
                    </p>
                </div>
            </div>
            <button @click="open = false; setTimeout(() => $el.remove(), 300)"
                    class="text-jmie-gray hover:text-on-background transition-colors">
                <span class="material-symbols-outlined">close</span>
            </button>
        </div>

        <!-- Preview Content -->
        <div class="p-6">
            {{ preview_html|safe }}
        </div>

        <!-- Footer Actions (sticky) -->
        <div class="sticky bottom-0 bg-surface-container/95 backdrop-blur-md p-6 
                    border-t border-white/10 flex items-center justify-between">
            <button @click="open = false; setTimeout(() => $el.remove(), 300)"
                    class="px-6 py-2.5 text-xs font-black uppercase tracking-widest 
                           text-jmie-gray hover:text-on-background border border-white/10 
                           rounded-xl hover:bg-white/5 transition-all flex items-center gap-2">
                <span class="material-symbols-outlined text-sm">arrow_back</span>
                Volver a Editar
            </button>

            <form hx-post="{% url 'actas:acta_create' %}"
                  hx-target="closest .fixed.inset-0.z-50"
                  hx-swap="outerHTML">
                {% csrf_token %}
                {# Reenviar todos los campos del form original como hidden #}
                {% for key, values in form_data.lists %}
                    {% for value in values %}
                        <input type="hidden" name="{{ key }}" value="{{ value }}">
                    {% endfor %}
                {% endfor %}
                <input type="hidden" name="confirmado" value="true">

                <button type="submit"
                        class="px-8 py-2.5 bg-jmie-blue text-white text-xs font-black 
                               uppercase tracking-widest rounded-xl hover:brightness-110 
                               shadow-[0_10px_30px_rgba(0,53,148,0.3)] transition-all 
                               flex items-center gap-2">
                    <span class="material-symbols-outlined text-sm">check_circle</span>
                    Confirmar y Generar Acta
                </button>
            </form>
        </div>
    </div>
</div>
```

### Modificaciones en `acta_crear_modal.html`

El cambio clave es transformar el form de `hx-post="{% url 'actas:acta_create' %}"` a tener **dos botones con diferentes hx-post**:

```html
<!-- El form ya no hace submit directo; los botones definen su propio hx-post -->
<form id="acta-form"
      class="space-y-6">
    {% csrf_token %}
    <!-- ... campos del formulario (sin cambios) ... -->

    <div class="pt-6 border-t border-white/5 flex items-center justify-between">
        <div id="form-indicator" class="htmx-indicator ...">
            <!-- spinner -->
        </div>
        
        <div class="flex gap-3 ml-auto">
            <button type="button" @click="open = false; ..."
                    class="...">Cancelar</button>
            
            <!-- NUEVO: Botón de Previsualizar -->
            <button type="button"
                    hx-post="{% url 'actas:acta_preview' %}"
                    hx-include="#acta-form"
                    hx-target="#preview-sideover-container"
                    hx-swap="innerHTML"
                    hx-indicator="#form-indicator"
                    class="px-8 py-2.5 bg-amber-500 text-white text-xs font-black 
                           uppercase tracking-widest rounded-xl hover:brightness-110 
                           shadow-[0_10px_30px_rgba(245,158,11,0.2)] transition-all 
                           flex items-center gap-2">
                <span class="material-symbols-outlined text-sm">preview</span>
                Previsualizar Acta
            </button>
        </div>
    </div>
</form>

<!-- Contenedor donde se inyecta el side-over de preview -->
<div id="preview-sideover-container"></div>
```

---

## Plan de Implementación

### Fase 1: Backend (sin romper nada)
1. Agregar `ActaService.generar_preview_html()` en `services.py`
2. Agregar `acta_preview()` view en `views.py`
3. Agregar URL `acta_preview` en `urls.py`
4. Modificar `acta_pdf.html` con bloque `{% if preview %}`

### Fase 2: Templates
5. Crear `acta_preview_content.html` (wrapper que incluye el template PDF)
6. Crear `acta_preview_sideover.html` (panel Alpine.js)

### Fase 3: Integración en el modal
7. Modificar `acta_crear_modal.html`: reemplazar botón "Emitir Acta" por "Previsualizar Acta"
8. Agregar contenedor `#preview-sideover-container`

### Fase 4: Tests
9. Tests unitarios para `generar_preview_html()` — validar que no persiste, que levanta ValidationError sin asignaciones
10. Tests de integración para endpoint `acta_preview` — validar respuestas HTML, errores de formulario
11. Tests E2E con Playwright: flujo completo modal → preview → confirmar

---

## Decisiones de Diseño Clave

| Decisión | Alternativas consideradas | Justificación |
|----------|--------------------------|---------------|
| Side-over en vez de modal step-2 | Modal multi-paso, página completa | Mantiene el formulario visible; mismo patrón que `acta_detail_sideover.html`; mejor UX para revisar documentos largos |
| Reutilizar `acta_pdf.html` en vez de template nuevo | Template separado para preview | Single source of truth; cualquier cambio legal en el PDF se refleja automáticamente en el preview |
| Sin PDF temporal | Generar PDF en preview | Menor carga del servidor; sin archivos huérfanos; la fidelidad HTML→PDF de xhtml2pdf es suficiente |
| HTMX POST dual-path en vez de sesión | django session, django-formtools | Sin estado en servidor; sin dependencias nuevas; patrón HTMX idiomático |
| Tabla con subfilas anidadas para accesorios | Cards, secciones expandibles | Formato legalmente más claro; igual al PDF; visibilidad completa de un vistazo |

---

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| El folio "PENDIENTE" en preview puede confundir | Mostrar claramente "PRELIMINAR" en watermark + alerta ámbar en header del side-over |
| Las asignaciones pueden ser tomadas por otro usuario entre preview y confirmación | `acta_create` ya valida `acta__isnull=True` — si ya no están disponibles, muestra error |
| El template `acta_pdf.html` usa CSS de impresión que se ve mal en side-over | El wrapper `acta_preview_content.html` sobreescribe estilos clave (ancho de tabla, fuentes) para el viewport |
| Muchos equipos → side-over muy largo | El side-over ya tiene `overflow-y-auto`; se puede agregar un contador "X equipos, Y accesorios" en el header |

---

*Documento generado a partir de sesión de brainstorming con 5 ramas de exploración.*
*Próximo paso: Iniciar implementación siguiendo el plan de 4 fases.*
