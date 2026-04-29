# Plan de Implementación: Paginación AJAX (HTMX) en Tablas de Inventario

**Fecha:** 2026-04-28
**Diseño base:** `thoughts/shared/designs/2026-04-28-paginacion-ajax-tablas-design.md`
**Objetivo:** Agregar paginación truncada (10/20 ítems por página) con navegación AJAX vía HTMX a todas las tablas de listado del sistema, sin recargar la página completa.

---

## Resumen de Arquitectura

- **Componente reutilizable Cotton `<c-paginator>`**: Renderiza controles de paginación truncada con enlaces HTMX. Recibe `page`, `target` y `push_url`.
- **Helper `core/pagination.py`**: Función `paginate_queryset(request, queryset, per_page)` para evitar duplicar lógica de `Paginator` + manejo de errores en cada FBV.
- **Patrón HTMX**: Las peticiones AJAX reemplazan `#tabla-wrapper` (o `#catalogo-list-container` en catálogos) con un partial que incluye tabla + paginador. Los enlaces del paginador usan `{% query_transform page=N %}` para preservar filtros activos.
- **Items por página**: 20 para `dispositivos` y `colaboradores` (alto volumen), 10 para `core` catálogos y `actas`.

---

## Fase 1: Infraestructura Core (Independiente)

### Paso 1.1: Crear helper de paginación `core/pagination.py`
**Archivo:** `core/pagination.py` (nuevo)
**Qué hacer:**
Crear una función utilitaria que envuelva la lógica repetida de `Paginator` + manejo de páginas inválidas.

```python
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

logger = logging.getLogger(__name__)


def paginate_queryset(request, queryset, per_page=10):
    """
    Devuelve un page_obj paginado y maneja páginas inválidas
    redirigiendo silenciosamente a la página 1.
    """
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
        logger.warning(
            'Página inválida "%s" para %s, fallback a página 1',
            page_number, request.path
        )
    return page_obj
```

**Por qué:** Evita duplicar los mismos `try/except` en ~10 vistas FBV distintas. Centraliza el logging de páginas inválidas y el fallback seguro a página 1.

---

### Paso 1.2: Crear componente Cotton `<c-paginator>`
**Archivo:** `templates/cotton/paginator.html` (nuevo)
**Qué hacer:**
Crear el componente reutilizable que renderiza la barra de paginación truncada con enlaces HTMX.

