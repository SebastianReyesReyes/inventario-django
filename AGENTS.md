# AGENTS.md — Inventario JMIE

## Stack
- Django 6.0.2 + HTMX + Alpine.js + Tailwind CSS (SSR, no SPA).
- SQLite local (`db.sqlite3` o ruta definida por `DB_PATH`).
- Tests: `pytest`, `pytest-django`, `factory-boy`, `pytest-playwright`.
- Componentes UI vía `django-cotton`.

## Estructura
```
inventario_jmie/   # settings, urls, wsgi
├── core/          # catálogos base, helpers HTMX, templatetags, templates base, Cotton components
├── colaboradores/ # AUTH_USER_MODEL = Colaborador
├── dispositivos/  # inventario polimórfico, mantenimientos, asignaciones, accesorios, QR
├── actas/         # actas legales, firma digital PDF (Playwright), folios
├── dashboard/     # métricas, filtros, exportación Excel/CSV, drill-down
└── suministros/   # gestión de suministros y compatibilidad con dispositivos
```

## Setup rápido (Windows)
```powershell
python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations && python manage.py migrate
python manage.py runserver
```

### ⚠️ Gotcha crítico: SECRET_KEY
- `.env.example` y la documentación referencian `DJANGO_SECRET_KEY`, pero **`settings.py` lee `SECRET_KEY`** (`os.getenv('SECRET_KEY')`).
- **Debes definir `SECRET_KEY=` en `.env`** (no `DJANGO_SECRET_KEY`). El sistema hace *fail-fast* al arrancar si está vacía, es un placeholder inseguro (`django-insecure-`, `change-me`, etc.), o si `ALLOWED_HOSTS` contiene `*` cuando `DEBUG=False`.
- Otras variables: `DEBUG`, `ALLOWED_HOSTS`, `DB_PATH` (opcional), `DATABASE_URL`.

## Comandos clave
```bash
# Tests (con coverage por defecto, ver pytest.ini)
pytest
pytest -m "not e2e"                    # excluye E2E
pytest -m e2e --headed --browser chromium
pytest path\to\test.py::test_name

# Importación masiva desde CSV
python manage.py import_devices ruta.csv --dry-run

# Docker
# Primera vez: docker compose up -d --build
# Migraciones: docker compose exec web python manage.py migrate
```

## Convenciones críticas
- **Service Layer**: lógica de negocio compleja (especialmente si toca ≥2 modelos o requiere atomicidad) va en `services.py`, no en views.
- **Transacciones**: escrituras multi-modelo dentro de `transaction.atomic()`. Si una operación secundaria (ej. generación de acta) puede fallar independientemente, usar un bloque atómico separado para no revertir la principal.
- **ORM performance**: usar `select_related()` / `prefetch_related()` en listados con relaciones. Ver `DispositivoQuerySet.con_detalles()` como patrón.
- **Soft delete de usuarios**: `Colaborador.delete()` desactiva (`esta_activo`/`is_active`), no borra la fila.
- **Logging**: loggers por app escriben a `inventario.log` en raíz. Revisar este archivo para trazabilidad.

## HTMX
- Responder con HTML parcial (no JSON para flujos de UI).
- Reutilizar helpers de `core/htmx.py` (`htmx_trigger_response`, `htmx_render_or_redirect`, `htmx_success_or_redirect`, `htmx_redirect_or_redirect`).
- En mutaciones exitosas, preferir `204 + HX-Trigger` para refrescar tabla/toast.
- Al capturar `ProtectedError` / `IntegrityError` en delete/toggle, devolver HTML del modal con error + `HX-Trigger` para toast (no silenciar con 400).

## Naming de URLs (obligatorio)
- CRUD debe seguir: **`[model_name]_[action]`** usando `model_name` real en minúsculas.
- Ejemplos válidos: `dispositivo_list`, `tipodispositivo_create`, `centrocosto_toggle_activa`.
- Esto es requerido por `core/templatetags/action_tags.py` (`reverse(f"{app_label}:{model_name}_{action}", ...)`).
- **Si no se respeta, se rompe `{% render_actions %}` con `NoReverseMatch` (Error 500).**

## Formularios
- Heredar de `core.forms.BaseStyledForm` para consistencia visual Tailwind.
- Atributos HTMX/Alpine van en el `__init__` del form/widget.

## Testing
- Usar `core/tests/factories.py` como fuente principal de datos de prueba.
- Marcadores disponibles: `e2e`, `integration`, `unit`.
- E2E usa `live_server` y `tests_e2e/pages/` (Page Object Model). `conftest.py` de E2E setea `DJANGO_ALLOW_ASYNC_UNSAFE=true`.
- `pytest.ini` incluye `--cov=. --cov-report=term-missing --reuse-db` por defecto.

## Docker / Deploy
- Piloto UAT con Docker Compose + Nginx + Gunicorn. Ver `ops/deploy/README_DEPLOY.md`.
- El contenedor corre con usuario `django` (UID 999); el directorio `data/` debe tener permisos de escritura para ese UID.

## Deviation Hotspots (Known Issues)
- `core/views.py:108-110` — Duplicate `@login_required` + `@permission_required` decorators on `ajax_modelo_create_inline`
- `inventario_jmie/urls.py:28` — Missing `namespace='core'` in `path('catalogos/', include('core.urls'))` (breaks `reverse('core:...')`)
- `dashboard/models.py` — Empty placeholder file (app has no models, uses `dispositivos.models` directly)
- `actas/models.py:116` — Stale comment referencing migrated models (incomplete refactoring artifact)

## Build / CI
- `.github/workflows/opencode.yml` — AI bot integration (non-standard CI, no test/build steps)
- `docker-compose.yml` — Contains `ALLOWED_HOSTS=*` (insecure for production), lacks migration step on startup
- No `pyproject.toml`, `setup.cfg`, `.editorconfig`, `ruff.toml`, or pre-commit config

## Test Patterns
- **Factories**: Canonical definitions in `core/tests/factories.py` with `sys.modules["pytest"]` guard
- **Specialized factories**: Preset states (`EstadoDisponibleFactory`, `EstadoAsignadoFactory`, etc.)
- **SubFactory chain**: `fabricante → modelo → dispositivo → historial`
- **E2E**: Page Object Model in `tests_e2e/pages/`, `conftest.py` sets `DJANGO_ALLOW_ASYNC_UNSAFE=true`
- **Integration tests**: Cross-app chains in `dispositivos/tests/test_integration.py`

## Complexity Hotspots
- `dispositivos/views.py` (523 lines) — 17 view functions mixing CRUD, AJAX, trazabilidad, mantenimiento; candidate for splitting
- `actas/services.py` (~400 lines) — ActaService + ActaPDFService; monitor for growth

## Referencias útiles
- `docs/dev_guide/01_tech_stack_y_entorno.md`
- `docs/dev_guide/02_patrones_y_arquitectura.md`
- `docs/dev_guide/URL_CONVENTIONS.md`
- `ops/deploy/README_DEPLOY.md`
