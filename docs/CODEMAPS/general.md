# General Codemap

**Last Updated:** 2026-04-24
**Entry Points:** `inventario_jmie/urls.py`, `inventario_jmie/settings.py`

## Architecture

```
inventario_jmie/
├── settings.py          # Configuración Django, logging, seguridad
├── urls.py              # URL routing principal
├── wsgi.py              # WSGI application
└── asgi.py              # ASGI application

Apps:
├── core/                # Utilidades globales, catálogos, HTMX helpers
├── colaboradores/       # AUTH_USER_MODEL, gestión de personal
├── dispositivos/        # Inventario, mantenimientos, asignaciones
├── actas/               # Actas legales, PDF, firma digital
└── dashboard/           # Métricas, filtros, reportes
```

## URL Routing

| Prefix | App | Namespace | Description |
|--------|-----|-----------|-------------|
| `/` | core | - | Home/dashboard |
| `/catalogos/` | core | core | Catálogos base (fabricantes, tipos, estados, modelos, CC) |
| `/dispositivos/` | dispositivos | dispositivos | CRUD inventario, mantenimientos, asignaciones |
| `/colaboradores/` | colaboradores | colaboradores | Gestión de personal |
| `/actas/` | actas | actas | Actas legales, PDF, firma |
| `/dashboard/` | dashboard | dashboard | Métricas y reportes |
| `/login/` | - | - | Autenticación |
| `/logout/` | - | - | Cierre de sesión |
| `/admin/` | - | - | Django admin |

## Key Modules

| Module | Purpose | Key Exports | Dependencies |
|--------|---------|-------------|--------------|
| `inventario_jmie/settings.py` | Configuración Django | LOGGING, INSTALLED_APPS, AUTH_USER_MODEL | python-dotenv, constance |
| `inventario_jmie/urls.py` | URL routing | urlpatterns | core.views, all apps |
| `core/htmx.py` | HTMX helpers | `htmx_trigger_response`, `htmx_render_or_redirect`, `htmx_success_or_redirect`, `is_htmx` | django_htmx |
| `core/utils.py` | Utilidades globales | Helpers de formato, validación | - |
| `core/templatetags/ui_tags.py` | Template tags UI | Tags para renderizado de componentes | - |
| `core/templatetags/nav_tags.py` | Template tags nav | Tags para navegación activa | - |
| `core/templatetags/url_tags.py` | Template tags URL | Tags para manipulación de URLs | - |

## Settings Highlights

- **AUTH_USER_MODEL:** `colaboradores.Colaborador`
- **CONSTANCE:** `CLI_PREFIX_ID` (prefijo para IDs internos, default `JMIE`)
- **LOGGING:** Loggers por app (`dispositivos`, `actas`, `colaboradores`, `core`) → `inventario.log`
- **Security:** Fail-fast validation para SECRET_KEY y ALLOWED_HOSTS
- **Database:** SQLite configurable vía `DB_PATH` env var

## External Dependencies

- Django 6.0.2
- django-htmx 1.27.0
- django-constance 4.3.5
- django-cotton 2.6.2
- django-filter 25.2
- python-dotenv 1.2.1

## Related Areas

- [Frontend Codemap](frontend.md) - Templates y componentes
- [Backend Codemap](backend.md) - Vistas y servicios
- [Database Codemap](database.md) - Modelos y relaciones
