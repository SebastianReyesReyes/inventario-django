# Backend Codemap

**Last Updated:** 2026-04-24
**Entry Points:** `dispositivos/views.py`, `actas/views.py`, `colaboradores/views.py`, `dashboard/views.py`

## Architecture

```
Views (HTTP Layer)
    │
    ├── Forms (Validation)
    │       └── core.forms.BaseStyledForm
    │
    └── Services (Business Logic)
            ├── ActaService (actas/services.py)
            ├── DispositivoFactory (dispositivos/services.py)
            └── TrazabilidadService (dispositivos/services.py)
                    │
                    └── ORM (models.py)
                            └── SQLite
```

## Key Modules - Dispositivos

| Module | Purpose | Key Functions | Dependencies |
|--------|---------|---------------|--------------|
| `dispositivos/views.py` | CRUD + trazabilidad | `dispositivo_create`, `dispositivo_list`, `dispositivo_detail`, `dispositivo_update`, `dispositivo_delete`, `dispositivo_asignar`, `dispositivo_reasignar`, `dispositivo_devolver`, `mantenimiento_create`, `colaborador_entrega_accesorio`, `dispositivo_qr` | DispositivoFactory, TrazabilidadService, ActaService |
| `dispositivos/services.py` | Factory + trazabilidad | `DispositivoFactory.create_form_instance()`, `TrazabilidadService.asignar()`, `TrazabilidadService.reasignar()`, `TrazabilidadService.devolver()`, `TrazabilidadService.entregar_accesorio()` | Dispositivo, HistorialAsignacion, EntregaAccesorio |
| `dispositivos/forms.py` | Formularios técnicos | `NotebookTechForm`, `SmartphoneTechForm`, `MonitorTechForm`, `MantenimientoForm`, `AsignacionForm`, `ReasignacionForm`, `DevolucionForm`, `AccesorioForm` | BaseStyledForm |
| `dispositivos/models.py` | Modelos de inventario | `Dispositivo`, `Notebook`, `Smartphone`, `Impresora`, `Servidor`, `EquipoRed`, `Monitor`, `BitacoraMantenimiento`, `HistorialAsignacion`, `EntregaAccesorio` | core.models, Colaborador |

## Key Modules - Actas

| Module | Purpose | Key Functions | Dependencies |
|--------|---------|---------------|--------------|
| `actas/views.py` | CRUD actas + PDF | `acta_list`, `acta_create`, `acta_detail`, `acta_pdf`, `acta_firmar`, `asignaciones_pendientes`, `ministros_por_colaborador` | ActaService |
| `actas/services.py` | Lógica de actas | `ActaService.crear_acta()`, `ActaService.obtener_acta_con_relaciones()`, `ActaService.generar_pdf()`, `ActaService.firmar_acta()`, `ActaService.obtener_pendientes()`, `ActaService.obtener_accesorios_pendientes()` | Acta, HistorialAsignacion, EntregaAccesorio |
| `actas/forms.py` | Formularios de actas | `ActaCrearForm` | BaseStyledForm |
| `actas/models.py` | Modelo Acta | `Acta` (folio, tipo_acta, colaborador, firmado, metodo_sanitizacion, ministro_de_fe) | Colaborador |

## Key Modules - Colaboradores

| Module | Purpose | Key Functions | Dependencies |
|--------|---------|---------------|--------------|
| `colaboradores/views.py` | Gestión de personal | CRUD Colaborador, detail con historial | Colaborador model |
| `colaboradores/forms.py` | Formularios | `ColaboradorForm` (hereda BaseStyledForm) | Colaborador model |
| `colaboradores/models.py` | AUTH_USER_MODEL | `Colaborador` (extends AbstractUser) | django.contrib.auth |

## Key Modules - Dashboard

| Module | Purpose | Key Functions | Dependencies |
|--------|---------|---------------|--------------|
| `dashboard/views.py` | Métricas y reportes | `dashboard_index`, `reportes` | Dashboard services, filters |
| `dashboard/services.py` | Cálculo de métricas | Contadores, agregaciones | Dispositivo, HistorialAsignacion |
| `dashboard/filters.py` | Filtros analíticos | `AnaliticaInventarioFilter` | django-filter |

## Key Modules - Core

| Module | Purpose | Key Functions | Dependencies |
|--------|---------|---------------|--------------|
| `core/htmx.py` | Helpers HTMX | `htmx_trigger_response`, `htmx_render_or_redirect`, `htmx_success_or_redirect`, `htmx_redirect_or_redirect`, `is_htmx` | django_htmx |
| `core/views.py` | Home + errores | `home`, `error_403`, `error_404`, `error_500` | - |
| `core/management/commands/import_devices.py` | Importación CSV | `Command.handle()` con `--dry-run` | Dispositivo, TipoDispositivo |
| `core/models.py` | Catálogos base | `Fabricante`, `TipoDispositivo`, `EstadoDispositivo`, `Modelo`, `CentroCosto` | - |

## HTMX Response Helpers

```python
# core/htmx.py
htmx_trigger_response(event_name)        # 204 + HX-Trigger
htmx_render_or_redirect(request, tmpl, ctx, redirect_url, trigger)  # HTMX o redirect
htmx_success_or_redirect(request, redirect_url, trigger)   # 204 + HX-Trigger + redirect
htmx_redirect_or_redirect(request, redirect_url)           # Redirect siempre
is_htmx(request)                                           # Check HX-Request header
```

## Transaction Patterns

```python
# Patrón: escritura principal + operación secundaria que puede fallar
with transaction.atomic():
    dispositivo = form.save()  # Escritura principal

# Bloque separado para operación que puede fallar
if generar_acta:
    with transaction.atomic():
        acta = ActaService.crear_acta(...)  # Si falla, no revierte dispositivo
```

## External Dependencies

- Django 6.0.2
- django-htmx 1.27.0
- django-filter 25.2
- django-constance 4.3.5
- django-cotton 2.6.2
- qrcode 8.2
- playwright 1.58.0
- pyHanko 0.33.0
- pypdf 6.7.2

## Related Areas

- [Database Codemap](database.md) - Modelos detallados
- [Frontend Codemap](frontend.md) - Templates
- [Integrations Codemap](integrations.md) - PDF, QR, MCP
