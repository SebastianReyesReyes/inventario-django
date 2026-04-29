date: 2026-04-28
topic: "Paginación AJAX (HTMX) en Tablas de Inventario"
status: draft

# Problem Statement

Las tablas de listado en las aplicaciones `dispositivos`, `colaboradores` y `core` (catálogos) actualmente renderizan **todos los registros** en una sola vista. Esto genera:
- **Páginas lentas** con grandes volúmenes de datos.
- **Alta carga de red y memoria** al transferir HTML masivo.
- **Mala experiencia de usuario** al intentar navegar listas muy largas.

El objetivo es agregar **paginación truncada** (10 o 20 registros por página) con navegación **AJAX vía HTMX**, sin recargar la página completa, aprovechando la infraestructura HTMX y partials que ya existe en el proyecto.

# Constraints

- **No se puede cambiar la arquitectura base**: Las vistas son principalmente FBV (Function-Based Views) y deben seguir siéndolo.
- **Naming de URLs obligatorio**: `[model_name]_[action]` (ej. `dispositivo_list`). No modificar nombres de URLs existentes.
- **HTMX + partials**: La respuesta para peticiones HTMX debe seguir siendo un template parcial que reemplace `#tabla-wrapper`.
- **Preservar filtros**: Al cambiar de página se deben mantener los parámetros de búsqueda y ordenamiento activos (usar `query_transform`).
- **Consistencia visual**: El paginador debe usar Tailwind CSS y encajar con el sistema de glassmorphism/diseño existente.
- **Paginación truncada inteligente**: No mostrar todos los números de página si hay muchos; mostrar rango cercano a la página actual con elipses.
- **Fallback seguro**: Página inválida (string, negativa, > total) debe redirigir a la primera página, no generar 500.

# Approach

## Opción A: Paginador como componente Cotton reutilizable
Crear `<c-paginator>` que reciba `page_obj` y genere enlaces HTMX. Esto asegura consistencia y mínima duplicación de código.

## Opción B: Snippet de template en cada app
Incluir un bloque de paginación directamente en cada `*_list_table.html`. Más rápido de implementar inicialmente, pero genera duplicación y es difícil de mantener si cambia el diseño.

## Opción C: Paginación via JavaScript/Alpine.js
Usar Alpine.js para ocultar/mostrar filas localesmente. **Rechazada**: No reduce carga inicial de servidor ni de red; no escala para miles de registros.

**Decisión:** Opción A. El proyecto ya usa Cotton extensivamente y un componente reutilizable es la mejor inversión a largo plazo.

# Architecture

## Componentes

### 1. Componente Cotton `<c-paginator>`
- **Archivo**: `templates/cotton/paginator.html`
- **Responsabilidad**: Renderizar controles de paginación (Anterior, números de página truncados, Siguiente) como enlaces `<a>` con atributos HTMX.
- **Props**:
  - `page`: El objeto `page` del Paginator de Django.
  - `target`: Selector HTMX para `hx-target` (default: `#tabla-wrapper`).
  - `push_url`: Booleano para `hx-push-url` (default: `true`).
- **Lógica interna**:
  - Si `page.paginator.num_pages == 1`, no renderizar nada.
  - Calcular rango de páginas visibles (ej. actual ± 2).
  - Mostrar `1` siempre; si el rango no empieza en 2, mostrar `...`.
  - Mostrar última página siempre; si el rango no llega a `num_pages - 1`, mostrar `...`.
  - Cada enlace usa `{% query_transform page=page_number %}` para mantener filtros.
  - Atributos HTMX: `hx-get="{{ request.path }}?{{ querystring }}" hx-target="{{ target }}" hx-swap="innerHTML" hx-push-url="{{ push_url }}"`.

### 2. Actualización de Vistas (FBV)
- **Responsabilidad**: Instanciar `Paginator` y manejar excepciones de página inválida.
- **Patrón común** (aplicable a todas las vistas de listado):
  ```python
  from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

  def lista_generica(request, queryset, items_por_pagina=10):
      paginator = Paginator(queryset, items_por_pagina)
      page_number = request.GET.get('page')
      try:
          page_obj = paginator.get_page(page_number)
      except (EmptyPage, PageNotAnInteger):
          page_obj = paginator.page(1)
      return page_obj
  ```
- **Apps a modificar**:
  - `dispositivos/views.py` (`dispositivo_list`)
  - `colaboradores/views.py` (`colaborador_list`)
  - `core/views.py` (`fabricante_list`, `modelo_list`, `tipo_list`, `cc_list`, `estado_list`, `departamento_list`)
  - `actas/views.py` (ya usa paginación backend; solo agregar controles en template)