```html
{% load url_tags %}
{% if page.paginator.num_pages > 1 %}
{% with current=page.number total=page.paginator.num_pages %}
{% with window_start=current|add:-2 window_end=current|add:2 %}
<div class="flex items-center justify-between px-6 py-4 bg-white/[0.01] border-t border-white/5">
    <div class="flex items-center gap-2">
        {% if page.has_previous %}
        <a href="?{% query_transform page=page.previous_page_number %}"
           hx-get="{{ request.path }}?{% query_transform page=page.previous_page_number %}"
           hx-target="{{ target|default:'#tabla-wrapper' }}"
           hx-swap="innerHTML"
           hx-push-url="{{ push_url|default:'true' }}"
           class="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-jmie-gray text-[10px] font-black uppercase tracking-widest transition-colors">
            Anterior
        </a>
        {% else %}
        <span class="px-3 py-1.5 rounded-lg bg-white/5 text-jmie-gray/30 text-[10px] font-black uppercase tracking-widest cursor-not-allowed">
            Anterior
        </span>
        {% endif %}

        <div class="flex items-center gap-1">
            {# Primera página siempre #}
            {% if current == 1 %}
            <span class="px-3 py-1.5 rounded-lg bg-jmie-orange/20 text-jmie-orange text-[10px] font-black transition-colors">1</span>
            {% else %}
            <a href="?{% query_transform page=1 %}"
               hx-get="{{ request.path }}?{% query_transform page=1 %}"
               hx-target="{{ target|default:'#tabla-wrapper' }}"
               hx-swap="innerHTML"
               hx-push-url="{{ push_url|default:'true' }}"
               class="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-jmie-gray text-[10px] font-black transition-colors">1</a>
            {% endif %}

            {# Elipsis inicial #}
            {% if window_start > 2 %}
            <span class="px-2 py-1.5 text-jmie-gray/40 text-[10px] font-black">...</span>
            {% endif %}

            {# Rango medio #}
            {% for p in page.paginator.page_range %}
                {% if p > 1 and p < total and p >= window_start and p <= window_end %}
                    {% if p == current %}
                    <span class="px-3 py-1.5 rounded-lg bg-jmie-orange/20 text-jmie-orange text-[10px] font-black transition-colors">{{ p }}</span>
                    {% else %}
                    <a href="?{% query_transform page=p %}"
                       hx-get="{{ request.path }}?{% query_transform page=p %}"
                       hx-target="{{ target|default:'#tabla-wrapper' }}"
                       hx-swap="innerHTML"
                       hx-push-url="{{ push_url|default:'true' }}"
                       class="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-jmie-gray text-[10px] font-black transition-colors">{{ p }}</a>
                    {% endif %}
                {% endif %}
            {% endfor %}

            {# Elipsis final #}
            {% if window_end < total|add:-1 %}
            <span class="px-2 py-1.5 text-jmie-gray/40 text-[10px] font-black">...</span>
            {% endif %}

            {# Última página siempre #}
            {% if total > 1 %}
                {% if current == total %}
                <span class="px-3 py-1.5 rounded-lg bg-jmie-orange/20 text-jmie-orange text-[10px] font-black transition-colors">{{ total }}</span>
                {% else %}
                <a href="?{% query_transform page=total %}"
                   hx-get="{{ request.path }}?{% query_transform page=total %}"
                   hx-target="{{ target|default:'#tabla-wrapper' }}"
                   hx-swap="innerHTML"
                   hx-push-url="{{ push_url|default:'true' }}"
                   class="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-jmie-gray text-[10px] font-black transition-colors">{{ total }}</a>
                {% endif %}
            {% endif %}
        </div>

        {% if page.has_next %}
        <a href="?{% query_transform page=page.next_page_number %}"
           hx-get="{{ request.path }}?{% query_transform page=page.next_page_number %}"
           hx-target="{{ target|default:'#tabla-wrapper' }}"
           hx-swap="innerHTML"
           hx-push-url="{{ push_url|default:'true' }}"
           class="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-jmie-gray text-[10px] font-black uppercase tracking-widest transition-colors">
            Siguiente
        </a>
        {% else %}
        <span class="px-3 py-1.5 rounded-lg bg-white/5 text-jmie-gray/30 text-[10px] font-black uppercase tracking-widest cursor-not-allowed">
            Siguiente
        </span>
        {% endif %}
    </div>

    <span class="text-[10px] font-bold text-jmie-gray/40 uppercase tracking-widest">
        Página {{ current }} de {{ total }} &middot; {{ page.paginator.count }} registros
    </span>
</div>
{% endwith %}
{% endwith %}
{% endif %}
```

**Por qué:** Componente Cotton reutilizable garantiza consistencia visual en todas las tablas. Usa `query_transform` para preservar filtros (`q`, `sort`, `order`, etc.). El rango truncado (actual ± 2) evita barras de paginación enormes. El fallback de `target` a `#tabla-wrapper` cubre el 90% de los casos; `core` catálogos pueden sobreescribirlo a `#catalogo-list-container`.

---

## Fase 2: App Dispositivos

### Paso 2.1: Modificar vista `dispositivo_list` para paginar
**Archivo:** `dispositivos/views.py`
**Qué hacer:**
Importar `paginate_queryset` y aplicar paginación de 20 ítems al queryset filtrado/ordenado. Pasar `page_obj` en el contexto en lugar del queryset crudo.

