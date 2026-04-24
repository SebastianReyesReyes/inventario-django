# Plan Maestro — Inventario JMIE

> **Fecha**: 24 de abril 2026
> **Estado del proyecto**: MVP funcional (95% de HUs completadas, Django 6.0.2 arrancando sin errores)
> **Objetivo de este plan**: Llevar el proyecto de "funcional" a "listo para producción"

---

## Resumen Ejecutivo

El sistema está operativo y sirve correctamente en desarrollo. Las 28 HUs del backlog están completadas al 95% (solo Dashboard en refinamiento). Sin embargo, hay deuda técnica acumulada en 4 ejes que deben resolverse antes de un despliegue real:

1. **Robustez** — Transacciones, manejo de errores, signals
2. **Seguridad** — Logging, cookies, rate limiting
3. **Calidad de código** — Refactors pendientes, templates duplicados, factories
4. **Escalabilidad** — Base de datos, caché, Tailwind build

---

## Fase 0 — Limpieza Inmediata (1-2 horas)

> Cosas rápidas que eliminan ruido y reducen riesgo sin cambiar lógica.

### 0.1 Templates duplicados de Colaboradores

**Problema**: Existen templates en `templates/colaboradores/` (root) que sombrean los de `colaboradores/templates/colaboradores/`. Django usa los del root primero por la configuración de `DIRS` en settings, lo que puede servir versiones desactualizadas.

**Archivos en root** (`templates/colaboradores/`):

- `colaborador_detail.html`
- `colaborador_form.html`
- `colaborador_list.html`
- `colaborador_side_over.html`
- `partials/colaborador_list_results.html`
- `partials/colaborador_list_table.html`
- `partials/detail_content.html`

**Acción**: Verificar cuál versión es la correcta (comparar contenido). Si los del root son los vigentes, mover a la app. Si son duplicados viejos, eliminar los del root.

**Riesgo si no se hace**: Bugs silenciosos donde editas un template en la app pero Django usa el del root.

---

### 0.2 Agregar `dispatch_uid` a signals

**Problema**: `dispositivos/signals.py` no usa `dispatch_uid`. Si la app se carga más de una vez (hot-reload, testing), los receivers se registran duplicados.

**Acción**:

```python
# dispositivos/apps.py → ready()
post_save.connect(handle_dispositivo_save, sender=Dispositivo, dispatch_uid='dispositivo_post_save')
```

**Impacto**: Prevención de doble-ejecución de signals.

---

### 0.3 Consolidar factories de testing

**Problema**: Existen 3 archivos de factories dispersos:

- `core/tests/factories.py`
- `colaboradores/tests/factories.py`
- `dispositivos/tests/factories.py`

Pueden tener defaults inconsistentes entre sí.

**Acción**: Auditar los 3 archivos. Si hay duplicación de `ColaboradorFactory` o `DispositivoFactory`, unificar en `core/tests/factories.py` como fuente principal (como dice AGENTS.md). Los otros archivos importan desde core.

---

### 0.4 Agregar entradas a `.gitignore`

**Acción**: Asegurar que estos patrones estén presentes:

```
scratch/
pytest_output.txt
stitch_*.html
query_test.py
skills-lock.json
*.sqlite3-journal
```

---

## Fase 1 — Robustez del Backend (P1, ~4-6 horas)

> Proteger la integridad de datos en operaciones multi-tabla.

### 1.1 `@transaction.atomic` en vistas de dispositivos

**Problema verificado**: `dispositivo_create` y `dispositivo_update` en `dispositivos/views.py` NO usan `transaction.atomic()`. Dado que la herencia multi-tabla (Dispositivo → Notebook/Smartphone/Monitor) implica escritura en 2+ tablas, un fallo parcial deja datos inconsistentes.

**Acción**: Envolver el bloque `if form.is_valid()` con `transaction.atomic()`:

```python
from django.db import transaction

@login_required
@permission_required('dispositivos.add_dispositivo', raise_exception=True)
def dispositivo_create(request):
    if request.method == 'POST':
        # ...
        with transaction.atomic():
            if form.is_valid():
                dispositivo = form.save()
                # guardar formulario técnico hijo
                # ...
```

**Archivos**: `dispositivos/views.py` (funciones `dispositivo_create`, `dispositivo_update`)

---

### 1.2 Manejo de errores en deletes

**Problema**: `dispositivo_delete` y `colaborador_delete` no capturan `IntegrityError`. Si un dispositivo tiene historial protegido con `PROTECT`, el delete crashea con 500 en vez de mostrar un mensaje amigable.

**Acción**:

