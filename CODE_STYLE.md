# CODE_STYLE.md — Inventario JMIE

## Naming Conventions

| Category | Convention | Examples |
|----------|-----------|----------|
| **Python files** | `snake_case.py` | `test_views.py`, `services.py`, `catalog_views.py` |
| **Classes** | `PascalCase`, singular Spanish | `Dispositivo`, `TrazabilidadService`, `TestDispositivoViews` |
| **Functions / Methods** | `snake_case`, verb-first | `dispositivo_create`, `ajax_get_modelos`, `cc_toggle_activa` |
| **Variables** | `snake_case`, Spanish domain | `ultima_acta_firmada`, `esta_activo`, `identificador_interno` |
| **Models** | `PascalCase`, singular Spanish, no suffix | `HistorialAsignacion`, `BitacoraMantenimiento` |
| **URL names** | `[modelname]_[action]` (lowercase) | `dispositivo_list`, `tipodispositivo_create`, `centrocosto_toggle_activa` |
| **Templates** | `snake_case.html`, partials in `partials/` | `dispositivo_list.html`, `partials/dispositivo_list_table.html` |
| **Forms** | `[Model]Form` or `[Model]TechForm` | `DispositivoForm`, `NotebookTechForm` |
| **Factories** | `[Model]Factory` | `DispositivoFactory`, `ColaboradorFactory` |
| **Cotton components** | `snake_case.html` | `btn_primary.html`, `glass_panel.html` |

**Critical Rule**: URL names **must** follow `[modelname]_[action]` using the exact Django `model_name` in lowercase. `render_actions` (`core/templatetags/action_tags.py`) resolves buttons via `reverse(f"{app_label}:{model_name}_{action}")`. Breaking this causes `NoReverseMatch` (HTTP 500).

## File Organization

- **Organize by feature/domain**, not by type. Each app (`dispositivos/`, `actas/`, `core/`) owns its models, views, forms, templates, and tests.
- **Keep files focused**: 200–400 lines typical, 800 max. Extract services, catalog views, or helpers when a file grows.
- **Tests live in `*/tests/`** inside each app, not in a global `tests/` folder.
- **Templates**: App templates under `app/templates/app/`. Global templates (base layout, auth, errors, Cotton) under `templates/`.
- **HTMX partials**: Store in `app/templates/app/partials/`.
- **Static assets**: `static/` for project-wide assets; `media/` for user uploads.

## Import Style

Follow standard Django/Python ordering:

```python
# 1. Standard library
import os
from datetime import datetime

# 2. Third-party packages
from django.db import models, transaction
from django.shortcuts import render, redirect

# 3. Local apps (absolute imports preferred)
from core.models import TipoDispositivo
from colaboradores.models import Colaborador
```

- Use **absolute imports** within the project.
- Avoid circular imports; use lazy references (`'app.Model'`) in ForeignKeys when needed.

## Code Patterns

### Views: FBV Preferred

Function-Based Views are the default. Use explicit decorators.

```python
@login_required
@permission_required('dispositivos.add_dispositivo', raise_exception=True)
def dispositivo_create(request):
    """Vista para crear un nuevo dispositivo general o específico."""
    ...
```

CBVs are **only** used for repetitive catalog CRUD via shared bases in `core/catalog_views.py` (e.g., `CatalogCreateViewBase`).

### Service Layer

Place complex business logic (especially multi-model or atomic writes) in `services.py`, not in views.

```python
from django.db import transaction

class TrazabilidadService:
    @staticmethod
    @transaction.atomic
    def asignar(dispositivo, form, creado_por=None):
        movimiento = form.save(commit=False)
        movimiento.dispositivo = dispositivo
        movimiento.save()
        # ... update related models ...
        return movimiento, acta
```

If a secondary operation (e.g., acta generation) can fail independently, consider a **separate atomic block** so it does not rollback the primary operation.

### HTMX Response Patterns

Use helpers from `core/htmx.py`:

| Scenario | Helper | Behavior |
|----------|--------|----------|
| Mutation success | `htmx_success_or_redirect(request, url, trigger, status=204)` | HTMX → 204 + `HX-Trigger`; non-HTMX → redirect |
| Render partial | `htmx_render_or_redirect(request, template, context, url, trigger)` | HTMX → render partial + trigger; else → redirect |
| Hard redirect | `htmx_redirect_or_redirect(request, url, status=204)` | HTMX → 204 + `HX-Redirect`; else → redirect |
| Custom trigger | `htmx_trigger_response(trigger, status=204)` | Returns 204 with `HX-Trigger` header |