```python
# Añadir al import de core
from core.pagination import paginate_queryset

# Dentro de dispositivo_list, reemplazar:
#     context = {
#         'dispositivos': dispositivos,
# ...
# por:
    page_obj = paginate_queryset(request, dispositivos, per_page=20)
    context = {
        'page_obj': page_obj,
        'dispositivos': page_obj,  # backward-compat para templates que aún usen 'dispositivos'
        'filter': filterset,
        'tipos': TipoDispositivo.objects.all(),
        'estados': EstadoDispositivo.objects.all(),
        'query': query,
        'current_sort': sort,
        'current_order': order,
    }
```

**Por qué:** La vista es el punto de entrada. Paginar aquí reduce la carga de DB y memoria. Mantener `'dispositivos': page_obj` evita romper templates que aún no se actualicen en esta tarea. El parámetro `per_page=20` es apropiado para el volumen de inventario.

---

### Paso 2.2: Refactorizar `dispositivo_list.html` para usar el partial de tabla
**Archivo:** `dispositivos/templates/dispositivos/dispositivo_list.html`
**Qué hacer:**
Reemplazar el bloque `<table>` duplicado inline por un `{% include %}` del partial `dispositivo_list_table.html` dentro de `#tabla-wrapper`.

Cambiar:
```html
<div id="tabla-wrapper">
    <table class="w-full text-left border-collapse">
    <thead>...todo el thead...</thead>
    <tbody id="search-results" class="divide-y divide-white/5">
        {% include "dispositivos/partials/dispositivo_list_results.html" %}
    </tbody>
    </table>
</div>
```

Por:
```html
<div id="tabla-wrapper">
    {% include "dispositivos/partials/dispositivo_list_table.html" %}
</div>
```

**Por qué:** Elimina la duplicación entre la carga inicial y la respuesta HTMX. Asegura que tanto la carga completa como las peticiones AJAX vean exactamente el mismo HTML (tabla + paginador). Esto es crítico para que HTMX haga swap consistente.

---

### Paso 2.3: Actualizar partial `dispositivo_list_table.html`
**Archivo:** `dispositivos/templates/dispositivos/partials/dispositivo_list_table.html`
**Qué hacer:**
Añadir el componente `<c-paginator />` debajo de la tabla.

```html
<table class="w-full text-left border-collapse">
    <thead>
        <tr class="bg-white/[0.02] border-b border-white/5 text-jmie-gray uppercase text-[10px] font-black tracking-widest">
            <c-th-sort sort="id">ID / Serie</c-th-sort>
            <c-th-sort sort="tipo">Tipo</c-th-sort>
            <c-th-sort sort="marca">Marca & Modelo</c-th-sort>
            <c-th-sort sort="responsable">Responsable & CC</c-th-sort>
            <c-th-sort sort="estado">Estado</c-th-sort>
            <c-th-sort sort="acta">Acta</c-th-sort>
            <th class="px-6 py-4 text-right">Acciones</th>
        </tr>
    </thead>
    <tbody id="search-results" class="divide-y divide-white/5">
        {% include "dispositivos/partials/dispositivo_list_results.html" %}
    </tbody>
</table>
<c-paginator page="{{ page_obj }}" />
```

**Por qué:** Este partial es el que devuelve la vista cuando `HX-Request` está presente. Incluir el paginador aquí garantiza que al navegar por páginas vía AJAX, el paginador se actualice junto con las filas.

---

### Paso 2.4: Actualizar partial `dispositivo_list_results.html` para iterar `page_obj`
**Archivo:** `dispositivos/templates/dispositivos/partials/dispositivo_list_results.html`
**Qué hacer:**
Cambiar el loop de `{% for d in dispositivos %}` a `{% for d in page_obj %}`.