```python
from django.db import IntegrityError

def dispositivo_delete(request, pk):
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    try:
        dispositivo.delete()
        # respuesta exitosa
    except IntegrityError:
        return HttpResponse(
            status=409,
            headers={'HX-Trigger': json.dumps({
                'showNotification': 'No se puede eliminar: tiene registros asociados.'
            })}
        )
```

**Archivos**: `dispositivos/views.py`, `colaboradores/views.py`

---

### 1.3 Refactorizar fat views (plan existente)

**Referencia**: Ya existe `docs/plan/refactor_dispositivos_views.md` con las 8 fases detalladas. El objetivo es extraer lógica de negocio a `dispositivos/services.py` (DispositivoFactory ya existe parcialmente).

**Prioridad dentro de esta fase**: Ejecutar las fases 1-5 del plan existente. Las fases 6-8 (testing y validación) van en Fase 3.

---

### 1.4 Service layer para módulos sin servicios

**Problema**: `dashboard`, `core` y `colaboradores` no tienen `services.py`. La lógica de negocio vive directamente en las views.

**Acción prioritaria** (solo lo crítico):

- `dashboard/services.py` — Ya existe pero tiene bug: queries de notebooks/smartphones disponibles ignoran `filtered_qs` (usan `Dispositivo.objects` directo). **Fix**: Cambiar a `filtered_qs.filter(...)`.
- `colaboradores/services.py` — Opcional por ahora, la lógica de baja lógica está en el modelo.

---

## Fase 2 — Seguridad y Auditoría (P1, ~3-4 horas)

> Preparar el sistema para un entorno de producción real.

### 2.1 Configurar sistema de logging

**Problema verificado**: No existe `LOGGING` en `settings.py`. Para un sistema que maneja actas legales y trazabilidad de activos, la falta de logging es crítica.

**Acción**: Agregar a `settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'inventario.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',
        },
        'dispositivos': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'actas': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'colaboradores': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
    },
}
```

Luego reemplazar `print()` statements por `logger.info()`/`logger.error()` en views y services.

---

### 2.2 Seguridad de cookies (producción)

**Problema**: `SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE` están en `False`. Sin HSTS.

**Acción** (condicional a producción):

```python
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_SSL_REDIRECT = True
    SECURE_BROWSER_XSS_FILTER = True
```

---

### 2.3 Validar SECRET_KEY al arranque

**Problema**: Si `SECRET_KEY` no está en `.env`, Django arranca con `None` como key.

**Acción**:

```python
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('Falta SECRET_KEY en las variables de entorno.')
```

---

### 2.4 Rate limiting en login (opcional)

**Problema**: Sin protección contra brute-force en `/auth/login/`.

**Opción ligera**: Usar `django-axes` o implementar un throttle manual con cache.

**Prioridad**: Media. Depende de si el sistema será accesible desde internet.

---

## Fase 3 — Calidad de Código y Testing (P2, ~6-8 horas)

> Mejorar la mantenibilidad y ampliar la red de seguridad.

### 3.1 Migrar `ColaboradorForm` a `BaseStyledForm`

**Problema**: `colaboradores/forms.py` hereda de `forms.ModelForm` y repite CSS en 9 widgets manualmente. Todos los demás formularios del sistema usan `BaseStyledForm` de `core/forms.py`.

**Acción**: Cambiar herencia a `BaseStyledForm`, quitar CSS inline, dejar solo placeholders.

---

### 3.2 Código duplicado en `core/views.py`

**Problema**: El CRUD de 5 catálogos (Fabricantes, Modelos, Tipos, CCs, Estados) es copy-paste de ~150 líneas repetidas.

**Acción**: Crear un mixin o vista genérica en `core/views.py`:

```python
class CatalogCRUDMixin:
    """Mixin genérico para CRUD de catálogos con HTMX."""
    model = None
    form_class = None
    list_template = None
    # ... lógica compartida
```

**Impacto**: Reduce ~150 líneas de código duplicado y facilita agregar nuevos catálogos.

---

### 3.3 Validadores de datos

**Problema**: Sin validación de RUT, IMEI, MAC address.

| Validador   | Ubicación                      | Prioridad                 |
| ----------- | ------------------------------- | ------------------------- |
| RUT chileno | `colaboradores/validators.py` | Alta (documentos legales) |
| IMEI        | `dispositivos/validators.py`  | Media                     |
| MAC address | `dispositivos/validators.py`  | Baja                      |

**Acción RUT** (prioritaria):

```python
# colaboradores/validators.py
from django.core.exceptions import ValidationError
import re

def validar_rut(value):
    """Valida formato y dígito verificador de RUT chileno."""
    rut = re.sub(r'[.\-]', '', value).upper()
    if len(rut) < 2:
        raise ValidationError('RUT inválido.')
    cuerpo, dv = rut[:-1], rut[-1]
    # ... algoritmo módulo 11
```

