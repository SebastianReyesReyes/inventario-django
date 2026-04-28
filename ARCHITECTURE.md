# ARCHITECTURE.md — Inventario JMIE

## Overview

Sistema de gestión de inventario de equipos tecnológicos para JMIE. Administra dispositivos polimórficos (notebooks, smartphones, servidores, etc.), asignaciones a colaboradores, mantenimientos, actas legales con firma digital, y métricas operativas. Arquitectura SSR con Django 6, HTMX, Alpine.js y Tailwind CSS.

## Tech Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Django 6.0.2, Python 3.12 |
| Frontend | HTMX 1.x, Alpine.js 3.x, Tailwind CSS 3.x (CDN Play) |
| UI Components | django-cotton 2.6.2 |
| Forms | django-crispy-forms + crispy-tailwind |
| Database | SQLite (local/Docker), configurable vía `DB_PATH` |
| Auth | Django built-in (`Colaborador` como `AUTH_USER_MODEL`) |
| PDF / Firma | xhtml2pdf, pyHanko, reportlab |
| QR | qrcode + Pillow |
| Import/Export | django-import-export, tablib, openpyxl |
| Config dinámica | django-constance (backend DB) |
| Testing | pytest, pytest-django, factory-boy, pytest-playwright |
| Deploy | Docker Compose + Nginx + Gunicorn |

## Directory Structure

```
inventario-django/
├── inventario_jmie/          # Configuración Django
│   ├── settings.py           # Settings con validación fail-fast de SECRET_KEY y ALLOWED_HOSTS
│   ├── urls.py               # Root URLconf, incluye apps + auth views
│   ├── wsgi.py               # Entry point producción
│   └── asgi.py               # Entry point async
├── core/                     # Catálogos base, utilidades globales, templates base
│   ├── models.py             # TipoDispositivo, EstadoDispositivo, Fabricante, Modelo, CentroCosto, Departamento
│   ├── views.py              # Home, dashboard drill-down, catálogos (FBV + CBV)
│   ├── catalog_views.py      # CBVs para CRUD de catálogos
│   ├── forms.py              # BaseStyledForm (Tailwind auto-styling)
│   ├── htmx.py               # Helpers HTMX: is_htmx, htmx_trigger_response, htmx_render_or_redirect
│   ├── utils.py              # Utilidades transversales
│   ├── filters.py            # Filtros django-filter
│   ├── templatetags/         # action_tags, nav_tags, ui_tags, url_tags
│   ├── management/commands/  # import_devices, load_entra_users, seed_cc
│   └── tests/factories.py    # Factory-boy: fuente principal de datos de prueba
├── colaboradores/            # AUTH_USER_MODEL = Colaborador
│   ├── models.py             # Extensión de AbstractUser con RUT, cargo, soft-delete
│   ├── views.py              # Gestión de colaboradores
│   └── tests/factories.py    # ColaboradorFactory
├── dispositivos/             # Inventario polimórfico, trazabilidad, QR
│   ├── models.py             # Dispositivo + especializados (Notebook, Smartphone, etc.)
│   ├── views.py              # CRUD + trazabilidad (asignar, reasignar, devolver) + AJAX
│   ├── services.py           # DispositivoFactory, TrazabilidadService (capa de servicios)
│   ├── forms.py              # Forms técnicos por tipo de dispositivo
│   ├── signals.py            # Señales Django
│   └── tests/                # Unit, integration, edge cases, signals
├── actas/                    # Actas legales, firma digital, folios
│   ├── models.py             # Acta con folio correlativo y blindaje de firma
│   ├── services.py           # ActaService: creación, firma digital, PDF
│   └── templatetags/         # acta_tags
├── dashboard/                # Métricas, filtros analíticos, exportación Excel/CSV
│   ├── views.py              # Vistas de reportes y gráficos
│   ├── services.py           # Lógica de agregación y exportación
│   └── filters.py            # AnaliticaInventarioFilter
├── suministros/              # Gestión de suministros y compatibilidad con dispositivos
│   ├── models.py             # CategoríaSuministro, Suministro
│   └── services.py           # Lógica de negocio
├── templates/                # Templates globales
│   ├── base.html             # Layout principal con contenedores HTMX (#modal-container, #side-over-container)
│   ├── auth/                 # Login/logout
│   ├── cotton/               # Componentes reutilizables django-cotton
│   └── partials/             # Partials globales
├── tests_e2e/                # E2E con Playwright (Page Object Model)
│   ├── pages/inventory_pages.py
│   ├── conftest.py           # Configura DJANGO_ALLOW_ASYNC_UNSAFE
│   └── test_*.py             # Flujos E2E
├── ops/                      # Infraestructura
│   ├── deploy/               # systemd, nginx, scripts de instalación
│   └── docker/               # entrypoint.sh, nginx.conf
├── docs/                     # Documentación técnica
│   ├── dev_guide/            # Guías numeradas (stack, patrones, testing)
│   ├── CODEMAPS/             # Mapas de código por capa
│   ├── ARQUITECTURA_TECNICA.md
│   └── STYLE_GUIDE.md        # Design tokens Tailwind
└── static/                   # CSS, JS, imágenes, fuentes locales
```