```html
{% load ui_tags %}
{% for d in page_obj %}
<tr class="group hover:bg-white/[0.02] border-b border-white/5 transition-colors">
    ...
</tr>
{% empty %}
<tr>
    <td colspan="7">
        <c-empty-state icon="inventory_2" title="Sin Activos" subtitle="No se encontraron dispositivos que coincidan con los filtros seleccionados." action_url="/dispositivos/crear/" action_label="Registrar Equipo" />
    </td>
</tr>
{% endfor %}
```

**Por qué:** `page_obj` es ahora la variable paginada que contiene solo los 20 registros de la página actual. Usar `dispositivos` seguiría funcionando por backward-compat, pero usar `page_obj` es explícito y correcto.

---

### Paso 2.5: Actualizar contador en el footer del panel
**Archivo:** `dispositivos/templates/dispositivos/dispositivo_list.html`
**Qué hacer:**
Cambiar el texto del footer para mostrar el total del paginador en lugar de `dispositivos.count`.

```html
<span class="text-[10px] font-bold text-jmie-gray uppercase tracking-tighter">
    Mostrando {{ page_obj.paginator.count }} activos registrados
</span>
```

**Por qué:** `dispositivos.count` ya no estará disponible (o sería el total del queryset previo a la paginación, lo cual es correcto, pero `page_obj.paginator.count` es más explícito y funciona siempre).

---

## Fase 3: App Colaboradores

### Paso 3.1: Modificar vista `colaborador_list` para paginar
**Archivo:** `colaboradores/views.py`
**Qué hacer:**
Importar `paginate_queryset` y aplicar paginación de 20 ítems.

```python
from core.pagination import paginate_queryset

# Dentro de colaborador_list, reemplazar el bloque context:
    page_obj = paginate_queryset(request, colaboradores, per_page=20)
    context = {
        'page_obj': page_obj,
        'colaboradores': page_obj,
        'query': query,
        'current_sort': sort,
        'current_order': order,
    }
```

**Por qué:** Mismo patrón que dispositivos. 20 ítems por página es adecuado para el directorio de personal.

---

### Paso 3.2: Refactorizar `colaborador_list.html` para usar el partial de tabla
**Archivo:** `templates/colaboradores/colaborador_list.html`
**Qué hacer:**
Reemplazar el `<table>` inline por inclusión del partial `colaborador_list_table.html`.

```html
<div id="tabla-wrapper" class="overflow-x-auto">
    {% include "colaboradores/partials/colaborador_list_table.html" %}
</div>
```

**Por qué:** Elimina duplicación y asegura consistencia entre carga inicial y HTMX.

---

### Paso 3.3: Actualizar partial `colaborador_list_table.html`
**Archivo:** `templates/colaboradores/partials/colaborador_list_table.html`
**Qué hacer:**
Añadir `<c-paginator page="{{ page_obj }}" />` debajo de la tabla.

```html
<table class="w-full text-left border-collapse">
    <thead>
        <tr class="bg-white/[0.02] border-b border-white/5 text-jmie-gray uppercase text-[10px] font-black tracking-widest">
            <c-th-sort sort="nombre">Colaborador</c-th-sort>
            <c-th-sort sort="rut">RUT</c-th-sort>
            <c-th-sort sort="departamento">Cargo / Depto</c-th-sort>
            <c-th-sort sort="centro_costo">Centro de Costo</c-th-sort>
            <c-th-sort sort="estado">Estado</c-th-sort>
            <th class="px-6 py-5 text-right font-black">Acciones</th>
        </tr>
    </thead>
    <tbody id="search-results" class="divide-y divide-white/5">
        {% include "colaboradores/partials/colaborador_list_results.html" %}
    </tbody>
</table>
<c-paginator page="{{ page_obj }}" />
```

**Por qué:** El partial debe devolver tabla + paginador en las respuestas HTMX.

---

### Paso 3.4: Actualizar partial `colaborador_list_results.html` para iterar `page_obj`
**Archivo:** `templates/colaboradores/partials/colaborador_list_results.html`
**Qué hacer:**
Cambiar el loop a `{% for c in page_obj %}` (o el nombre de variable que use el template actual).