---

### 3.4 Ampliar cobertura de tests

**Estado actual**: ~10 de ~25+ views testeadas. Faltan:

- CRUD completo de dispositivos (create, update, delete)
- Dispositivos especializados (Notebook, Smartphone, Monitor)
- Exportación Excel
- QR code generation
- Permisos (verificar 403 para roles no autorizados)
- Formularios con datos inválidos

**Acción**: Crear tests organizados por prioridad:

```
tests/
├── test_dispositivos_crud.py      # P1: create, update, delete
├── test_dispositivos_permisos.py  # P1: 403 para no autorizados
├── test_dispositivos_especializados.py  # P2: Notebook, Smartphone
├── test_exportacion.py            # P2: Excel export
├── test_qr.py                     # P3: QR generation
```

---

### 3.5 Aplicar marcadores pytest

**Problema**: Los markers `@pytest.mark.unit` e `@pytest.mark.integration` están definidos pero nunca se usan en tests.

**Acción**: Agregar markers a todos los tests existentes. Ejemplo:

```python
@pytest.mark.unit
def test_dispositivo_str():
    ...

@pytest.mark.integration
def test_dispositivo_create_view():
    ...
```

Esto permite ejecutar `pytest -m unit` para feedback rápido.

---

## Fase 4 — Optimización y Performance (P2-P3, ~4-6 horas)

> Preparar para crecimiento de datos y múltiples usuarios.

### 4.1 `select_related` en listado de dispositivos

**Problema verificado**: La respuesta de `/dispositivos/listado/` pesa **479KB**. Esto sugiere que la tabla carga todos los dispositivos sin paginación y/o sin `select_related`.

**Acción**:

```python
dispositivos = Dispositivo.objects.select_related(
    'tipo', 'modelo', 'modelo__fabricante', 'estado',
    'propietario_actual', 'centro_costo'
).all()
```

---

### 4.2 Paginación

**Problema**: Listados grandes sin paginación degradarán el rendimiento con miles de dispositivos.

**Acción**: Implementar paginación HTMX:

- Server: `Paginator(queryset, 25)` en views
- Client: `hx-get` con `?page=N` en botón "Cargar más" o scroll infinito
- Alternativa: Paginación clásica con números de página

---

### 4.3 Build step de Tailwind CSS

**Problema**: Tailwind se carga vía CDN Play (~200KB+ sin tree-shaking). En producción:

- Payload innecesariamente grande
- Dependencia de CDN externo (si se cae, el sitio pierde estilos)
- Sin purge de clases no usadas

**Acción**:

```bash
npm init -y
npm install -D tailwindcss
npx tailwindcss init
# Configurar tailwind.config.js con los tokens de STYLE_GUIDE.md
# Build: npx tailwindcss -i ./static/css/input.css -o ./static/css/output.css --minify
```

**Resultado esperado**: CSS de ~200KB+ → ~15-30KB.

**Prioridad**: P3 (funciona bien en desarrollo con CDN, pero es requisito para producción).

---

### 4.4 Caché del dashboard

**Problema**: Las queries del dashboard se ejecutan en cada request sin caché.

**Acción** (ligera):

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # 5 minutos
def dashboard_home(request):
    ...
