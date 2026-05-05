# ARCHITECTURE.md — Inventario JMIE

## Overview

Inventario JMIE is a Django server-side rendered (SSR) web application for managing IT asset inventory, personnel assignments, maintenance logs, legal delivery/return acts (with digital PDF signing), and analytics dashboards. It uses HTMX + Alpine.js + Tailwind CSS for interactive UI without building a SPA.

## Tech Stack

| Layer | Technology | Version / Notes |
|-------|-----------|-----------------|
| Framework | Django | SSR |
| Language | Python | |
| Database | SQLite | Local file (`db.sqlite3` or `DB_PATH` env) |
| Frontend | HTMX + Alpine.js + Tailwind CSS | SSR, no SPA |
| UI Components | django-cotton | Reusable components in `templates/cotton/` |
| Forms | django-crispy-forms + crispy-tailwind | Styled forms via `BaseStyledForm` |
| Auth | Django built-in | Custom `Colaborador` user model |
| Dynamic Config | django-constance | `CLI_PREFIX_ID` for auto IDs |
| Image Handling | django-imagekit | Thumbnails & processing |
| Import/Export | django-import-export | CSV/Excel bulk operations |
| Testing | pytest, pytest-django, factory-boy, pytest-playwright | `--cov=. --reuse-db` default |
| PDF Signing | pyHanko, pypdf, reportlab | Digital signature on legal acts |
| QR Codes | qrcode | Equipment QR generation |
| Deployment | Docker Compose + Nginx + Gunicorn | UAT pilot ready |

## Directory Structure

```
inventario-django/
├── inventario_jmie/          # Project config: settings, root urls, WSGI/ASGI
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py / asgi.py
│
├── core/                     # Base catalogs, HTMX helpers, shared template tags, Cotton base
│   ├── models.py             # TipoDispositivo, EstadoDispositivo, Fabricante, Modelo, Departamento, CentroCosto
│   ├── htmx.py               # HTMX response helpers (htmx_trigger_response, htmx_render_or_redirect, etc.)
│   ├── forms.py              # BaseStyledForm (Tailwind-styled base form)
│   ├── catalog_views.py      # Shared CBVs for catalog CRUD
│   ├── templatetags/         # action_tags, nav_tags, ui_tags, url_tags
│   ├── management/commands/  # import_devices, seed_db, setup_groups, reset_db, etc.
│   └── tests/factories.py    # Shared factory-boy factories
│
├── colaboradores/            # AUTH_USER_MODEL = Colaborador
│   ├── models.py             # Custom user extending AbstractUser with soft-delete (esta_activo)
│   ├── views.py              # CRUD + export
│   └── tests/
│
├── dispositivos/             # Polymorphic inventory, maintenance, assignments, accessories, QR
│   ├── models.py             # Dispositivo (base) + Notebook, Smartphone, etc. + BitacoraMantenimiento + HistorialAsignacion
│   ├── services.py           # DispositivoFactory (form resolution), TrazabilidadService (assign/return)
│   ├── signals.py            # Signal handlers for assignments/events
│   ├── forms.py              # DispositivoForm, NotebookTechForm, AsignacionForm, DevolucionForm, AccesorioForm
│   ├── views.py              # FBV for device CRUD, assignments, QR, HTMX partials
│   └── templates/dispositivos/ + partials/
│
├── actas/                    # Legal acts (delivery/return/destruction), PDF generation, folios, digital signature
│   ├── services.py           # ActaService, ActaPDFService (PDF gen & signing)
│   ├── models.py             # Acta, FolioCounter
│   ├── playwright_browser.py # PDF rendering via Playwright
│   └── templatetags/acta_tags.py
│
├── dashboard/                # Metrics, Chart.js, Excel/CSV export, drill-down
│   ├── services.py           # Aggregation/metric logic
│   ├── filters.py            # AnaliticaInventarioFilter
│   └── templates/dashboard/ + partials/
│
├── suministros/              # Supplies management (additional domain)
│   ├── models.py, services.py, views.py, forms.py, templates/
│
├── templates/                # Global templates: base.html, auth, error pages, Cotton components
│   ├── base.html             # Master layout (loads HTMX, Alpine.js, Tailwind)
│   ├── cotton/               # Reusable UI components (btn_primary, glass_panel, paginator, etc.)
│   └── partials/             # Shared partials (action_buttons.html)
│
├── static/                   # Static assets (fonts, images)
├── media/                    # User uploads (device photos)
│
├── tests_e2e/                # Playwright E2E tests with Page Object Model
│   ├── conftest.py           # E2E fixtures, sets DJANGO_ALLOW_ASYNC_UNSAFE=true
│   ├── pages/                # Page Object classes (inventory_pages, suministros_pages)
│   └── test_*.py             # Flow tests (inventory, maintenance, actas, full lifecycle)
│
├── docs/                     # Technical docs, architecture maps, dev guides
│   └── dev_guide/
│
├── ops/                      # Deployment & operations
│   ├── deploy/               # Nginx, Gunicorn, systemd, README_DEPLOY.md
│   └── docker/               # entrypoint.sh, nginx.conf
│
├── scripts/                  # Utility scripts for data migration and maintenance
│
├── manage.py
├── requirements.txt
├── pytest.ini
├── docker-compose.yml
└── Dockerfile
```