**Por qué:** Iterar sobre la página actual, no todo el queryset.

---

## Fase 4: App Core (Catálogos)

Los catálogos usan `base_catalogo.html` como layout compartido. La estrategia es:
1. Paginar en cada vista FBV de catálogo.
2. Pasar `page_obj` al contexto.
3. En cada template hijo, iterar `page_obj` en lugar del nombre propio (`fabricantes`, `modelos`, etc.).
4. Añadir `<c-paginator page="{{ page_obj }}" target="#catalogo-list-container" />` en `base_catalogo.html`.

### Paso 4.1: Modificar vista `fabricante_list`
**Archivo:** `core/views.py`
**Qué hacer:**
```python
from core.pagination import paginate_queryset

@login_required
def fabricante_list(request):
    fabricantes = Fabricante.objects.prefetch_related('modelos').all().order_by('nombre')
    page_obj = paginate_queryset(request, fabricantes, per_page=10)
    return render(request, 'core/fabricante_list.html', {'page_obj': page_obj, 'fabricantes': page_obj})
```

**Por qué:** 10 ítems es suficiente para catálogos que típicamente tienen pocos registros.

---

### Paso 4.2: Modificar vista `modelo_list`
**Archivo:** `core/views.py`
**Qué hacer:**
```python
@login_required
def modelo_list(request):
    fabricante_id = request.GET.get('fabricante_id')
    modelos = Modelo.objects.select_related('fabricante').all().order_by('fabricante__nombre', 'nombre')
    if fabricante_id:
        modelos = modelos.filter(fabricante_id=fabricante_id)
    page_obj = paginate_queryset(request, modelos, per_page=10)
    fabricantes = Fabricante.objects.all().order_by('nombre')
    return render(request, 'core/modelo_list.html', {
        'page_obj': page_obj,
        'modelos': page_obj,
        'fabricantes': fabricantes,
        'selected_fabricante': int(fabricante_id) if fabricante_id else None
    })
```

**Por qué:** Preservar el filtro por fabricante y paginar el resultado.

---

### Paso 4.3: Modificar vista `tipo_list`
**Archivo:** `core/views.py`
**Qué hacer:**
```python
@login_required
def tipo_list(request):
    tipos = TipoDispositivo.objects.all().order_by('nombre')
    page_obj = paginate_queryset(request, tipos, per_page=10)
    return render(request, 'core/tipo_list.html', {'page_obj': page_obj, 'tipos': page_obj})
```

---

### Paso 4.4: Modificar vista `cc_list`
**Archivo:** `core/views.py`
**Qué hacer:**
```python
@login_required
def cc_list(request):
    ccs = CentroCosto.objects.all().order_by('-activa', 'nombre')
    page_obj = paginate_queryset(request, ccs, per_page=10)
    return render(request, 'core/cc_list.html', {'page_obj': page_obj, 'ccs': page_obj})
```

---

### Paso 4.5: Modificar vista `estado_list`
**Archivo:** `core/views.py`
**Qué hacer:**
```python
@login_required
def estado_list(request):
    estados = EstadoDispositivo.objects.all().order_by('nombre')
    page_obj = paginate_queryset(request, estados, per_page=10)
    return render(request, 'core/estado_list.html', {'page_obj': page_obj, 'estados': page_obj})
```

---

### Paso 4.6: Modificar vista `departamento_list`
**Archivo:** `core/views.py`
**Qué hacer:**
```python
@login_required
def departamento_list(request):
    departamentos = Departamento.objects.all().order_by('nombre')
    page_obj = paginate_queryset(request, departamentos, per_page=10)
    return render(request, 'core/departamento_list.html', {'page_obj': page_obj, 'departamentos': page_obj})
```

---

