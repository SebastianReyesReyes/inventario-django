# CODE_STYLE.md — Inventario JMIE

## Naming Conventions

### Files
- **Python modules**: `snake_case` — `dispositivos/views.py`, `core/services.py`, `test_models.py`
- **Templates**: `snake_case` — `dispositivo_list.html`, `mantenimiento_form_modal.html`
- **Partials HTMX**: prefijo descriptivo — `*_form_modal.html`, `*_success.html`, `*_detail_sideover.html`, `*_list_table.html`
- **Cotton components**: `snake_case` — `btn_primary.html`, `glass_panel.html`
- **Management commands**: `snake_case` — `import_devices.py`, `seed_cc.py`

### Classes
- **Models**: `PascalCase`, **siempre singular**, español — `Dispositivo`, `BitacoraMantenimiento`, `HistorialAsignacion`
- **Forms**: `[Model]Form` o `[Model]TechForm` — `DispositivoForm`, `NotebookTechForm`
- **Services**: `[Domain]Service` — `TrazabilidadService`, `ActaService`
- **Factories**: `[Model]Factory` — `DispositivoFactory`, `ColaboradorFactory`
- **QuerySets**: `[Model]QuerySet` — `DispositivoQuerySet`
- **Tests**: `Test` + `PascalCase` — `TestDispositivoViews`, `TestTrazabilidadService`

### Functions / Methods
- **Vistas**: `[modelo]_[accion]` — `dispositivo_create`, `dispositivo_asignar`, `cc_toggle_activa`
- **AJAX helpers**: `ajax_[verbo]_[sustantivo]` — `ajax_get_modelos`, `ajax_crear_modelo`
- **Tests**: `test_[descripcion]` — `test_asignar_post_htmx_crea_acta`
- **Privados**: `_prefijo` — `_get_value`, `_normalize_string`

### Variables
- `snake_case`, español para dominio, inglés para técnico
- QuerySets: plural — `dispositivos`, `modelos`, `accesorios`
- Instancias: singular — `dispositivo`, `colaborador`, `acta`
- Booleanos: participio/adjetivo — `firmada`, `activa`, `esta_activo`, `cambio_estado_automatico`

### URLs (Convención Crítica)
**Obligatorio**: `[model_name]_[action]` en minúsculas, usando `model_name` real del modelo.

```python
# Correcto
dispositivo_list, dispositivo_create, dispositivo_update
tipodispositivo_create, tipodispositivo_delete
centrocosto_toggle_activa

# Incorrecto — rompe {% render_actions %} con NoReverseMatch
tipo_create        # Modelo es TipoDispositivo
estado_edit        # Debe ser _update
cc_list            # Modelo es CentroCosto
```

### Model Fields & Related Names
- **Campos**: `snake_case`, español — `identificador_interno`, `fecha_compra`, `propietario_actual`
- **related_name**: plural descriptivo en español — `equipos_asignados`, `asignaciones_registradas`, `mantenimientos`
- **Meta**: siempre definir `verbose_name` y `verbose_name_plural` en español

## File Organization

### Django App Standard
```
{app}/
├── models.py           # Dominio + Meta
├── views.py            # FBVs principales (HTMX-aware)
├── urls.py             # URLconf con app_name
├── forms.py            # Heredan de BaseStyledForm
├── services.py         # Lógica de negocio transaccional
├── signals.py          # Señales (opcional)
├── filters.py          # django-filter (opcional)
├── admin.py            # Config admin
├── tests/
│   ├── factories.py    # Si aplica
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_services.py
│   └── test_integration.py
├── templates/{app}/
│   ├── {model}_list.html
│   ├── {model}_form.html
│   ├── {model}_detail.html
│   └── partials/
└── templatetags/       # Si aplica
```

### Templates
```
templates/
├── base.html                    # Layout global (HTMX containers)
├── {app}/
│   ├── partials/               # HTMX partials
│   └── ...
└── cotton/
    ├── btn_primary.html
    ├── empty_state.html
    ├── glass_panel.html
    ├── page_header.html
    ├── search_input.html
    └── th_sort.html
```

## Import Style

### Orden de imports
```python
# 1. stdlib
import json
import io
from datetime import date

# 2. Django
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction, IntegrityError
from django.contrib.auth.decorators import login_required, permission_required

# 3. Third-party
from constance import config
from dashboard.filters import AnaliticaInventarioFilter

# 4. Local apps (de más genérico a más específico)
from core.models import TipoDispositivo, EstadoDispositivo
from colaboradores.models import Colaborador
from .models import Dispositivo, HistorialAsignacion
from .forms import AsignacionForm, ReasignacionForm
from .services import DispositivoFactory, TrazabilidadService
from core.htmx import htmx_render_or_redirect, is_htmx
```

## Code Patterns

### Service Layer (Obligatorio para multi-modelo)
```python
# views.py — delegar a servicio
from .services import TrazabilidadService

@login_required
@permission_required('dispositivos.add_historialasignacion', raise_exception=True)
def dispositivo_asignar(request, pk):
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    if request.method == 'POST':
        form = AsignacionForm(request.POST)
        if form.is_valid():
            creado_por = getattr(request.user, 'colaborador', None)
            movimiento, acta = TrazabilidadService.asignar(dispositivo, form, creado_por=creado_por)
            return htmx_render_or_redirect(...)
    else:
        form = AsignacionForm()
    return render(request, 'dispositivos/partials/asignacion_form_modal.html', {...})
```

### Transacciones Anidadas (Aislamiento de fallos)
```python
def dispositivo_create(request):
    if form.is_valid():
        # Bloque 1: operación principal
        with transaction.atomic():
            dispositivo = form.save()

        # Bloque 2: operación secundaria que puede fallar
        if form.cleaned_data.get('generar_acta') and dispositivo.propietario_actual:
            with transaction.atomic():
                acta = ActaService.crear_acta(...)
```