## Core Components

### 1. `core` — Infraestructura Global
- **Catálogos base**: `TipoDispositivo`, `EstadoDispositivo`, `Fabricante`, `Modelo`, `CentroCosto`, `Departamento`
- **HTMX helpers** (`core/htmx.py`): `is_htmx()`, `htmx_trigger_response()`, `htmx_render_or_redirect()`, `htmx_success_or_redirect()`, `htmx_redirect_or_redirect()`
- **BaseStyledForm** (`core/forms.py`): Aplica clases Tailwind automáticamente a widgets de formulario
- **Templatetags críticos**:
  - `action_tags.py`: `{% render_actions obj %}` genera botones Ver/Editar/Eliminar. **Depende estrictamente de la convención de URLs `[model_name]_[action]`**.
  - `nav_tags.py`, `ui_tags.py`, `url_tags.py`: Helpers de UI
- **Management commands**: `import_devices` (CSV masivo), `load_entra_users`, `seed_cc`

### 2. `dispositivos` — Inventario y Trazabilidad
- **Modelo base**: `Dispositivo` con identificador automático `PREFIX-SIGLA-NNNN` (ej: `JMIE-NB-0001`)
- **Herencia polimórfica**: Multi-table inheritance Django
  - `Notebook`, `Smartphone`, `Impresora`, `Servidor`, `EquipoRed`, `Monitor`
- **QuerySet custom**: `DispositivoQuerySet` con `.activos()`, `.con_detalles()`
- **Trazabilidad**: `HistorialAsignacion`, `BitacoraMantenimiento`, `EntregaAccesorio`
- **Factory pattern**: `DispositivoFactory` resuelve formulario técnico según tipo
- **Service layer**: `TrazabilidadService` encapsula asignar, reasignar, devolver, entregar_accesorio con `transaction.atomic()`

### 3. `colaboradores` — Identidad y Acceso
- `Colaborador(AbstractUser)`: Extiende usuario Django con `rut`, `cargo`, `departamento`, `centro_costo`, `azure_id`
- **Soft delete**: `delete()` desactiva (`esta_activo = False`, `is_active = False`) sin borrar fila
- `AUTH_USER_MODEL = 'colaboradores.Colaborador'`

### 4. `actas` — Documentos Legales
- `Acta` con folio correlativo `ACT-{YYYY}-{NNNN}`
- **Blindaje de firma**: Si `firmada=True`, `save()` lanza `ValidationError`
- **Firma digital**: `ActaService.firmar_acta()` con pyHanko
- **Generación PDF**: xhtml2pdf desde templates HTML
- Tipos: `ENTREGA`, `DEVOLUCION`, `DESTRUCCIÓN`

### 5. `dashboard` — Inteligencia Operativa
- Métricas, gráficos Chart.js con drill-down a listados filtrados
- Exportación Excel/CSV
- Reutiliza `AnaliticaInventarioFilter` de `dashboard/filters.py`

