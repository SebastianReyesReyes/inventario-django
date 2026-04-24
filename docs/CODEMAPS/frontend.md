# Frontend Codemap

**Last Updated:** 2026-04-24
**Entry Points:** `templates/base.html`, `core/templates/core/`

## Architecture

```
templates/
├── base.html                    # Layout principal (sidebar, navbar, containers)
├── auth/                        # Login, logout
├── colaboradores/               # Templates de colaboradores
│   ├── colaborador_list.html
│   ├── colaborador_form.html
│   └── partials/                # HTMX partials
└── cotton/                      # Componentes reutilizables (django-cotton)
    ├── btn_primary.html
    ├── empty_state.html
    ├── form_label.html
    ├── glass_panel.html
    ├── htmx_loader.html
    ├── page_header.html
    ├── search_input.html
    ├── th.html
    └── th_sort.html

core/templates/core/
├── base_catalogo.html           # Template base para catálogos
├── home.html                    # Página principal
├── *_list.html                  # Listados de catálogos
└── partials/                    # Partials HTMX

dispositivos/templates/dispositivos/
├── dispositivo_list.html        # Listado con filtros HTMX
├── dispositivo_detail.html      # Detalle con side-over
├── dispositivo_form.html        # Formulario creación/edición
└── partials/                    # HTMX partials (tabla, confirm delete, etc.)

actas/templates/actas/
├── acta_list.html               # Listado paginado
└── partials/                    # Modales, tablas, error blocks

dashboard/templates/dashboard/
├── index.html                   # Dashboard principal
├── reportes.html                # Página de reportes
└── partials/                    # Chart.js containers, drill-down
```

## UI Layer Stack

```
┌─────────────────────────────────────────────┐
│              Tailwind CSS                    │
│   Utility classes, responsive, dark mode    │
├─────────────────────────────────────────────┤
│              Alpine.js                       │
│   Modales, tooltips, estados visuales       │
│   x-data, x-show, x-on, x-model             │
├─────────────────────────────────────────────┤
│              HTMX                            │
│   hx-get, hx-post, hx-target, hx-swap       │
│   hx-trigger, hx-push-url, hx-confirm       │
├─────────────────────────────────────────────┤
│          Django Templates                    │
│   {% block %}, {% include %}, {% cotton %}  │
│   Custom templatetags (ui_tags, nav_tags)   │
└─────────────────────────────────────────────┘
```

## HTMX Patterns

| Pattern | Implementation | Location |
|---------|---------------|----------|
| **Side-over** | `#side-over-container` para detalles rápidos | `base.html` |
| **Modales** | `#modal-container` para formularios de acción | `base.html` |
| **Auto-sanación** | Listener re-crea contenedores si HTMX los elimina | `base.html` |
| **Tabla refresh** | `hx-swap="innerHTML"` en `<tbody>` | `*_list_table.html` |
| **Drill-down** | Charts → click → lista filtrada en modal | `dashboard/partials/` |
| **Lazy load** | Historial/accesorios cargados on-demand | `dispositivos/partials/` |

## Cotton Components

| Component | Purpose | Props |
|-----------|---------|-------|
| `btn_primary` | Botón primario estilizado | `href`, `type`, `hx_*` attrs |
| `empty_state` | Estado vacío con mensaje | `message`, `icon` |
| `form_label` | Label consistente para formularios | `for`, `text`, `required` |
| `glass_panel` | Panel con efecto glassmorphism | `class` |
| `htmx_loader` | Indicador de carga HTMX | `target` |
| `page_header` | Encabezado de página con título y acciones | `title`, `actions` |
| `search_input` | Input de búsqueda con HTMX | `hx_get`, `placeholder` |
| `th` | Header de tabla | `text`, `sortable` |
| `th_sort` | Header de tabla ordenable | `field`, `current_sort`, `current_order` |

## Key Template Tags

| Tag | Module | Purpose |
|-----|--------|---------|
| `{% render_actions %}` | `action_tags.py` | Renderiza botones CRUD basados en URL naming convention |
| `{% active_nav %}` | `nav_tags.py` | Marca item de navegación activo |
| `{% ui_component %}` | `ui_tags.py` | Renderiza componentes UI reutilizables |
| `{% url_modify %}` | `url_tags.py` | Modifica parámetros de URL manteniendo el resto |

## JavaScript Dependencies

- **HTMX** - Interactividad sin JS custom
- **Alpine.js** - Estado local (modales, dropdowns)
- **Chart.js** - Gráficos del dashboard
- **Material Symbols** - Iconografía

## Related Areas

- [Backend Codemap](backend.md) - Vistas que renderizan templates
- [General Codemap](general.md) - Configuración global