### Paso 4.7: Actualizar `base_catalogo.html` para incluir el paginador
**Archivo:** `core/templates/core/base_catalogo.html`
**Qué hacer:**
Añadir el paginador dentro de `#catalogo-list-container`, después del `</table>` y antes del footer.

```html
        </table>
        <c-paginator page="{{ page_obj }}" target="#catalogo-list-container" />
    </div>
```

**Por qué:** `#catalogo-list-container` es el elemento que se reemplaza en los refrescos HTMX de catálogos (ver el `hx-target` en el hidden refrescador de líneas 37-44 del template base).

---

### Paso 4.8: Actualizar templates hijos de catálogos para iterar `page_obj`
**Archivos:**
- `core/templates/core/fabricante_list.html`
- `core/templates/core/modelo_list.html`
- `core/templates/core/tipo_list.html`
- `core/templates/core/cc_list.html`
- `core/templates/core/estado_list.html`
- `core/templates/core/departamento_list.html`

**Qué hacer:**
En cada template, cambiar el loop `{% for fabricante in fabricantes %}` a `{% for fabricante in page_obj %}`, `{% for modelo in modelos %}` a `{% for modelo in page_obj %}`, etc.

**Por qué:** El paginador mostrará los controles correctos, pero si el template itera el queryset completo, seguiríamos mostrando todos los registros.

---

## Fase 5: App Actas (Agregar paginador visual)

`actas` ya tiene paginación backend (`Paginator` con 10 ítems). Solo falta el componente visual.

### Paso 5.1: Actualizar partial `acta_table.html`
**Archivo:** `actas/templates/actas/partials/acta_table.html`
**Qué hacer:**
Añadir el paginador después de la tabla.

```html
{% load acta_tags %}
<table class="w-full text-left border-collapse">
    <thead>
        <tr class="bg-white/[0.02] border-b border-white/5 text-jmie-gray uppercase text-[10px] font-black tracking-widest">
            <c-th-sort sort="folio">Folio</c-th-sort>
            <c-th-sort sort="colaborador">Colaborador / RUT</c-th-sort>
            <c-th-sort sort="fecha">Fecha Emisión</c-th-sort>
            <c-th-sort sort="tipo">Tipo</c-th-sort>
            <c-th-sort sort="firmada">Estado Legal</c-th-sort>
            <th class="px-6 py-5 text-right font-black">Acciones</th>
        </tr>
    </thead>
    <tbody id="search-results" class="divide-y divide-white/5">
        {% include "actas/partials/acta_table_rows.html" %}
    </tbody>
</table>
<c-paginator page="{{ page_obj }}" />
```

**Por qué:** La vista `acta_list` ya pasa `page_obj` al contexto. Solo hace falta renderizarlo.

---

### Paso 5.2: Actualizar `acta_list.html` para incluir el paginador en carga inicial
**Archivo:** `actas/templates/actas/acta_list.html`
**Qué hacer:**
Reemplazar el bloque de tabla inline dentro de `#tabla-wrapper` por `{% include "actas/partials/acta_table.html" %}`.

```html
<div id="tabla-wrapper" class="overflow-x-auto"
     hx-get="{% url 'actas:acta_list' %}"
     hx-trigger="actaCreated from:body"
     hx-indicator=".htmx-indicator"
     hx-push-url="false">
    {% include "actas/partials/acta_table.html" %}
</div>
```

**Por qué:** Alinea la carga inicial con la respuesta HTMX. Elimina duplicación de markup de tabla.

---

### Paso 5.3: Actualizar `acta_table_rows.html` para iterar `page_obj`
**Archivo:** `actas/templates/actas/partials/acta_table_rows.html`
**Qué hacer:**
Verificar/cambiar el loop a `{% for acta in page_obj %}`.

**Por qué:** Asegurar que solo se rendericen las filas de la página actual.

---

## Fase 6: Pruebas