### 3. Actualización de Templates Parciales
- **Responsabilidad**: Incluir `<c-paginator />` dentro del partial de tabla para que HTMX lo renderice junto con las filas.
- **Archivos a modificar** (ejemplos):
  - `dispositivos/templates/dispositivos/partials/dispositivo_list_table.html`
  - `colaboradores/templates/colaboradores/partials/colaborador_list_table.html`
  - `core/templates/core/partials/catalogo_list_table.html` (o equivalente por catálogo)
- **Nota**: El `queryset` iterado en el tbody debe cambiar de `object_list`/`queryset` a `page_obj`.

### 4. Template Tag `query_transform` (ya existe)
- **Archivo**: `core/templatetags/url_tags.py`
- **Uso**: Los enlaces del paginador usarán `{% query_transform page=N %}` para preservar `q`, `sort`, `order`, etc.

## Data Flow

1. **Carga inicial (no HTMX)**:
   - El usuario accede a `/dispositivos/listado/`.
   - La vista devuelve `dispositivo_list.html` completo.
   - Dentro de `dispositivo_list.html`, `#tabla-wrapper` carga `dispositivo_list_table.html` via `{% include %}`.
   - La tabla muestra las primeras 10 filas y el componente `<c-paginator page=page_obj />`.

2. **Navegación AJAX (HTMX)**:
   - El usuario clickea página 3.
   - HTMX dispara `GET /dispositivos/listado/?page=3&q=laptop&sort=nombre`.
   - La vista detecta `HX-Request`, aplica filtros, pagina al queryset y devuelve `dispositivo_list_table.html`.
   - HTMX reemplaza `#tabla-wrapper` con el nuevo HTML (filas + paginador actualizado).
   - La URL del navegador se actualiza gracias a `hx-push-url="true"`.

## Error Handling Strategy

- **Página inválida**: Capturar `PageNotAnInteger` y `EmptyPage` para devolver página 1 en lugar de 500. Loggear como warning.
- **Sin resultados**: Si el queryset filtrado está vacío, `Paginator` devuelve 1 página vacía. El template ya maneja el `empty_state`.
- **Timeout de red**: HTMX maneja el retry por defecto; el loader de `<c-glass-panel>` da feedback visual.

## Testing Strategy

- **Unit Tests (pytest)**:
  - Verificar que la vista `dispositivo_list` devuelve `page_obj` en el contexto.
  - Verificar que `page="abc"` o `page="999"` cae en página 1 sin error.
  - Verificar que el número de items por página es exactamente 10 (o 20 según app).

- **Integration Tests**:
  - Realizar GET a `/dispositivos/listado/?page=2&q=laptop` y confirmar que el queryset paginado filtra primero y luego pagina.

- **E2E Tests (Playwright)**:
  - Navegar a la lista de dispositivos.
  - Aplicar un filtro de búsqueda.
  - Clickear página 2.
  - Assert: URL contiene `page=2` y `q=...`.
  - Assert: La tabla muestra registros diferentes y el indicador de página activa es 2.
  - Assert: No hay recarga completa de página (verificar que el sidebar no se re-renderice o que no haya `networkidle` global).

## Open Questions

- **Items por página**: ¿Es 10 universal o varía por app? (Asumiré 10 para catálogos y 20 para dispositivos/colaboradores, que suelen tener más volumen).
- **¿Incluir selector de "Items por página"?** (Ej. dropdown para elegir 10/20/50). Por ahora, no. Es un nice-to-have que se puede agregar después sin romper el diseño.
- **¿Afecta a exportación Excel/CSV?** La exportación debe seguir exportando el queryset completo (no paginado). Asegurarse de que el parámetro `page` no interfiera con la lógica de exportación si comparte la misma vista.

## Plan de Implementación Sugerido

1. Crear `templates/cotton/paginator.html`.
2. Crear helper Python opcional `core/pagination.py` con función `paginate_queryset(request, queryset, per_page)` para evitar repetir lógica en cada FBV.
3. Modificar vistas:
   - `dispositivos/views.py`
   - `colaboradores/views.py`
   - `core/views.py`
4. Modificar templates parciales de tabla para iterar `page_obj` e incluir `<c-paginator />`.
5. Modificar `actas` para agregar el paginador visual (si aplica).
6. Ejecutar tests y verificar flujo E2E.