### 6. `suministros` — Gestión de Insumos
- `CategoriaSuministro`, `Suministro`
- Campos de compatibilidad con tipos de dispositivo

## Data Flow

### Flujo HTMX (Interacción UI)
```
Usuario → Click/Búsqueda → HTMX request → Django View
    → Service Layer (si ≥2 modelos o transacción)
    → ORM → SQLite
    → Responde HTML parcial (no JSON)
    → HTMX swapea DOM objetivo (#modal-container, #side-over-container, tabla)
```

### Flujo de Trazabilidad (Asignación/Reasignación/Devolución)
```
Vista de Dispositivo → TrazabilidadService
    → transaction.atomic()
        1. Crea/actualiza HistorialAsignacion
        2. Actualiza Dispositivo.estado + propietario_actual
    → (bloque separado) ActaService.crear_acta()
        → Genera Acta con folio correlativo
    → Responde con HX-Trigger + partial de éxito
```

### Flujo de Creación de Dispositivo
```
dispositivo_create view → DispositivoFactory.create_form_instance()
    → Resuelve form según tipo (NotebookForm, SmartphoneForm, etc.)
    → transaction.atomic(): guarda dispositivo base + subclase
    → (bloque separado) Si generar_acta + propietario: ActaService.crear_acta()
    → Renderiza detalle con modal de acta o redirect
```

## External Integrations

| Servicio | Uso | Ubicación |
|----------|-----|-----------|
| SQLite | Base de datos principal | Configurable vía `DB_PATH` o `DATABASE_URL` |
| Azure AD (Entra ID) | Carga de usuarios | `core/management/commands/load_entra_users.py` |
| pyHanko | Firma digital de PDFs | `actas/services.py` |
| xhtml2pdf / reportlab | Generación de PDFs | `actas/services.py` |
| Nginx | Reverse proxy + static files | `ops/docker/nginx.conf`, `ops/deploy/nginx_inventario.conf` |

## Configuration

### Environment Variables (`.env`)
```bash
# CRÍTICO: settings.py lee SECRET_KEY (no DJANGO_SECRET_KEY)
SECRET_KEY=cambia-por-una-clave-segura-de-al-menos-50-caracteres
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
# DB_PATH=/data/db.sqlite3   # Opcional para Docker
```

### Configuración Dinámica
- `django-constance` con backend DB para configuraciones editables en runtime
- `CLI_PREFIX_ID`: prefijo para identificadores internos de equipos (default: `JMIE`)

### Logging
- Loggers por app escriben a `inventario.log` en raíz del proyecto
- Apps con logger: `dispositivos`, `actas`, `colaboradores`, `core`, `suministros`

## Build & Deploy

### Desarrollo local (Windows)
```powershell
python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Editar .env: SECRET_KEY=...
python manage.py makemigrations && python manage.py migrate
python manage.py runserver
```

### Tests
```bash
pytest                              # Todo con coverage
pytest -m "not e2e"                # Excluye E2E
pytest -m e2e --headed --browser chromium
```

### Docker (Piloto UAT)
```bash
docker compose up -d --build       # Primera vez
docker compose exec web python manage.py migrate
```
- Contenedor corre con usuario `django` (UID 999)
- Volumen `./data` para persistencia SQLite
- Healthcheck en `/login/`

### Deploy tradicional
- Ver `ops/deploy/README_DEPLOY.md`
- Servicio systemd Gunicorn + Nginx

## Decisiones Arquitectónicas Clave

1. **Herencia manual (multi-table)**: Se prefirió sobre CTI o JSONField para mantener integridad referencial y queries eficientes con `select_related`.
2. **Service Layer obligatorio**: Cualquier lógica que toque ≥2 modelos o requiera atomicidad va en `services.py`.
3. **Transacciones separadas**: Operación principal y generación de acta usan `transaction.atomic()` independientes para evitar revertir el registro principal si falla el acta.
4. **HTMX sobre JSON**: Todas las respuestas de UI son HTML parciales (HATEOAS). JSON solo para APIs externas.
5. **Soft delete de usuarios**: Protege el historial de asignaciones y actas legales.