### ORM Performance
```python
# Listados: siempre select_related / prefetch_related
dispositivos = Dispositivo.objects.select_related(
    'estado', 'modelo', 'modelo__fabricante', 'modelo__tipo_dispositivo',
    'propietario_actual', 'centro_costo'
)

# Patrón: custom QuerySet con métodos reutilizables
class DispositivoQuerySet(models.QuerySet):
    def activos(self):
        return self.exclude(estado__nombre='Fuera de Inventario')

    def con_detalles(self):
        return self.select_related(...)
```

### HTMX Response Patterns
```python
from core.htmx import (
    htmx_trigger_response,      # 204 + HX-Trigger
    htmx_render_or_redirect,    # Render partial o redirect
    htmx_success_or_redirect,   # 204 + trigger o redirect
    htmx_redirect_or_redirect,  # HX-Redirect o redirect
    is_htmx,                    # Detectar request HTMX
)

# Mutación exitosa: 204 + trigger para refrescar tabla/toast
def cc_toggle_activa(request, pk):
    cc = get_object_or_404(CentroCosto, pk=pk)
    cc.activa = not cc.activa
    cc.save()
    return htmx_trigger_response({"ccListChanged": True, "showNotification": "..."})

# Error en delete: devolver modal con error + trigger toast
try:
    dispositivo.delete()
    return htmx_redirect_or_redirect(request, redirect_url=reverse('...'))
except (ProtectedError, IntegrityError):
    response = render(request, 'dispositivos/partials/dispositivo_confirm_delete.html',
                      {'dispositivo': dispositivo, 'error': error_msg})
    response['HX-Trigger'] = json.dumps({'show-notification': {'value': error_msg}})
    return response
```

### Forms con Tailwind
```python
from core.forms import BaseStyledForm

class MiModeloForm(BaseStyledForm):
    class Meta:
        model = MiModelo
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ejemplo...'}),
        }
```

## Error Handling

### En Vistas
- Usar `get_object_or_404()` para lookups por PK
- Capturar `ProtectedError` / `IntegrityError` en deletes para mostrar mensaje amigable
- No silenciar errores con 400 genéricos en HTMX: devolver HTML del modal con error

### En Servicios
- Levantar excepciones del ORM o `ValidationError` para casos de negocio inválidos
- Nunca capturar silenciosamente; dejar que la vista decida cómo presentar el error

### En Modelos
- `clean()` para validaciones cross-field
- `save()` para lógica de generación automática (folios, identificadores)

## Logging

```python
import logging
logger = logging.getLogger(__name__)

# Usar levels apropiados
logger.info("Equipo %s asignado a %s", dispositivo.identificador_interno, colaborador)
logger.warning("Intento de modificación de acta firmada: %s", acta.folio)
logger.error("Error al generar PDF del acta %s", acta.folio, exc_info=True)
```

- Evitar `print()`; todo logging va a `inventario.log`
- Cada app tiene su logger configurado en `settings.LOGGING`

## Testing

### Marcadores pytest
```python
import pytest

@pytest.mark.unit
def test_model_str():
    ...

@pytest.mark.integration
def test_service_asignar_crea_historial():
    ...

@pytest.mark.e2e
def test_inventory_flow(page):
    ...
```

### Factories
```python
# Usar core/tests/factories.py (o app/tests/factories.py) como fuente principal
from core.tests.factories import DispositivoFactory, ColaboradorFactory

def test_asignacion(client):
    dispositivo = DispositivoFactory()
    colaborador = ColaboradorFactory()
    ...
```

### E2E (Page Object Model)
```python
# tests_e2e/pages/inventory_pages.py
class InventoryPage:
    def __init__(self, page):
        self.page = page

    def search_device(self, query):
        self.page.fill('[name="q"]', query)
        self.page.press('[name="q"]', 'Enter')
```

## Do's and Don'ts

### Do
- [ ] Delegar lógica multi-modelo a `services.py`
- [ ] Usar `transaction.atomic()` para escrituras multi-modelo
- [ ] Usar `select_related()` / `prefetch_related()` en listados
- [ ] Seguir la convención `[model_name]_[action]` para URLs
- [ ] Heredar de `BaseStyledForm` para consistencia visual
- [ ] Responder HTML parcial en flujos HTMX (no JSON)
- [ ] Usar `htmx_trigger_response` con `204` en mutaciones exitosas
- [ ] Implementar soft-delete en modelos con historial legal
- [ ] Forzar formato `YYYY-MM-DD` en widgets de fecha: `forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})`
- [ ] Definir `Meta.verbose_name` y `verbose_name_plural` en español

### Don't
- [ ] **NO** escribir lógica de negocio compleja directamente en views
- [ ] **NO** revertir la operación principal si falla una operación secundaria (usar bloques atómicos separados)
- [ ] **NO** usar `tipo_create` cuando el modelo es `TipoDispositivo` (rompe `render_actions`)
- [ ] **NO** silenciar `ProtectedError` / `IntegrityError` con 400 genérico en HTMX
- [ ] **NO** usar `DJANGO_SECRET_KEY` en `.env`; usar `SECRET_KEY` (así lo lee `settings.py`)
- [ ] **NO** mutar objetos en lugar de crear nuevos (patrón inmutabilidad donde aplique)
- [ ] **NO** dejar `DEBUG=True` en producción ni usar `ALLOWED_HOSTS=['*']` con `DEBUG=False`
- [ ] **NO** usar `print()` para debug; usar `logging.getLogger(__name__)`