## Core Components

### Domain Apps

| App | Responsibility | Key Models |
|-----|---------------|------------|
| `core` | Shared catalogs, HTMX utilities, template tags, management commands | `TipoDispositivo`, `EstadoDispositivo`, `Fabricante`, `Modelo`, `Departamento`, `CentroCosto` |
| `colaboradores` | Personnel & authentication | `Colaborador` (custom user) |
| `dispositivos` | Polymorphic IT asset inventory, assignments, maintenance | `Dispositivo`, `Notebook`, `Smartphone`, `BitacoraMantenimiento`, `HistorialAsignacion` |
| `actas` | Legal acts, PDF generation, digital signature | `Acta`, `FolioCounter` |
| `dashboard` | Analytics, exports, drill-downs | Filters & aggregation services |
| `suministros` | Supplies/consumables tracking | Supply-specific models |

### Service Layer

Complex business logic lives in `*/services.py`, not in views:

- **`dispositivos/services.py`**
  - `DispositivoFactory` — Resolves the correct form class (e.g., `NotebookForm`) from `tipo_id` or instance.
  - `TrazabilidadService` — Encapsulates atomic operations for `asignar`, `reasignar`, `devolver`. All use `@transaction.atomic`.

- **`actas/services.py`**
  - `ActaService` — Creates acts with folio numbering, links assignments.
  - `ActaPDFService` — Renders act HTML to PDF and applies digital signatures using `pyHanko`.

- **`dashboard/services.py`**
  - Aggregation logic for metrics and chart data.

### HTMX Architecture

The UI is server-rendered with HTMX for partial updates:

- **Helpers**: `core/htmx.py` provides `htmx_trigger_response`, `htmx_render_or_redirect`, `htmx_success_or_redirect`, `htmx_redirect_or_redirect`.
- **Partials**: HTML fragments live in `*/templates/*/partials/` (tables, forms, side-overs, modals).
- **Response Pattern**: On successful mutations, prefer `204 No Content` + `HX-Trigger` to refresh tables or show toasts.
- **Error Handling**: When `ProtectedError` or `IntegrityError` occurs on delete/toggle, return the modal HTML with the error + `HX-Trigger` for a toast.

### Template Tags

- **`core/templatetags/action_tags.py`** — `{% render_actions obj 'inventory' %}` dynamically generates View/Edit/Delete/Toggle buttons by resolving URLs using the convention `app:modelname_action`.
- **`core/templatetags/ui_tags.py`** — UI helpers.
- **`actas/templatetags/acta_tags.py`** — Acta-specific formatting.

## Data Flow

### Request Flow (Typical List View)

```
Browser (HTMX request)
  → Nginx (ops/deploy/)
  → Gunicorn → Django WSGI
    → Middleware (django_htmx.HtmxMiddleware, CSRF, Auth)
    → URL Router (inventario_jmie/urls.py → app/urls.py)
    → View (FBV with @login_required + @permission_required)
      → Filter (django-filter FilterSet)
      → QuerySet (.con_detalles() with select_related/prefetch_related)
      → Pagination (custom paginator)
    → Template Renderer
      → If HTMX: render partial template (partials/_table.html)
      → If full page: render full template (dispositivo_list.html)
    → HttpResponse (or 204 + HX-Trigger for mutations)
```

### Assignment Flow

```
User submits AsignacionForm (HTMX)
  → dispositivo_asignar view
    → TrazabilidadService.asignar(dispositivo, form, creado_por)
      → @transaction.atomic
      → Creates HistorialAsignacion
      → Updates Dispositivo.estado → "Asignado"
      → Updates Dispositivo.propietario_actual
      → If generar_acta: calls ActaService.crear_acta(...)
        → Generates Acta with folio
        → Generates signed PDF via ActaPDFService
    → Returns 204 + HX-Trigger {"showToast": "Asignado correctamente"}
```

