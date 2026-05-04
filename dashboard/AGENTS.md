# dashboard — AGENTS.md

## OVERVIEW
Métricas analíticas, gráficos Chart.js con drill-down, filtros dinámicos y exportación Excel/CSV.

## STRUCTURE
```
dashboard/
├── views.py               # Dashboard principal, métricas, exportaciones
├── services.py            # DashboardMetricsService — agregaciones y cálculos
├── urls.py                # Names: dashboard_index, dashboard_export, etc.
├── templates/dashboard/   # Templates con Chart.js y filtros
├── tests/                 # Tests de métricas y exportación
└── migrations/            # Vacío — dashboard no tiene modelos propios
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Ver métricas | `dashboard/views.py` | `dashboard_index` — contexto con métricas calculadas |
| Exportar Excel/CSV | `dashboard/views.py` | `dashboard_export` — genera archivo y devuelve response |
| Gráficos drill-down | `dashboard/templates/dashboard/` | Chart.js con links a listados filtrados |
| Cálculos complejos | `dashboard/services.py` | `DashboardMetricsService` — agregaciones ORM |
| Filtros | `dashboard/views.py` | Reutiliza filtros de `dispositivos` |

## CONVENTIONS
- **Sin modelos**: Dashboard opera sobre `dispositivos.models` (no tiene `models.py` propio)
- **Service layer**: Métricas complejas en `DashboardMetricsService`, no en views
- **Exportación**: Respuesta HTTP con `Content-Disposition: attachment`
- **Drill-down**: Links de gráficos apuntan a listados con query params pre-filtrados

## ANTI-PATTERNS
- **NUNCA** crear modelos en dashboard — usar `dispositivos.models` directamente
- **NUNCA** calcular métricas en views — delegar a `DashboardMetricsService`
- **NUNCA** hardcodear query params en drill-down — usar `reverse()` + query strings