### Paso 6.1: Tests unitarios para `core/pagination.py`
**Archivo:** `core/tests/test_pagination.py` (nuevo)
**Qué hacer:**
```python
import pytest
from django.http import HttpRequest
from django.core.paginator import Paginator
from core.pagination import paginate_queryset


@pytest.mark.django_db
class TestPaginateQueryset:
    def test_returns_correct_page(self):
        request = HttpRequest()
        request.GET = {'page': '2'}
        qs = list(range(25))  # simula 25 items
        page_obj = paginate_queryset(request, qs, per_page=10)
        assert page_obj.number == 2
        assert len(page_obj) == 10

    def test_invalid_string_page_fallback_to_one(self):
        request = HttpRequest()
        request.GET = {'page': 'abc'}
        request.path = '/test/'
        qs = list(range(25))
        page_obj = paginate_queryset(request, qs, per_page=10)
        assert page_obj.number == 1

    def test_empty_page_fallback_to_one(self):
        request = HttpRequest()
        request.GET = {'page': '999'}
        request.path = '/test/'
        qs = list(range(5))
        page_obj = paginate_queryset(request, qs, per_page=10)
        assert page_obj.number == 1
```

**Por qué:** Valida el fallback seguro ante páginas inválidas, que es un requisito crítico del diseño.

---

### Paso 6.2: Tests de integración para `dispositivo_list`
**Archivo:** `dispositivos/tests/test_views.py`
**Qué hacer:**
Añadir tests dentro de `TestDispositivoViews`:

```python
    def test_dispositivo_list_returns_page_obj(self, client):
        user = self._login_superuser(client)
        for i in range(25):
            DispositivoFactory(identificador_interno=f"JMIE-NOT-{i:05d}")
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url)
        assert response.status_code == 200
        assert 'page_obj' in response.context
        assert response.context['page_obj'].paginator.per_page == 20

    def test_dispositivo_list_invalid_page_fallback(self, client):
        user = self._login_superuser(client)
        DispositivoFactory()
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'page': 'xyz'})
        assert response.status_code == 200
        assert response.context['page_obj'].number == 1

    def test_dispositivo_list_htmx_pagination(self, client):
        user = self._login_superuser(client)
        for i in range(25):
            DispositivoFactory(identificador_interno=f"JMIE-NOT-{i:05d}")
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'page': '2'}, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert 'dispositivos/partials/dispositivo_list_table.html' in [t.name for t in response.templates]
        html = response.content.decode('utf-8')
        assert '<c-paginator' in html or 'Página 2 de' in html
```

**Por qué:** Verifica que la vista pagina correctamente, que `page_obj` está en el contexto, que páginas inválidas no generan 500, y que las respuestas HTMX incluyen el paginador.

---

### Paso 6.3: Tests de integración para `colaborador_list`
**Archivo:** `colaboradores/tests/test_views.py`
**Qué hacer:**
Añadir tests similares validando `page_obj`, fallback de página inválida, y que el partial HTMX incluye el paginador.

---

### Paso 6.4: Tests de integración para catálogos core
**Archivo:** `core/tests/test_views.py`
**Qué hacer:**
Añadir tests para al menos `fabricante_list` y `modelo_list`:

```python
@pytest.mark.django_db
def test_fabricante_list_paginated(client):
    user = ColaboradorFactory(is_staff=True, is_superuser=True)
    user.set_password('password')
    user.save()
    client.login(username=user.username, password='password')
    for i in range(15):
        FabricanteFactory(nombre=f"Fab {i}")
    response = client.get(reverse('core:fabricante_list'))
    assert response.status_code == 200
    assert 'page_obj' in response.context
    assert len(response.context['page_obj']) <= 10
```

**Por qué:** Los catálogos usan `base_catalogo.html` que no tenía paginación antes; es importante validar que el cambio no rompe el renderizado.

---

