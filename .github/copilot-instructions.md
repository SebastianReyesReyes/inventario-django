# Copilot Instructions for `inventario-django`

## Build, test, and lint commands

```powershell
# Environment setup
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# DB setup / updates
python manage.py makemigrations
python manage.py migrate

# Run app
python manage.py runserver
```

```powershell
# Full test suite (pytest.ini already enables coverage and reuse-db)
pytest

# Fast suite without browser E2E
pytest -m "not e2e"

# E2E suite (Playwright)
pytest tests_e2e\ -m e2e --headed --browser chromium

# Run a single test (unit/integration/E2E)
pytest path\to\test_file.py::test_name
```

No dedicated lint command is configured in repository config files (`pyproject.toml`, `setup.cfg`, `tox.ini`, `.flake8`, `ruff.toml` are absent).

## High-level architecture

- Django project is split by domain apps: `core` (catalogs + base views), `colaboradores` (custom user model), `dispositivos` (inventory + traceability), `actas` (legal handoff/return documents), `dashboard` (analytics/export).
- `inventario_jmie/settings.py` configures `AUTH_USER_MODEL = 'colaboradores.Colaborador'`; `inventario_jmie/urls.py` mounts all app routes and Django auth login/logout.
- Business flow spans apps:
  1. Catalog entities (`core.models`: tipo, estado, fabricante, modelo, centro de costo) feed inventory records.
  2. `dispositivos` manages assets, assignment history (`HistorialAsignacion`) and accessories (`EntregaAccesorio`), including assign/reassign/return flows.
  3. `actas.services.ActaService` creates/signs legal records, links pending assignments/accessories, and generates PDFs.
  4. `dashboard` aggregates `dispositivos` data with shared filters and exports XLSX.
- UI is SSR + HTMX/Alpine: views often branch on `HX-Request` to return partial templates (instead of JSON APIs) and trigger client refreshes via `HX-Trigger` headers.

## Key conventions specific to this repo

- Keep multi-model business logic in service layer classes (not in views), especially `actas/services.py`.
- For list/detail queries with relations, proactively use `select_related()` / `prefetch_related()` to avoid N+1; this pattern is used across `core`, `dispositivos`, `actas`, and `dashboard`.
- Wrap multi-step writes in `transaction.atomic()` (assignment/reassignment/return and acta creation paths rely on this).
- URL names for CRUD must follow `modelname_action` (lowercase Django model name), because `core/templatetags/action_tags.py` builds action URLs dynamically from `obj._meta.model_name`.
- HTMX mutation responses commonly return `204` with `HX-Trigger` JSON payloads to refresh tables/toasts; preserve this response style when extending CRUD flows.
- `colaboradores.Colaborador` is a soft-delete user model (`delete()` toggles `esta_activo` / `is_active`) and is the canonical auth user across apps.
- Reuse `core.forms.BaseStyledForm` for consistent form styling and keep HTMX/Alpine widget attributes in form definitions when needed.
- Prefer factories from `core/tests/factories.py` for test data; markers in `pytest.ini` are `e2e`, `integration`, `unit`.
