# Inventario JMIE

Sistema de gestión de inventario TI para JMIE, construido con **Django 6.x + HTMX + Alpine.js + Tailwind CSS**. Permite el control completo de dispositivos, asignaciones a colaboradores, trazabilidad legal mediante actas firmadas, y dashboard analítico.

## Setup Rápido (Windows)

```powershell
# 1. Crear entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install -r requirements.txt
playwright install chromium  # Requerido para generación de PDFs

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env: rellenar SECRET_KEY con un valor seguro (>30 chars).
# Opcional: definir DB_PATH si deseas ubicar la base de datos fuera de la raíz.

# 4. Migraciones e inicio
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

### Variables de Entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `SECRET_KEY` | Sí | Clave segura (>30 chars, sin prefijos como `django-insecure-`). El sistema falla al arrancar si está vacía o usa placeholder. **Nota:** `settings.py` lee `SECRET_KEY`, no `DJANGO_SECRET_KEY`. |
| `DEBUG` | No | `True`/`False`. En producción se fuerzan validaciones adicionales. |
| `ALLOWED_HOSTS` | Sí (cuando `DEBUG=False`) | Lista separada por comas. No puede estar vacía ni contener `*` en producción. |
| `DB_PATH` | No | Permite cambiar la ubicación de `db.sqlite3` (útil para Docker). |
| `DATABASE_URL` | No | URL de conexión (por defecto `sqlite:///db.sqlite3`). |

## Arquitectura

Ver [docs/CODEMAPS/INDEX.md](docs/CODEMAPS/INDEX.md) para el mapa detallado.

### Apps del Proyecto

| App | Propósito |
|-----|-----------|
| `core` | Catálogos base (fabricantes, tipos, estados, modelos, centros de costo), utilidades HTMX, templates base, componentes Cotton |
| `colaboradores` | Modelo de usuario personalizado (`Colaborador`), gestión de personal, roles y centros de costo |
| `dispositivos` | Inventario de equipos (Notebook, Smartphone, Monitor, Impresora, Servidor, EquipoRed), mantenimientos, asignaciones, accesorios |
| `actas` | Generación de actas legales (ENTREGA, DEVOLUCIÓN, DESTRUCCIÓN), firma digital, exportación PDF (Playwright) |
| `dashboard` | Métricas, filtros analíticos, gráficos Chart.js, reportes y exportación |
| `suministros` | Gestión de suministros y compatibilidad con dispositivos |

### Stack Tecnológico

- **Backend:** Django 6.0.2, Django REST Framework, django-htmx, django-cotton, django-constance, django-filter, django-import-export
- **Frontend:** HTMX, Alpine.js, Tailwind CSS
- **Base de datos:** SQLite (local), configurable vía `DB_PATH`
- **PDF:** Playwright/Chromium (renderizado HTML→PDF), pyHanko (firma digital), pypdf
- **QR:** qrcode
- **Testing:** pytest, pytest-django, factory-boy, pytest-playwright
- **Otros:** django-crispy-forms, crispy-tailwind, django-imagekit, django-debug-toolbar

## Características Principales

- **Inventario polimórfico:** Dispositivo base con modelos especializados (Notebook, Smartphone, Monitor, Impresora, Servidor, EquipoRed)
- **Identificadores automáticos:** Formato `JMIE-SIGLA-00001` configurable vía Django Constance
- **Trazabilidad completa:** Historial de asignaciones con actas legales vinculadas
- **Generación de actas PDF:** Folio correlativo, renderizado con Playwright/Chromium, firma digital con pyHanko
- **Códigos QR:** Generación dinámica por equipo para escaneo rápido
- **Dashboard analítico:** Gráficos Chart.js con drill-down a listados filtrados
- **Importación masiva:** Comando `import_devices` para carga desde CSV
- **HTMX nativo:** Respuestas parciales, modales, side-overs, sin SPA

## Comandos Clave

```bash
# Ejecutar todas las pruebas
pytest

# Excluir E2E (más rápido)
pytest -m "not e2e"

# Solo E2E con navegador visible
pytest -m e2e --headed --browser chromium

# Prueba específica
pytest path/to/test.py::test_name

# Importar dispositivos desde CSV
python manage.py import_devices ruta/al/archivo.csv
python manage.py import_devices ruta/al/archivo.csv --dry-run  # Simulación
```

## Convenciones Críticas

- **Service Layer:** Lógica de negocio compleja en `services.py`, no en views
- **Transacciones:** Escrituras multi-modelo en `transaction.atomic()`. Si una operación secundaria puede fallar (ej. generación de acta), usar bloque atómico separado
- **Soft delete de usuarios:** `Colaborador.delete()` desactiva (`esta_activo`/`is_active`), no borra fila
- **ORM performance:** Usar `select_related()` / `prefetch_related()` en listados con relaciones
- **HTMX:** Responder con HTML parcial (no JSON para flujos de UI). Usar helpers de `core/htmx.py`
- **Naming de URLs:** CRUD debe seguir `[modelname]_[action]` con `model_name` en minúsculas (requerido por `{% render_actions %}`)

## Documentación

- [Arquitectura Técnica](docs/ARQUITECTURA_TECNICA.md)
- [Guía de Stack y Entorno](docs/dev_guide/01_tech_stack_y_entorno.md)
- [Patrones y Arquitectura](docs/dev_guide/02_patrones_y_arquitectura.md)
- [Mejores Prácticas Django](docs/dev_guide/03_mejores_practicas_django.md)
- [Mejores Prácticas Frontend](docs/dev_guide/04_mejores_practicas_frontend.md)
- [Guía de Pruebas E2E](docs/dev_guide/05_guia_de_pruebas_e2e.md)
- [Poblado de Datos Iniciales y Reset](docs/dev_guide/06_poblado_de_datos_iniciales.md)
- [Convenciones de URLs](docs/dev_guide/URL_CONVENTIONS.md)
- [Higiene de Dependencias](docs/dev_guide/dependency_hygiene.md)
- [Guía de Despliegue](ops/deploy/README_DEPLOY.md)

## Estructura del Proyecto

```
inventario-django/
├── inventario_jmie/     # Settings, urls, arranque del proyecto
├── core/                # Utilidades globales, catálogos base, helpers HTMX, templatetags
├── colaboradores/       # AUTH_USER_MODEL (Colaborador), formularios, vistas
├── dispositivos/        # Inventario, mantenimientos, asignaciones, accesorios, servicios
├── actas/               # Lógica legal/documental (service layer), generación PDF
├── dashboard/           # Métricas, filtros, gráficos, exportación
├── tests_e2e/           # E2E Playwright + Page Objects
├── templates/           # Templates globales (base, auth, colaboradores, cotton components)
├── ops/                 # Docker, deploy, scripts de backup
├── docs/                # Documentación técnica, guías de desarrollo, planes
├── static/              # Archivos estáticos (CSS, JS, imágenes)
└── media/               # Uploads de usuarios (fotos de equipos)
```

## Docker

```bash
# Construir y levantar
docker-compose up --build

# Solo producción
docker-compose -f docker-compose.yml up -d
```

## Contributing

1. Seguir convenciones de [AGENTS.md](AGENTS.md)
2. Escribir pruebas para nuevas funcionalidades
3. Ejecutar `pytest` antes de commit
4. Actualizar documentación si cambian APIs o flujos

---
*Última actualización: 29 de abril de 2026*