### Auto-ID Generation

On `Dispositivo.save()`:
1. Reads `config.CLI_PREFIX_ID` (django-constance, default `JMIE`).
2. Reads `modelo.tipo_dispositivo.sigla` (e.g., `NTBK`).
3. Finds the last device with that prefix.
4. Generates next sequential ID: `JMIE-NTBK-00001`.

## External Integrations

| Service | Purpose | Location |
|---------|---------|----------|
| SQLite | Primary database | `DB_PATH` env or `db.sqlite3` |
| Nginx | Reverse proxy & static files | `ops/deploy/nginx_inventario.conf` |
| Gunicorn | WSGI HTTP server | `ops/deploy/gunicorn_inventario.service` |
| Docker | Containerization | `Dockerfile`, `docker-compose.yml` |

No external APIs (REST/GraphQL) are consumed at runtime. The app is self-contained.

## Configuration

### Environment Variables (`.env`)

| Variable | Required | Purpose |
|----------|----------|---------|
| `SECRET_KEY` | Yes | Django secret key (fail-fast if missing/placeholder) |
| `DEBUG` | Yes | `True`/`False` |
| `ALLOWED_HOSTS` | Yes | Comma-separated hosts |
| `DB_PATH` | No | Custom SQLite path (default: `db.sqlite3` in root) |
| `DATABASE_URL` | No | Alternative DB connection string |

**Critical**: `settings.py` reads `SECRET_KEY` from `os.getenv('SECRET_KEY')`, NOT `DJANGO_SECRET_KEY`. The `.env.example` incorrectly names it `DJANGO_SECRET_KEY`; you must define `SECRET_KEY=` in `.env`.

### Django Settings

- `AUTH_USER_MODEL = 'colaboradores.Colaborador'`
- `django_htmx` middleware active for HTMX detection.
- `django-cotton` for reusable UI components.
- `django-constance` with database backend for `CLI_PREFIX_ID`.
- `USE_X_FORWARDED_HOST = True` and `SECURE_PROXY_SSL_HEADER` for Docker/Nginx.

### Fail-Fast Security Checks

`settings.py` raises `ImproperlyConfigured` on startup if:
- `SECRET_KEY` is missing, empty, or starts with `django-insecure-` / `change-me` / `your-secret-key`.
- `ALLOWED_HOSTS` is empty.
- `ALLOWED_HOSTS` contains `*` when `DEBUG=False`.

## Build & Deploy

### Local Development (Windows)

```powershell
python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env          # Edit SECRET_KEY!
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

### Testing

```bash
pytest                          # All tests with coverage
pytest -m "not e2e"            # Exclude E2E
pytest -m e2e --headed --browser chromium
```

### Docker

```bash
# First time
docker compose up -d --build

# Migrations
docker compose exec web python manage.py migrate
```

### Production Deploy

See `ops/deploy/README_DEPLOY.md`. Stack:
- Docker Compose (web + nginx containers)
- Gunicorn with `gunicorn_inventario.service`
- Nginx with `nginx_inventario.conf`
- SQLite volume mounted at `data/`
- Container runs as `django` user (UID 999); `data/` must be writable by that UID.

### Management Commands

| Command | Purpose |
|---------|---------|
| `python manage.py import_devices ruta.csv --dry-run` | Bulk device import |
| `python manage.py seed_db` | Seed catalogs & test data |
| `python manage.py setup_groups` | Create Django auth groups |
| `python manage.py reset_db` | Reset database (dev only) |
| `python manage.py import_catalogos` | Import catalogs from CSV |
| `python manage.py load_entra_users` | Sync users from Entra ID |

## Key Architectural Decisions

1. **SSR over SPA**: HTMX + Alpine.js keeps the frontend simple and tightly coupled to Django templates.
2. **FBV over CBV**: Function-Based Views are preferred for business logic; CBVs are only used for repetitive catalog CRUD via `core/catalog_views.py`.
3. **Service Layer**: Multi-model or atomic operations are centralized in `services.py` with explicit `@transaction.atomic`.
4. **Soft Delete**: `Colaborador.delete()` sets `esta_activo=False` and `is_active=False` to preserve historical records.
5. **Polymorphic Inventory**: `Dispositivo` is the base table; `Notebook`, `Smartphone`, etc. use multi-table inheritance.
6. **URL Convention Enforcement**: The `[modelname]_[action]` URL naming pattern is critical because `render_actions` depends on it for automatic button generation.
