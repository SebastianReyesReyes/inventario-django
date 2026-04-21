# AGENTS.md - Inventario JMIE

## Stack
- **Django 6.0.2** with Django REST Framework
- **HTMX + Alpine.js** for frontend reactivity (no SPA frameworks)
- **Tailwind CSS** via crispy-tailwind for forms
- **pytest** with pytest-django, pytest-playwright, factory-boy
- **Playwright** for E2E browser tests
- **SQLite** by default (`db.sqlite3`)

## Project Structure
```
inventario_jmie/     # Django project settings
core/                # Base templates, layouts, global utilities
colaboradores/       # Staff model (AUTH_USER_MODEL) and management
dispositivos/        # Inventory: hardware, types, maintenance
actas/               # Legal documents (delivery/return), services layer
dashboard/           # Statistics and metrics views
tests_e2e/           # Playwright E2E tests
```

## Key Commands
```bash
# Setup
python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py makemigrations && python manage.py migrate

# Run dev server
python manage.py runserver

# Tests
pytest                              # All tests
pytest -m "not e2e"                # Fast tests only (no browser)
pytest -m e2e --headed --browser chromium  # E2E with visual inspection
pytest --cov=. --cov-report=term-missing   # With coverage
```

## Architecture Conventions
- **Service Layer**: Complex business logic goes in `services.py`, not views. Example: `actas/services.py`
- **Models**: Use `clean()` for validation, signals only for cache/notifications
- **HTMX responses**: Return HTML partials, not JSON. Use `TemplateResponse` or `HttpResponse`
- **N+1 prevention**: Always use `select_related()` or `prefetch_related()` for related objects
- **Atomic transactions**: Wrap multi-model writes in `transaction.atomic()`

## Forms
- Use Crispy `FormHelper` for all forms: `self.helper = FormHelper()`
- HTMX attributes on widgets: `self.fields['field'].widget.attrs.update({'x-data': 'autocomplete()'})`

## Tests
- **Factories**: Use `core/tests/factories.py` for test data, not manual `.objects.create()`
- **E2E selectors**: Wait for HTMX renders with `.wait_for_selector()` before asserting
- **Markers**: `@pytest.mark.e2e`, `@pytest.mark.integration`, `@pytest.mark.unit`

## Settings Notes
- `AUTH_USER_MODEL = 'colaboradores.Colaborador'`
- `LOGIN_URL = '/login/'`
- Language: Spanish Chile (`LANGUAGE_CODE = 'es-cl'`)
- Secret key is hardcoded (dev only) - do not commit production secrets

## Config Files
| File | Purpose |
|------|---------|
| `.env.example` | Environment variables template |
| `pytest.ini` | Pytest configuration |
| `inventario_jmie/settings.py` | Django settings |

## Docs
- Full dev guide: `docs/dev_guide/` (tech stack, patterns, testing, frontend)
- Testing guide: `.agents/notes/testing_guide.md`
