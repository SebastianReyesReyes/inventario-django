# AGENTS.md - Inventario JMIE

## Stack real (actual)
- Django 6.0.2 + HTMX + Alpine.js + Tailwind (SSR, sin SPA).
- Pruebas con `pytest`, `pytest-django`, `factory-boy`, `pytest-playwright`.
- Base de datos local: SQLite (`db.sqlite3`).

## Estructura del proyecto
```
inventario_jmie/     # settings, urls, arranque del proyecto
core/                # utilidades globales, catálogos base, helpers HTMX
colaboradores/       # AUTH_USER_MODEL (Colaborador)
dispositivos/        # inventario, mantenimientos, asignaciones, accesorios
actas/               # lógica legal/documental (service layer)
dashboard/           # métricas, filtros y exportación
tests_e2e/           # E2E Playwright + Page Objects
```

## Setup rápido (Windows)
- `python -m venv venv && .\venv\Scripts\Activate.ps1`
- `pip install -r requirements.txt`
- Copiar `.env.example` a `.env` (el `SECRET_KEY` se lee desde entorno).
- `python manage.py makemigrations && python manage.py migrate`
- `python manage.py runserver`

## Comandos clave
```bash
pytest
pytest -m "not e2e"
pytest -m e2e --headed --browser chromium
pytest path\to\test.py::test_name
```

## Convenciones críticas
- **Service Layer**: lógica de negocio compleja en `services.py`, no en views.
- **ORM performance**: usar `select_related()` / `prefetch_related()` en listados con relaciones.
- **Transacciones**: envolver escrituras multi-modelo en `transaction.atomic()`.
- **Soft delete de usuarios**: `Colaborador.delete()` desactiva (`esta_activo`/`is_active`), no borra fila.

## HTMX
- Responder con HTML parcial (no JSON para flujos de UI).
- Reutilizar helpers de `core/htmx.py` (`htmx_trigger_response`, `htmx_render_or_redirect`, `htmx_success_or_redirect`, `htmx_redirect_or_redirect`).
- En mutaciones, preferir `204 + HX-Trigger` para refrescar tabla/toast cuando aplique.

## Naming de URLs (obligatorio)
- CRUD debe seguir: `[modelname]_[action]` usando `model_name` real en minúscula.
- Esto es requerido por `core/templatetags/action_tags.py` (`reverse(f"{app_label}:{model_name}_{action}", ...)`).
- Si no se respeta, se rompe `{% render_actions %}` con `NoReverseMatch`.

## Formularios
- Patrón base: heredar de `core.forms.BaseStyledForm` para consistencia visual.
- Atributos HTMX/Alpine van definidos en el `__init__` del form/widget.

## Testing
- Usar `core/tests/factories.py` como fuente principal de datos de prueba.
- Marcadores disponibles: `e2e`, `integration`, `unit`.
- E2E usa `live_server` y `tests_e2e/pages/` (Page Object Model).

## Higiene de dependencias
- Si una dependencia no tiene uso verificable en código/flujo actual, se elimina de `requirements.txt`.
- Dependencias opcionales deben tener caso de uso concreto y referencia de roadmap.
- Revisar dependencias cada 4–6 semanas.

## Referencias útiles
- Guía dev: `docs/dev_guide/`
- Guía de pruebas: `.agents/notes/testing_guide.md`