### Paso 6.5: Tests de integración para `acta_list` (paginador visual)
**Archivo:** `actas/tests/test_views.py` (crear si no existe)
**Qué hacer:**
```python
import pytest
from django.urls import reverse
from core.tests.factories import ColaboradorFactory
from actas.tests.factories import ActaFactory

@pytest.mark.django_db
class TestActaListPagination:
    def test_acta_list_has_page_obj(self, client):
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        for i in range(15):
            ActaFactory()
        response = client.get(reverse('actas:acta_list'))
        assert response.status_code == 200
        assert 'page_obj' in response.context
        assert response.context['page_obj'].paginator.per_page == 10
```

**Por qué:** Aunque `actas` ya tenía paginación backend, debemos validar que ahora el paginador visual se renderiza y que la respuesta HTMX sigue funcionando.

---

## Checklist de Testing Final

Antes de dar por terminada la implementación, ejecutar y verificar:

- [ ] `pytest core/tests/test_pagination.py` pasa (helper de paginación).
- [ ] `pytest dispositivos/tests/test_views.py -k "pagina or page_obj or htmx_pagination"` pasa.
- [ ] `pytest colaboradores/tests/test_views.py -k "pagina or page_obj"` pasa.
- [ ] `pytest core/tests/test_views.py -k "pagina or page_obj"` pasa.
- [ ] `pytest actas/tests/test_views.py -k "page_obj"` pasa (crear archivo si no existe).
- [ ] Navegar manualmente a `/dispositivos/listado/` y verificar:
  - [ ] Se muestran máximo 20 registros.
  - [ ] El paginador muestra "Página 1 de N".
  - [ ] Click en página 2 carga vía AJAX (no recarga completa).
  - [ ] La URL se actualiza a `?page=2`.
  - [ ] Aplicar un filtro de búsqueda y cambiar de página preserva el término `q=`.
- [ ] Navegar a `/colaboradores/listado/` y repetir las mismas verificaciones.
- [ ] Navegar a `/catalogos/fabricantes/` y verificar paginación de 10 ítems.
- [ ] Navegar a `/actas/listado/` y verificar que el paginador visual aparece y funciona.
- [ ] Probar página inválida: `/dispositivos/listado/?page=abc` redirige silenciosamente a página 1 (sin 500).
- [ ] Probar página mayor al total: `/dispositivos/listado/?page=999` redirige a página 1.
- [ ] Verificar que la exportación Excel/CSV (si existe en el mismo endpoint) **no** se ve afectada por el parámetro `page`. Si comparte vista, asegurarse de que el export ignora `page`.

---

## Notas de Implementación

1. **Exportación vs Paginación:** Si alguna vista de listado comparte lógica con exportación a Excel/CSV, asegurarse de que la lógica de exportación use el queryset **completo** (previo a la paginación) y no `page_obj`. El helper `paginate_queryset` se llama después de que el queryset está filtrado/ordenado; la exportación debe tomar ese queryset antes de paginar.

2. **Backward Compatibility:** Las vistas pasan tanto `page_obj` como el nombre legacy (`dispositivos`, `colaboradores`, etc.) para no romper templates que no se actualicen inmediatamente. Los templates actualizados deben preferir `page_obj`.

3. **HTMX y `hx-push-url`:** El componente `<c-paginator>` usa `hx-push-url="true"` por defecto, lo que actualiza la URL del navegador al cambiar de página. Esto permite compartir URLs con página específica y funciona correctamente con el botón "Atrás" del navegador.

4. **Core Catalogs y `#catalogo-list-container`:** El refrescador HTMX de `base_catalogo.html` usa `hx-target="#catalogo-list-container"` y `hx-swap="outerHTML"`. El paginador usa `target="#catalogo-list-container"` para que los clicks reemplacen todo el contenedor, manteniendo consistencia con el refresco por eventos.

5. **No modificar naming de URLs:** Todas las vistas listado mantienen sus nombres de URL existentes (`dispositivo_list`, `colaborador_list`, `fabricante_list`, etc.). El paginador usa `request.path` para generar las URLs, por lo que no depende de `reverse()` con nombres.