```

O usar `django.core.cache` con invalidación manual en signals de dispositivo.

---

## Fase 5 — Migración a PostgreSQL (P3, ~2-3 horas)

> Resolver limitaciones estructurales de SQLite.

### 5.1 Por qué migrar

| Problema SQLite             | Solución PostgreSQL                            |
| --------------------------- | ----------------------------------------------- |
| Sin escrituras concurrentes | Soporte multi-writer                            |
| Race condition en folios    | `select_for_update()` con row-level locking   |
| Sin índices parciales      | Índices condicionales para queries optimizadas |
| Sin full-text search        | `SearchVector` + `SearchRank` nativo        |
| Sin backup incremental      | `pg_dump` + WAL archiving                     |

### 5.2 Pasos

1. Instalar PostgreSQL y `psycopg[binary]`
2. Crear base de datos: `CREATE DATABASE inventario_jmie;`
3. Configurar `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'inventario_jmie'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}
```

1. Migrar datos: `python manage.py dumpdata > backup.json` → `python manage.py loaddata backup.json`
2. Agregar `select_for_update()` en generación de folios y IDs

---

## Fase 6 — Dashboard Refinamiento (P2, ~3-4 horas)

> Completar la única épica al 95%.

### 6.1 Estado actual (HU-26)

Los gráficos base (Chart.js + Alpine.js) están implementados con drill-down interactivo. Falta:

- Drill-down más granular (click en barra → filtrar tabla)
- Toggle entre vista por Centro de Costo y por Departamento
- Exportación de métricas filtradas

### 6.2 Fix de queries del dashboard

**Bug verificado**: Las queries de "Notebooks disponibles" y "Smartphones disponibles" en `dashboard/services.py` usan `Dispositivo.objects` en vez de `filtered_qs`, ignorando los filtros del dashboard.

---

## Fase 7 — Preparación para Producción (P3, ~4-6 horas)

> Checklist final antes del despliegue.

### 7.1 CI/CD Pipeline

- [ ] Crear `GitHub Actions` workflow:
  - Lint (flake8/ruff)
  - Tests (`pytest -m "not e2e"`)
  - Security scan (`pip-audit`)
  - Django check (`manage.py check --deploy`)

### 7.2 Documentación de usuario

- [ ] Manual de usuario básico con capturas
- [ ] Guía de instalación para IT
- [ ] Procedimiento de backup y restore

### 7.3 Despliegue

- [ ] Decidir hosting (VPS, Docker, PaaS)
- [ ] Configurar Gunicorn/uWSGI
- [ ] Nginx como reverse proxy
- [ ] Certificado SSL (Let's Encrypt)
- [ ] Monitoreo básico (uptime, errores)

---

## Cronograma Sugerido

| Semana | Fase                                         | Esfuerzo |
| ------ | -------------------------------------------- | -------- |
| 1      | Fase 0 (Limpieza) + Fase 2.1-2.3 (Seguridad) | ~5h      |
| 1-2    | Fase 1 (Robustez backend)                    | ~5h      |
| 2      | Fase 3.1-3.3 (Calidad código)               | ~4h      |
| 3      | Fase 4.1-4.2 (Performance)                   | ~4h      |
| 3      | Fase 6 (Dashboard)                           | ~3h      |
| 4      | Fase 3.4-3.5 (Testing)                       | ~5h      |
| 4-5    | Fase 5 (PostgreSQL)                          | ~3h      |
| 5      | Fase 4.3 (Tailwind build)                    | ~2h      |
| 6      | Fase 7 (Producción)                         | ~5h      |

**Total estimado**: ~36 horas de trabajo

---

## Matriz de Prioridad vs Impacto

```
                    IMPACTO ALTO                    IMPACTO BAJO
              ┌─────────────────────────────┬───────────────────────────┐
              │                             │                           │
  ESFUERZO    │  ★ dispatch_uid (0.2)       │  Marcadores pytest        │
  BAJO        │  ★ Fix dashboard queries    │  .gitignore               │
              │  ★ SECRET_KEY validación    │  Renombrar acta_crear     │
              │                             │                           │
              ├─────────────────────────────┼───────────────────────────┤
              │                             │                           │
  ESFUERZO    │  ★★ transaction.atomic      │  CRUD genérico core       │
  MEDIO       │  ★★ Logging config          │  Tailwind build step      │
              │  ★★ Templates duplicados    │  Validador RUT            │
              │  ★★ Manejo errores deletes  │                           │
              │                             │                           │
              ├─────────────────────────────┼───────────────────────────┤
              │                             │                           │
  ESFUERZO    │  ★★★ PostgreSQL migration   │  CI/CD pipeline           │
  ALTO        │  ★★★ Refactor fat views     │  Manual de usuario        │
              │  ★★★ Ampliar tests          │                           │
              │                             │                           │
              └─────────────────────────────┴───────────────────────────┘
```

> **Recomendación**: Empezar por las ★ (alto impacto, bajo esfuerzo) y avanzar diagonalmente.

---

## Relación con Documentos Existentes

| Documento                                    | Relación con este plan                                                                               |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `FODA.md`                                  | Este plan implementa las acciones priorizadas del FODA                                                |
| `product_backlog.md`                       | Las 28 HUs están al 95%. Solo HU-26 requiere trabajo                                                 |
| `hu_verification_status.md`                | Confirma el estado de completitud por épica                                                          |
| `plan/Plan de Corrección Post-Auditoría` | Muchos items ya resueltos (DEBUG, ALLOWED_HOSTS, MCP/DRF removidos). Este plan actualiza lo pendiente |
| `plan/refactor_fat_views.md`               | Se incorpora como Fase 1.3 de este plan                                                               |
| `plan/refactor_dispositivos_views.md`      | Detalle granular de la Fase 1.3                                                                       |
| `STYLE_GUIDE.md`                           | Referencia para cualquier cambio de frontend                                                          |
| `ARQUITECTURA_TECNICA.md`                  | Referencia para entender decisiones de diseño                                                        |

---

*Plan generado el 24 de abril de 2026. Actualizar conforme se avance en las fases.*
