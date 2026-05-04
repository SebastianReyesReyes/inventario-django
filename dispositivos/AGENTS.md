# dispositivos — AGENTS.md

## OVERVIEW
Inventario polimórfico de equipos TI, con trazabilidad completa (asignaciones, reasignaciones, devoluciones), mantenimientos, accesorios y códigos QR.

## STRUCTURE
```
dispositivos/
├── models.py              # Dispositivo (polimórfico), Notebook, Smartphone, Monitor, etc.
├── views.py               # 523 líneas — CRUD + trazabilidad + AJAX + QR (COMPLEJO)
├── services.py            # DispositivoFactory, TrazabilidadService
├── forms.py               # Formularios por tipo de dispositivo
├── urls.py                # Names obligatorios: dispositivo_list, dispositivo_asignar, etc.
├── templates/dispositivos/
│   ├── dispositivo_*.html # CRUD templates
│   └── partials/          # HTMX partials (17 archivos)
├── tests/                 # factories.py, test_integration.py (cross-app), test_edge_cases.py
└── migrations/
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Crear/editar dispositivo | `dispositivos/views.py` | Usa `tech_forms` dict para campos específicos por tipo |
| Asignar/reasignar/devolver | `dispositivos/views.py:40-100` | Envuelve en `transaction.atomic()` |
| Historial trazabilidad | `dispositivos/views.py` | `dispositivo_historial` con timeline |
| Generar QR | `dispositivos/views.py` | `dispositivo_qr` — renderiza template para escaneo |
| Mantenimiento | `dispositivos/views.py` | `mantenimiento_create`, `mantenimiento_update` |
| Accesorios | `dispositivos/views.py` | `colaborador_entrega_accesorio` |
| Service layer | `dispositivos/services.py` | `TrazabilidadService` para lógica compleja |
| QuerySet optimizado | `dispositivos/models.py` | `DispositivoQuerySet.con_detalles()` — patrón N+1 |
| Tests cross-app | `dispositivos/tests/test_integration.py` | Flujo completo: asignar → acta → dashboard |

## CONVENTIONS
- **Polimorfismo**: `Dispositivo` base con especializaciones (Notebook, Smartphone, etc.)
- **Identificadores**: Formato `JMIE-SIGLA-00001` via Django Constance
- **Trazabilidad**: `HistorialAsignacion` registra cada cambio de custodia
- **QR**: Generación dinámica por equipo para escaneo rápido
- **Soft delete**: `Colaborador.delete()` desactiva, no borra

## ANTI-PATTERNS
- **NUNCA** tocar `dispositivos/views.py` sin considerar dividir en módulos (ya tiene 523 líneas)
- **NUNCA** omitir `select_related()` / `prefetch_related()` en listados con relaciones
- **NUNCA** generar acta fuera de `transaction.atomic()` — usar bloque atómico separado
- **NUNCA** hardcodear estados — usar `EstadoDispositivoFactory` o constants

## COMPLEXITY NOTES
- `views.py` es el archivo más grande del proyecto (523 líneas). Contiene 17 funciones de vista mezclando CRUD, AJAX, trazabilidad, mantenimiento y accesorios. Considerar dividir en `views_crud.py`, `views_trazabilidad.py`, `views_ajax.py`.
