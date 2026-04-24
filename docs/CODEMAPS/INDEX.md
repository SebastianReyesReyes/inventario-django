# CODEMAPS - Inventario JMIE

**Last Updated:** 2026-04-24

Mapas arquitectónicos del sistema de inventario JMIE, generados a partir del código fuente real.

## Índice de Mapas

| Mapa | Descripción | Enlace |
|------|-------------|--------|
| **General** | Vista completa del sistema y relaciones entre apps | [general.md](general.md) |
| **Frontend** | Templates, componentes Cotton, HTMX, Alpine.js | [frontend.md](frontend.md) |
| **Backend/API** | Vistas, servicios, URLs, formularios | [backend.md](backend.md) |
| **Database** | Modelos, relaciones, constraints | [database.md](database.md) |
| **Integrations** | Servicios externos, PDF, QR, MCP | [integrations.md](integrations.md) |

## Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                        Navegador (Cliente)                       │
│   HTMX requests ←→ Alpine.js interactivity ←→ Tailwind CSS      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/HTMX
┌──────────────────────────▼──────────────────────────────────────┐
│                     Django 6.0.2 (SSR)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  core    │  │colaborad.│  │dispositiv.│  │     actas        │ │
│  │catálogos │  │  AUTH    │  │inventario│  │  actas PDF       │ │
│  │htmx utils│  │  users   │  │mantenim. │  │  folios legales  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
│       │              │             │                 │            │
│  ┌────▼──────────────▼─────────────▼─────────────────▼────────┐  │
│  │                    dashboard                                │  │
│  │              métricas, filtros, reportes                    │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │              Service Layer (services.py)                   │  │
│  │   ActaService │ DispositivoFactory │ TrazabilidadService   │  │
│  └───────────────────────────┬───────────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   SQLite (db.sqlite3)│
                    │   Django ORM         │
                    └─────────────────────┘
```

## Flujo de Datos Principal

1. **Usuario interactúa** con la UI (click, form submit)
2. **HTMX envía request** parcial al servidor
3. **Django view** recibe, valida con forms, delega a services
4. **Service layer** ejecuta lógica de negocio con `transaction.atomic()`
5. **ORM** persiste en SQLite
6. **View retorna** HTML parcial (no JSON)
7. **HTMX swap** actualiza el DOM

## Convenciones Globales

- **URLs:** `[app]/[model]_[action]` (requerido por `{% render_actions %}`)
- **HTMX:** Usar helpers `core/htmx.py` (`htmx_trigger_response`, `htmx_render_or_redirect`, etc.)
- **Transacciones:** Bloques separados para operaciones que pueden fallar independientemente
- **Logging:** Loggers por app → `inventario.log`