On successful mutations, **prefer `204 + HX-Trigger`** to refresh tables or show toasts.

### ORM Performance

- Use `select_related()` for ForeignKey / OneToOne relationships.
- Use `prefetch_related()` for reverse FK / ManyToMany.
- Define custom QuerySets with reusable methods.

```python
class DispositivoQuerySet(models.QuerySet):
    def activos(self):
        return self.exclude(estado__nombre='Fuera de Inventario')

    def con_detalles(self):
        return self.select_related(
            'estado', 'modelo', 'modelo__fabricante',
            'modelo__tipo_dispositivo', 'propietario_actual', 'centro_costo'
        )

class Dispositivo(models.Model):
    objects = DispositivoQuerySet.as_manager()
```

### Soft Delete

`Colaborador.delete()` performs logical deletion instead of physical removal to preserve historical records:

```python
def delete(self, *args, **kwargs):
    self.esta_activo = False
    self.is_active = False
    self.save()
```

## Error Handling

- **Views**: Catch `ProtectedError` and `IntegrityError` on delete/toggle operations. Return the modal HTML with the error message and an `HX-Trigger` for a toast. Do not silently return 400.
- **Forms**: Validate in `clean()` or `clean_<field>()`. Raise `ValidationError` with field-specific dicts.
- **Services**: Let exceptions propagate to views unless recovery is explicitly part of the service contract.

## Forms

All forms must inherit from `core.forms.BaseStyledForm` for Tailwind CSS consistency.

```python
from core.forms import BaseStyledForm

class DispositivoForm(BaseStyledForm):
    class Meta:
        model = Dispositivo
        fields = [...]
```

- Inject HTMX/Alpine attributes in the form’s `__init__` or widget `attrs`.
- Use `NotebookTechForm` pattern for polymorphic sub-models that only render UI fields via HTMX.

## Logging

- Use app-specific loggers. Logs are written to `inventario.log` in the project root.
- Check `inventario.log` for runtime traceability when debugging.

## Testing

### Test Structure

```python
import pytest

@pytest.mark.django_db
class TestDispositivoViews:
    def test_dispositivo_list_standard_request(self, client):
        ...

    def test_dispositivo_list_htmx_request(self, client):
        ...
```

### Conventions

- **Files**: `test_[module].py` inside each app’s `tests/` directory.
- **Classes**: `Test[Feature]`.
- **Methods**: `test_[description]` in `snake_case`, highly descriptive.
- **Factories**: Centralize shared factories in `core/tests/factories.py`. App-specific factories import from core and extend.
- **Markers**: `e2e`, `integration`, `unit`, `slow`.
- **Coverage**: `pytest.ini` runs with `--cov=. --cov-report=term-missing --reuse-db` by default.

### E2E Tests

- Use **Page Object Model** (`tests_e2e/pages/`).
- `conftest.py` sets `DJANGO_ALLOW_ASYNC_UNSAFE=true`.
- Run with: `pytest -m e2e --headed --browser chromium`.

## Do's and Don'ts

### Do

- [ ] Use `transaction.atomic()` for multi-model writes.
- [ ] Use `select_related` / `prefetch_related` in list views.
- [ ] Follow the `[modelname]_[action]` URL naming convention.
- [ ] Return `204 + HX-Trigger` on successful HTMX mutations.
- [ ] Put complex business logic in `services.py`.
- [ ] Use `BaseStyledForm` for all forms.
- [ ] Write descriptive test names and keep tests isolated.
- [ ] Use `Dispositivo.objects.con_detalles()` instead of raw queries when possible.

### Don't

- [ ] Don't put multi-model business logic directly in views.
- [ ] Don't break the URL naming convention — it breaks `render_actions`.
- [ ] Don't silently swallow `ProtectedError` / `IntegrityError` on deletes; return error UI + toast trigger.
- [ ] Don't use `*` in `ALLOWED_HOSTS` when `DEBUG=False` (settings will crash on startup).
- [ ] Don't use `DJANGO_SECRET_KEY` in `.env`; the app reads `SECRET_KEY`.
- [ ] Don't write deeply nested CBVs for standard business logic; prefer FBV.
- [ ] Don't forget to add migrations when changing models.
