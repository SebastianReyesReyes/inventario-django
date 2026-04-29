# Suministros UI Module Implementation Plan

**Goal:** Build the complete user interface for the `suministros` app — list, CRUD, inline stock movement modals, soft delete, low-stock alerts, and dashboard widget — while reusing existing backend models, forms, and services.

**Architecture:** HTMX-driven CRUD with inline modals, following the existing `dispositivos` FBV patterns. All list mutations return HTML partials. Stock movements use `core/htmx.py` helpers to emit `HX-Trigger` events that refresh the list and show toasts via Alpine.js.

**Design:** [thoughts/shared/designs/2026-04-27-suministros-ui-design.md](thoughts/shared/designs/2026-04-27-suministros-ui-design.md)

**Key Decisions:**
- **FBVs over CBVs:** The existing `dispositivos` app uses function-based views with `@login_required` / `@permission_required`. Following this convention for consistency.
- **Soft delete field:** `Suministro` currently lacks `esta_activo`. Adding it with a custom `SuministroQuerySet` (`activos()`, `bajo_stock()`).
- **Pagination:** Django `Paginator` at 20 items per page (design requirement; `dispositivos` currently unpaginated but the 479KB list problem is noted).
- **Movement form:** Reuses `MovimientoStockForm` but the view hides `suministro` and pre-fills it to keep the modal focused.

---

## Dependency Graph

```
Batch 1 (parallel): 1.1, 1.2, 1.3, 1.4 [foundation - no deps]
Batch 2 (parallel): 2.1 [backend views - depends on 1.1, 1.2]
Batch 3 (parallel): 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9 [templates - depends on 2.1 for URL/context names]
Batch 4 (parallel): 4.1, 4.2 [unit/integration tests - depends on 1.1, 2.1, 3.x]
Batch 5 (parallel): 5.1, 5.2 [E2E tests - depends on everything above]
```

---

## Batch 1: Foundation (parallel — 4 implementers)

All tasks in this batch have NO dependencies and run simultaneously.

### Task 1.1: Suministro Model Soft-Delete + Custom Manager
**File:** `suministros/models.py`  
**Test:** `suministros/tests/test_models.py` (create if absent)  
**Depends:** none

**Step 1 — Add QuerySet + manager and `esta_activo` field to `suministros/models.py`:**

```python
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum, F
from core.models import Modelo, CentroCosto
from colaboradores.models import Colaborador


class CategoriaSuministro(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, help_text="Descripción de la categoría de suministros")
    tipos_dispositivo_compatibles = models.ManyToManyField('core.TipoDispositivo', blank=True, help_text="Tipos de dispositivos que usan esta categoría de suministros")

    class Meta:
        verbose_name = "Categoría de Suministro"
        verbose_name_plural = "Categorías de Suministros"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class SuministroQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(esta_activo=True)

    def bajo_stock(self):
        return self.filter(stock_actual__lte=F('stock_minimo'))


class Suministro(models.Model):
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaSuministro, on_delete=models.PROTECT, related_name='suministros')
    codigo_interno = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="SKU o código de barras")

    marca = models.CharField(max_length=100, blank=True, help_text="Marca del insumo (Ej: Dataline para alternativos, o Brother si es original)")
    es_alternativo = models.BooleanField(default=False, help_text="Marcar si es un insumo alternativo/genérico")

    unidad_medida = models.CharField(max_length=50, default="Unidades", help_text="Ej: Unidades, Cajas, Litros")
    stock_minimo = models.PositiveIntegerField(default=2, help_text="Nivel de alerta para reposición")

    modelos_compatibles = models.ManyToManyField(Modelo, blank=True, related_name='suministros_compatibles', help_text="Modelos de impresoras o dispositivos compatibles")

    # Campo de solo lectura, actualizado vía señales o services
    stock_actual = models.IntegerField(default=0, editable=False, help_text="Stock calculado en base a movimientos")

    esta_activo = models.BooleanField(default=True, help_text="Indica si el suministro está activo en el catálogo")

    class Meta:
        verbose_name = "Suministro"
        verbose_name_plural = "Suministros"
        ordering = ['categoria__nombre', 'nombre']

    objects = SuministroQuerySet.as_manager()

    def __str__(self):
        marca_str = ""
        if self.marca and self.marca.lower() not in self.nombre.lower():
            marca_str = f" ({self.marca})"

        tipo_str = " [Alternativo]" if self.es_alternativo else ""
        return f"{self.nombre}{marca_str}{tipo_str}"

    def recalcular_stock(self):
        entradas = self.movimientos.filter(
            tipo_movimiento__in=[MovimientoStock.TipoMovimiento.ENTRADA, MovimientoStock.TipoMovimiento.AJUSTE_POSITIVO]
        ).aggregate(total=Sum('cantidad'))['total'] or 0

        salidas = self.movimientos.filter(
            tipo_movimiento__in=[MovimientoStock.TipoMovimiento.SALIDA, MovimientoStock.TipoMovimiento.AJUSTE_NEGATIVO]
        ).aggregate(total=Sum('cantidad'))['total'] or 0

        nuevo_stock = entradas - salidas
        if self.stock_actual != nuevo_stock:
            self.stock_actual = nuevo_stock
            self.save(update_fields=['stock_actual'])

    @property
    def stock_critico(self):
        return self.stock_actual <= self.stock_minimo


class MovimientoStock(models.Model):
    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada (Compra)'
        SALIDA = 'SALIDA', 'Salida (Entrega/Asignación)'
        AJUSTE_POSITIVO = 'AJUSTE_POS', 'Ajuste Positivo'
        AJUSTE_NEGATIVO = 'AJUSTE_NEG', 'Ajuste Negativo (Merma/Pérdida)'

    suministro = models.ForeignKey(Suministro, on_delete=models.PROTECT, related_name='movimientos')
    fecha = models.DateTimeField(default=timezone.now)
    tipo_movimiento = models.CharField(max_length=20, choices=TipoMovimiento.choices)
    cantidad = models.PositiveIntegerField(help_text="Cantidad del movimiento (siempre positiva)")

    # Datos de la Factura (Solo para ENTRADAS)
    costo_unitario = models.PositiveIntegerField(null=True, blank=True, help_text="Costo unitario en la factura (solo entradas)")
    numero_factura = models.CharField(max_length=100, null=True, blank=True)

    # Datos de Salida (Solo para SALIDAS)
    colaborador_destino = models.ForeignKey(Colaborador, on_delete=models.SET_NULL, null=True, blank=True, related_name='suministros_recibidos')
    centro_costo = models.ForeignKey(CentroCosto, on_delete=models.SET_NULL, null=True, blank=True, related_name='suministros_cargados')

    registrado_por = models.ForeignKey(Colaborador, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_stock_registrados')
    notas = models.TextField(blank=True, help_text="Razón de la merma, detalle de la entrega, etc.")

    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.tipo_movimiento} de {self.cantidad} {self.suministro.unidad_medida} - {self.suministro.nombre}"

    def clean(self):
        if self.tipo_movimiento == self.TipoMovimiento.SALIDA and self.cantidad > self.suministro.stock_actual:
            if self.pk is None:
                raise ValidationError({"cantidad": f"No hay suficiente stock. Stock actual: {self.suministro.stock_actual}."})
```

**Step 2 — Create migration:**
```bash
python manage.py makemigrations suministros
```
Expected file: `suministros/migrations/0003_suministro_esta_activo.py`

**Step 3 — Test (`suministros/tests/test_models.py`):**

```python
import pytest
from suministros.models import CategoriaSuministro, Suministro, MovimientoStock

@pytest.mark.django_db
class TestSuministroModel:
    @pytest.fixture
    def categoria(self):
        return CategoriaSuministro.objects.create(nombre="Papel", descripcion="Papel bond")

    @pytest.fixture
    def suministro(self, categoria):
        return Suministro.objects.create(nombre="Papel A4", categoria=categoria, stock_minimo=5)

    def test_esta_activo_default_true(self, suministro):
        assert suministro.esta_activo is True

    def test_queryset_activos_excludes_inactivos(self, categoria):
        s1 = Suministro.objects.create(nombre="Activo", categoria=categoria)
        s2 = Suministro.objects.create(nombre="Inactivo", categoria=categoria, esta_activo=False)
        activos = Suministro.objects.activos()
        assert s1 in activos
        assert s2 not in activos

    def test_bajo_stock_filter(self, categoria):
        normal = Suministro.objects.create(nombre="Normal", categoria=categoria, stock_actual=10, stock_minimo=5)
        critico = Suministro.objects.create(nombre="Critico", categoria=categoria, stock_actual=3, stock_minimo=5)
        bajo = Suministro.objects.bajo_stock()
        assert normal not in bajo
        assert critico in bajo

    def test_stock_critico_property(self, categoria):
        s = Suministro.objects.create(nombre="Test", categoria=categoria, stock_actual=2, stock_minimo=5)
        assert s.stock_critico is True
        s.stock_actual = 10
        assert s.stock_critico is False
```

**Verify:** `pytest suministros/tests/test_models.py -v`
**Commit:** `feat(suministros): add soft-delete flag and custom queryset with bajo_stock filter`

---

### Task 1.2: URL Routes
**File:** `suministros/urls.py`  
**Test:** none (covered by view tests in Batch 4)  
**Depends:** none

Replace the entire contents of `suministros/urls.py`:

```python
from django.urls import path
from . import views

app_name = 'suministros'

urlpatterns = [
    path('', views.suministro_list, name='suministro_list'),
    path('crear/', views.suministro_create, name='suministro_create'),
    path('editar/<int:pk>/', views.suministro_update, name='suministro_update'),
    path('detalle/<int:pk>/', views.suministro_detail, name='suministro_detail'),
    path('eliminar/<int:pk>/', views.suministro_delete, name='suministro_delete'),
    path('movimiento/nuevo/', views.movimiento_create, name='movimiento_create'),
    path('ajax/modelos-compatibles/', views.ajax_get_modelos_compatibles, name='ajax_get_modelos_compatibles'),
]
```

**Verify:** `python manage.py check --deploy` (ensure no URL collisions)  
**Commit:** `feat(suministros): define CRUD and movement URL routes`

---

### Task 1.3: Navigation Link in Base Template
**File:** `templates/base.html`  
**Test:** none  
**Depends:** none

Locate the "Inventario" section in `templates/base.html` (around line 231–243) and add the Suministros link after "Actas":

```html
            <a href="{% url 'suministros:suministro_list' %}"
                class="flex items-center px-3 py-2 text-sm font-bold uppercase tracking-wide rounded-lg transition-all group {% active_url 'suministros:suministro_list' %}">
                <span
                    class="material-symbols-outlined mr-3 {% active_icon 'suministros:suministro_list' %}">inventory</span>
                Suministros
            </a>
```

Place it immediately after the "Actas" link and before the `{% if perms.dispositivos.add_dispositivo %}` block.

**Verify:** Load any page and confirm the "Suministros" nav item renders.  
**Commit:** `feat(ui): add suministros link to main navigation`

---

### Task 1.4: Test Factories
**File:** `suministros/tests/factories.py`  
**Test:** none (used by other tests)  
**Depends:** none

Create `suministros/tests/factories.py`:

```python
import factory
from suministros.models import CategoriaSuministro, Suministro, MovimientoStock
from core.tests.factories import ColaboradorFactory, ModeloFactory


class CategoriaSuministroFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CategoriaSuministro
        django_get_or_create = ('nombre',)

    nombre = factory.Sequence(lambda n: f"Categoría {n}")
    descripcion = factory.Sequence(lambda n: f"Descripción {n}")


class SuministroFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Suministro

    nombre = factory.Sequence(lambda n: f"Suministro {n}")
    categoria = factory.SubFactory(CategoriaSuministroFactory)
    codigo_interno = factory.Sequence(lambda n: f"SKU-{n:04d}")
    marca = "Generico"
    es_alternativo = False
    unidad_medida = "Unidades"
    stock_minimo = 2
    stock_actual = 0
    esta_activo = True

    @factory.post_generation
    def modelos_compatibles(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for modelo in extracted:
                self.modelos_compatibles.add(modelo)


class MovimientoStockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MovimientoStock

    suministro = factory.SubFactory(SuministroFactory)
    tipo_movimiento = MovimientoStock.TipoMovimiento.ENTRADA
    cantidad = 10
    costo_unitario = 5000
    numero_factura = "FACT-001"
    registrado_por = factory.SubFactory(ColaboradorFactory)
    notas = "Movimiento de prueba"
```

**Verify:** `pytest suministros/tests/test_services.py -v` (existing tests should still pass; factories are syntactically valid if importable)  
**Commit:** `test(suministros): add factories for categoria, suministro and movimiento`

---

## Batch 2: Backend Views (1 implementer — depends on Batch 1)

### Task 2.1: All Suministros Views
**File:** `suministros/views.py`  
**Test:** `suministros/tests/test_views.py` ( Batch 4 )  
**Depends:** 1.1, 1.2

Replace the entire contents of `suministros/views.py`:

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError

from core.htmx import htmx_trigger_response, htmx_render_or_redirect
from core.models import Modelo
from .models import Suministro, MovimientoStock, CategoriaSuministro
from .forms import SuministroForm, MovimientoStockForm
from .services import registrar_movimiento_stock


@login_required
def suministro_list(request):
    """Listado de suministros con búsqueda, filtro por categoría y paginación."""
    query = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')

    suministros = Suministro.objects.activos().select_related('categoria')

    if categoria_id:
        suministros = suministros.filter(categoria_id=categoria_id)

    if query:
        suministros = suministros.filter(
            Q(nombre__icontains=query) |
            Q(codigo_interno__icontains=query) |
            Q(marca__icontains=query)
        )

    # Paginación: 20 items por página
    paginator = Paginator(suministros, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'suministros': page_obj.object_list,
        'categorias': CategoriaSuministro.objects.all(),
        'query': query,
        'categoria_id': categoria_id,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'suministros/partials/suministro_list_table.html', context)

    return render(request, 'suministros/suministro_list.html', context)


@login_required
@permission_required('suministros.add_suministro', raise_exception=True)
def suministro_create(request):
    """Crear un nuevo suministro (página completa)."""
    if request.method == 'POST':
        form = SuministroForm(request.POST)
        if form.is_valid():
            suministro = form.save()
            messages.success(request, f"Suministro '{suministro.nombre}' creado correctamente.")
            return htmx_render_or_redirect(
                request,
                'suministros/suministro_list.html',
                {'page_obj': None, 'suministros': [], 'categorias': [], 'query': '', 'categoria_id': ''},
                reverse('suministros:suministro_list'),
                trigger={'showToast': {'message': f'Suministro "{suministro.nombre}" creado', 'type': 'success'}}
            )
    else:
        form = SuministroForm()

    return render(request, 'suministros/suministro_form.html', {
        'form': form,
        'titulo': 'Nuevo Suministro',
        'action': 'Crear',
    })


@login_required
@permission_required('suministros.change_suministro', raise_exception=True)
def suministro_update(request, pk):
    """Editar un suministro existente."""
    suministro = get_object_or_404(Suministro, pk=pk)
    if request.method == 'POST':
        form = SuministroForm(request.POST, instance=suministro)
        if form.is_valid():
            suministro = form.save()
            messages.success(request, f"Suministro '{suministro.nombre}' actualizado correctamente.")
            return redirect('suministros:suministro_list')
    else:
        form = SuministroForm(instance=suministro)

    return render(request, 'suministros/suministro_form.html', {
        'form': form,
        'suministro': suministro,
        'titulo': 'Editar Suministro',
        'action': 'Guardar Cambios',
    })


@login_required
def suministro_detail(request, pk):
    """Detalle de suministro con historial de movimientos paginado."""
    suministro = get_object_or_404(
        Suministro.objects.select_related('categoria').prefetch_related('modelos_compatibles'),
        pk=pk
    )

    movimientos = suministro.movimientos.select_related('registrado_por', 'colaborador_destino', 'centro_costo')
    paginator = Paginator(movimientos, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    if request.headers.get('HX-Request') and request.GET.get('_partial') == 'movimientos':
        return render(request, 'suministros/partials/movimiento_history.html', {
            'suministro': suministro,
            'page_obj': page_obj,
        })

    return render(request, 'suministros/suministro_detail.html', {
        'suministro': suministro,
        'page_obj': page_obj,
    })


@login_required
@permission_required('suministros.delete_suministro', raise_exception=True)
def suministro_delete(request, pk):
    """Soft delete de suministro. Si tiene stock > 0, advierte pero permite desactivar."""
    suministro = get_object_or_404(Suministro, pk=pk)

    if request.method == 'POST':
        if suministro.stock_actual > 0:
            messages.warning(
                request,
                f"El suministro '{suministro.nombre}' tenía stock {suministro.stock_actual}. Se ha desactivado pero el historial de movimientos se conserva."
            )
        else:
            messages.success(request, f"Suministro '{suministro.nombre}' desactivado correctamente.")

        suministro.esta_activo = False
        suministro.save(update_fields=['esta_activo'])
        return htmx_trigger_response(
            trigger={'refreshSuministroList': '', 'showToast': {'message': 'Suministro desactivado', 'type': 'info'}},
            status=204
        )

    # GET: modal de confirmación
    return render(request, 'suministros/partials/suministro_confirm_delete.html', {
        'suministro': suministro,
    })


@login_required
@permission_required('suministros.add_movimientostock', raise_exception=True)
def movimiento_create(request):
    """HTMX-only: carga modal (GET) o registra movimiento (POST)."""
    suministro_id = request.GET.get('suministro') or request.POST.get('suministro')
    suministro = get_object_or_404(Suministro, pk=suministro_id) if suministro_id else None

    if request.method == 'POST':
        form = MovimientoStockForm(request.POST)
        if suministro:
            form.fields['suministro'].widget = forms.HiddenInput()
            form.fields['suministro'].initial = suministro.pk

        if form.is_valid():
            cd = form.cleaned_data
            try:
                registrar_movimiento_stock(
                    suministro_id=cd['suministro'].id,
                    tipo_movimiento=cd['tipo_movimiento'],
                    cantidad=cd['cantidad'],
                    registrado_por_id=request.user.id,
                    colaborador_destino_id=cd.get('colaborador_destino').id if cd.get('colaborador_destino') else None,
                    centro_costo_id=cd.get('centro_costo').id if cd.get('centro_costo') else None,
                    costo_unitario=cd.get('costo_unitario'),
                    numero_factura=cd.get('numero_factura'),
                    notas=cd.get('notas', ''),
                )
                return htmx_trigger_response(
                    trigger={
                        'refreshSuministroList': '',
                        'showToast': {'message': 'Movimiento registrado', 'type': 'success'}
                    },
                    status=204
                )
            except ValidationError as e:
                # Añadimos el error al formulario para que se muestre en el modal
                if 'cantidad' in e.message_dict:
                    form.add_error('cantidad', e.message_dict['cantidad'][0])
                else:
                    form.add_error(None, str(e))

        # Si llegamos aquí, el form tiene errores (validación o excepción)
        if suministro:
            form.fields['suministro'].widget = forms.HiddenInput()
            form.fields['suministro'].initial = suministro.pk
        return render(request, 'suministros/partials/movimiento_modal.html', {
            'form': form,
            'suministro': suministro,
        })

    # GET: renderizar modal
    initial = {}
    if suministro:
        initial['suministro'] = suministro.pk
    form = MovimientoStockForm(initial=initial)
    if suministro:
        form.fields['suministro'].widget = forms.HiddenInput()
        form.fields['suministro'].initial = suministro.pk

    return render(request, 'suministros/partials/movimiento_modal.html', {
        'form': form,
        'suministro': suministro,
    })


@login_required
def ajax_get_modelos_compatibles(request):
    """Retorna opciones de modelos filtrados por categoría (usado en SuministroForm)."""
    categoria_id = request.GET.get('categoria')
    modelos = Modelo.objects.all().order_by('nombre')

    if categoria_id:
        try:
            categoria = CategoriaSuministro.objects.get(pk=categoria_id)
            tipos = categoria.tipos_dispositivo_compatibles.all()
            if tipos.exists():
                modelos = modelos.filter(tipo_dispositivo__in=tipos)
        except (ValueError, TypeError, CategoriaSuministro.DoesNotExist):
            pass

    return render(request, 'suministros/partials/modelo_options.html', {'modelos': modelos})
```

**Note:** Add `from django import forms` import at the top (it is needed for `forms.HiddenInput()` inside `movimiento_create`).

**Verify:** `python manage.py check`  
**Commit:** `feat(suministros): implement list, CRUD, movement modal and ajax views`

---

## Batch 3: Templates (parallel — 9 implementers, depends on Batch 2)

### Task 3.1: Supply List Page
**File:** `suministros/templates/suministros/suministro_list.html`  
**Test:** none  
**Depends:** 2.1

```django
{% extends "base.html" %}

{% block title %}Suministros | JMIE{% endblock %}
{% block section_name %}Suministros{% endblock %}

{% block content %}
<div class="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700"
     x-data="{ toastMessage: '', toastType: '', showToast: false }"
     @showtoast.window="
        toastMessage = $event.detail.message;
        toastType = $event.detail.type;
        showToast = true;
        setTimeout(() => showToast = false, 4000)
     ">

    <!-- Toast -->
    <div x-show="showToast" x-transition
         class="fixed top-6 right-6 z-[60] px-6 py-4 rounded-xl border shadow-2xl flex items-center gap-3"
         :class="toastType === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : (toastType === 'error' ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-blue-500/10 border-blue-500/20 text-blue-400')">
        <span class="material-symbols-outlined" x-text="toastType === 'success' ? 'check_circle' : (toastType === 'error' ? 'error' : 'info')"></span>
        <span class="text-sm font-bold" x-text="toastMessage"></span>
    </div>

    <c-page-header title="Gestión de Suministros" subtitle="Inventario de insumos, repuestos y consumibles.">
        {% if perms.suministros.add_suministro %}
        <a href="{% url 'suministros:suministro_create' %}" class="px-4 py-2.5 bg-jmie-orange text-white text-xs font-black rounded-xl hover:brightness-110 shadow-[0_4px_20px_rgba(237,139,0,0.2)] transition-all flex items-center">
            <span class="material-symbols-outlined text-sm mr-2 leading-none">add</span>
            Nuevo Suministro
        </a>
        {% endif %}
    </c-page-header>

    <!-- Filtros -->
    <div class="bg-surface-container-low p-6 rounded-xl border border-white/5 space-y-6">
        <form hx-get="{% url 'suministros:suministro_list' %}"
              hx-target="#tabla-wrapper"
              hx-trigger="change delay:200ms, keyup changed delay:500ms from:input[name='q']"
              hx-push-url="true"
              class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <c-search-input label="Búsqueda" wrapper_class="md:col-span-2" value="{{ query }}" placeholder="Buscar por nombre, SKU o marca..." />
                <div class="space-y-2">
                    <c-form-label>Categoría</c-form-label>
                    <select name="categoria" class="w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background appearance-none">
                        <option value="">Todas las categorías</option>
                        {% for cat in categorias %}
                        <option value="{{ cat.pk }}" {% if categoria_id == cat.pk|stringformat:"s" %}selected{% endif %}>{{ cat.nombre }}</option>
                        {% endfor %}
                    </select>
                </div>
            </div>
        </form>
    </div>

    <c-glass-panel loader_label="Cargando...">
        <div class="overflow-x-auto">
            <div id="tabla-wrapper"
                 hx-get="{% url 'suministros:suministro_list' %}"
                 hx-trigger="refreshSuministroList from:body"
                 hx-target="#tabla-wrapper"
                 hx-swap="innerHTML">
                {% include "suministros/partials/suministro_list_table.html" %}
            </div>
        </div>
    </c-glass-panel>
</div>

<!-- Modal container global -->
<div id="modal-container" class="relative z-50"></div>
{% endblock %}
```

**Verify:** Load `/suministros/` (after views exist) and confirm the page renders without `TemplateDoesNotExist`.  
**Commit:** `feat(suministros): add supply list full-page template`

---

### Task 3.2: Supply Table Partial (HTMX)
**File:** `suministros/templates/suministros/partials/suministro_list_table.html`  
**Test:** none  
**Depends:** 2.1, 3.4 (stock_badge)

```django
<table class="w-full text-left border-collapse">
    <thead>
        <tr class="bg-white/[0.02] border-b border-white/5 text-jmie-gray uppercase text-[10px] font-black tracking-widest">
            <th class="px-6 py-4">Nombre / SKU</th>
            <th class="px-6 py-4">Categoría</th>
            <th class="px-6 py-4">Stock</th>
            <th class="px-6 py-4">Umbral</th>
            <th class="px-6 py-4 text-right">Acciones</th>
        </tr>
    </thead>
    <tbody class="divide-y divide-white/5">
        {% include "suministros/partials/suministro_list_results.html" %}
    </tbody>
</table>

{% if page_obj.has_other_pages %}
<div class="px-6 py-4 bg-white/[0.01] border-t border-white/5 flex items-center justify-between">
    <span class="text-[10px] font-bold text-jmie-gray uppercase tracking-tighter">
        Página {{ page_obj.number }} de {{ page_obj.paginator.num_pages }}
    </span>
    <div class="flex gap-2">
        {% if page_obj.has_previous %}
        <a href="?page={{ page_obj.previous_page_number }}{% if query %}&q={{ query }}{% endif %}{% if categoria_id %}&categoria={{ categoria_id }}{% endif %}"
           class="px-3 py-1.5 rounded-lg bg-white/5 text-[10px] font-black uppercase tracking-widest text-jmie-gray hover:bg-white/10 transition-all">Anterior</a>
        {% endif %}
        {% if page_obj.has_next %}
        <a href="?page={{ page_obj.next_page_number }}{% if query %}&q={{ query }}{% endif %}{% if categoria_id %}&categoria={{ categoria_id }}{% endif %}"
           class="px-3 py-1.5 rounded-lg bg-white/5 text-[10px] font-black uppercase tracking-widest text-jmie-gray hover:bg-white/10 transition-all">Siguiente</a>
        {% endif %}
    </div>
</div>
{% endif %}
```

**Verify:** HTMX request to `/suministros/` returns only table markup (no `<html>`).  
**Commit:** `feat(suministros): add HTMX-swappable supply table partial`

---

### Task 3.3: Supply Row Partial
**File:** `suministros/templates/suministros/partials/suministro_list_results.html`  
**Test:** none  
**Depends:** 2.1, 3.4

```django
{% for s in suministros %}
<tr class="group hover:bg-white/[0.02] border-b border-white/5 transition-colors">
    <td class="px-6 py-4">
        <div class="flex flex-col">
            <span class="text-xs font-black tracking-tighter text-on-background">{{ s.nombre }}</span>
            <span class="text-[10px] text-jmie-gray font-bold">{{ s.codigo_interno|default:"Sin SKU" }}</span>
        </div>
    </td>
    <td class="px-6 py-4 text-xs font-bold text-jmie-gray">{{ s.categoria.nombre }}</td>
    <td class="px-6 py-4">
        {% include "suministros/partials/stock_badge.html" with suministro=s only %}
    </td>
    <td class="px-6 py-4 text-xs font-bold text-jmie-gray">{{ s.stock_minimo }}</td>
    <td class="px-6 py-4 text-right">
        <div class="flex items-center justify-end gap-2">
            {% if perms.suministros.add_movimientostock %}
            <button hx-get="{% url 'suministros:movimiento_create' %}?suministro={{ s.pk }}"
                    hx-target="#modal-container"
                    class="px-3 py-1.5 rounded-lg bg-jmie-blue/10 text-jmie-blue text-[10px] font-black uppercase tracking-widest hover:bg-jmie-blue/20 transition-all">
                <span class="material-symbols-outlined text-[14px] leading-none align-middle mr-1">sync_alt</span>
                Movimiento
            </button>
            {% endif %}
            {% load action_tags %}
            {% render_actions s 'inventory' %}
        </div>
    </td>
</tr>
{% empty %}
<tr>
    <td colspan="5">
        <c-empty-state icon="inventory" title="Sin Suministros" subtitle="No se encontraron suministros que coincidan con los filtros."
            action_url="{% url 'suministros:suministro_create' %}" action_label="Registrar Suministro" />
    </td>
</tr>
{% endfor %}
```

**Verify:** Rows render with correct stock badge colors.  
**Commit:** `feat(suministros): add supply row partial with movement button`

---

### Task 3.4: Stock Badge Component
**File:** `suministros/templates/suministros/partials/stock_badge.html`  
**Test:** none  
**Depends:** none

```django
{% if suministro.stock_actual == 0 %}
<span class="px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-wider bg-red-500/10 text-red-400 border border-red-500/20">
    Sin Stock (0)
</span>
{% elif suministro.stock_actual <= suministro.stock_minimo %}
<span class="px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20">
    Bajo Stock ({{ suministro.stock_actual }})
</span>
{% else %}
<span class="px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
    OK ({{ suministro.stock_actual }})
</span>
{% endif %}
```

**Verify:** Badge renders green for stock>minimo, yellow for stock<=minimo>0, red for 0.  
**Commit:** `feat(suministros): add color-coded stock badge partial`

---

### Task 3.5: Supply Form (Create/Update)
**File:** `suministros/templates/suministros/suministro_form.html`  
**Test:** none  
**Depends:** 2.1

```django
{% extends "base.html" %}

{% block title %}{{ titulo }} | JMIE{% endblock %}
{% block section_name %}Suministros{% endblock %}

{% block content %}
<div class="max-w-3xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
    <c-page-header title="{{ titulo }}" subtitle="Complete los datos del suministro.">
        <a href="{% url 'suministros:suministro_list' %}" class="px-4 py-2.5 rounded-xl border border-white/10 text-on-background hover:bg-white/5 transition-all text-xs font-bold">
            Volver al Listado
        </a>
    </c-page-header>

    <c-glass-panel>
        <form method="post" class="space-y-6">
            {% csrf_token %}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="md:col-span-2">
                    <c-form-label>Nombre</c-form-label>
                    {{ form.nombre }}
                    {% if form.nombre.errors %}<p class="mt-1 text-xs text-red-400">{{ form.nombre.errors.0 }}</p>{% endif %}
                </div>
                <div>
                    <c-form-label>Categoría</c-form-label>
                    {{ form.categoria }}
                    {% if form.categoria.errors %}<p class="mt-1 text-xs text-red-400">{{ form.categoria.errors.0 }}</p>{% endif %}
                </div>
                <div>
                    <c-form-label>Código Interno / SKU</c-form-label>
                    {{ form.codigo_interno }}
                </div>
                <div>
                    <c-form-label>Marca</c-form-label>
                    {{ form.marca }}
                </div>
                <div>
                    <c-form-label>Unidad de Medida</c-form-label>
                    {{ form.unidad_medida }}
                </div>
                <div>
                    <c-form-label>Stock Mínimo</c-form-label>
                    {{ form.stock_minimo }}
                </div>
                <div class="flex items-center gap-3 p-4 bg-white/5 border border-white/5 rounded-xl">
                    {{ form.es_alternativo }}
                    <label for="{{ form.es_alternativo.id_for_label }}" class="text-xs font-bold text-on-surface cursor-pointer">
                        Es insumo alternativo / genérico
                    </label>
                </div>
                <div class="md:col-span-2">
                    <c-form-label>Modelos Compatibles</c-form-label>
                    {{ form.modelos_compatibles }}
                </div>
            </div>

            <div class="flex justify-end gap-3 pt-6 border-t border-white/5">
                <a href="{% url 'suministros:suministro_list' %}" class="px-5 py-2.5 rounded-xl border border-white/10 text-on-background hover:bg-white/5 transition-all text-xs font-bold">
                    Cancelar
                </a>
                <button type="submit" class="px-6 py-2.5 rounded-xl bg-jmie-orange text-white font-black uppercase tracking-widest text-[10px] hover:brightness-110 shadow-[0_4px_15px_rgba(237,139,0,0.3)] transition-all">
                    {{ action }}
                </button>
            </div>
        </form>
    </c-glass-panel>
</div>
{% endblock %}
```

**Verify:** Create and update pages render correctly with existing `SuministroForm`.  
**Commit:** `feat(suministros): add create/edit form template`

---

### Task 3.6: Supply Detail + Movement History
**File:** `suministros/templates/suministros/suministro_detail.html`  
**Test:** none  
**Depends:** 2.1

```django
{% extends "base.html" %}

{% block title %}{{ suministro.nombre }} | JMIE{% endblock %}
{% block section_name %}Suministros{% endblock %}

{% block content %}
<div class="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
    <c-page-header title="{{ suministro.nombre }}" subtitle="{{ suministro.categoria.nombre }} — SKU: {{ suministro.codigo_interno|default:"N/A" }}">
        <a href="{% url 'suministros:suministro_list' %}" class="px-4 py-2.5 rounded-xl border border-white/10 text-on-background hover:bg-white/5 transition-all text-xs font-bold">
            Volver
        </a>
    </c-page-header>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Info Card -->
        <c-glass-panel class="lg:col-span-1">
            <div class="space-y-4">
                <div class="flex items-center justify-between">
                    <span class="text-[10px] font-black text-jmie-gray uppercase tracking-widest">Stock Actual</span>
                    {% include "suministros/partials/stock_badge.html" with suministro=suministro only %}
                </div>
                <div class="text-3xl font-black tracking-tighter text-on-background">{{ suministro.stock_actual }}</div>
                <div class="pt-4 border-t border-white/5 space-y-3 text-xs text-jmie-gray font-bold">
                    <div class="flex justify-between"><span>Stock Mínimo</span><span class="text-on-background">{{ suministro.stock_minimo }}</span></div>
                    <div class="flex justify-between"><span>Unidad</span><span class="text-on-background">{{ suministro.unidad_medida }}</span></div>
                    <div class="flex justify-between"><span>Marca</span><span class="text-on-background">{{ suministro.marca|default:"—" }}</span></div>
                    <div class="flex justify-between"><span>Alternativo</span><span class="text-on-background">{% if suministro.es_alternativo %}Sí{% else %}No{% endif %}</span></div>
                </div>
                {% if perms.suministros.change_suministro %}
                <div class="pt-4 border-t border-white/5">
                    <a href="{% url 'suministros:suministro_update' suministro.pk %}" class="w-full flex items-center justify-center py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-xs font-bold transition-all border border-white/10">
                        <span class="material-symbols-outlined text-sm mr-2">edit</span> Editar Suministro
                    </a>
                </div>
                {% endif %}
            </div>
        </c-glass-panel>

        <!-- Movement History -->
        <c-glass-panel class="lg:col-span-2" title="Historial de Movimientos">
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-white/[0.02] border-b border-white/5 text-jmie-gray uppercase text-[10px] font-black tracking-widest">
                            <th class="px-4 py-3">Fecha</th>
                            <th class="px-4 py-3">Tipo</th>
                            <th class="px-4 py-3">Cantidad</th>
                            <th class="px-4 py-3">Registrado por</th>
                            <th class="px-4 py-3">Notas</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-white/5">
                        {% for m in page_obj %}
                        <tr class="hover:bg-white/[0.02] transition-colors">
                            <td class="px-4 py-3 text-xs text-jmie-gray">{{ m.fecha|date:"d/m/Y H:i" }}</td>
                            <td class="px-4 py-3">
                                <span class="px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-wider
                                    {% if m.tipo_movimiento == 'ENTRADA' %}bg-emerald-500/10 text-emerald-400 border border-emerald-500/20
                                    {% elif m.tipo_movimiento == 'SALIDA' %}bg-blue-500/10 text-blue-400 border border-blue-500/20
                                    {% elif m.tipo_movimiento == 'AJUSTE_POS' %}bg-amber-500/10 text-amber-400 border border-amber-500/20
                                    {% else %}bg-red-500/10 text-red-400 border border-red-500/20{% endif %}">
                                    {{ m.get_tipo_movimiento_display }}
                                </span>
                            </td>
                            <td class="px-4 py-3 text-xs font-bold text-on-background">{{ m.cantidad }}</td>
                            <td class="px-4 py-3 text-xs text-jmie-gray">{{ m.registrado_by.get_full_name|default:m.registrado_por.username|default:"—" }}</td>
                            <td class="px-4 py-3 text-xs text-jmie-gray max-w-xs truncate">{{ m.notas|default:"—" }}</td>
                        </tr>
                        {% empty %}
                        <tr>
                            <td colspan="5" class="px-4 py-8 text-center text-xs text-jmie-gray font-bold">Sin movimientos registrados</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% if page_obj.has_other_pages %}
            <div class="px-4 py-3 bg-white/[0.01] border-t border-white/5 flex items-center justify-between">
                <span class="text-[10px] text-jmie-gray font-bold">Página {{ page_obj.number }} de {{ page_obj.paginator.num_pages }}</span>
                <div class="flex gap-2">
                    {% if page_obj.has_previous %}
                    <a href="?page={{ page_obj.previous_page_number }}" class="px-3 py-1.5 rounded-lg bg-white/5 text-[10px] font-black text-jmie-gray hover:bg-white/10 transition-all">Anterior</a>
                    {% endif %}
                    {% if page_obj.has_next %}
                    <a href="?page={{ page_obj.next_page_number }}" class="px-3 py-1.5 rounded-lg bg-white/5 text-[10px] font-black text-jmie-gray hover:bg-white/10 transition-all">Siguiente</a>
                    {% endif %}
                </div>
            </div>
            {% endif %}
        </c-glass-panel>
    </div>
</div>
{% endblock %}
```

**Verify:** Detail page renders with movement history and pagination.  
**Commit:** `feat(suministros): add detail template with paginated movement history`

---

### Task 3.7: Movement Modal
**File:** `suministros/templates/suministros/partials/movimiento_modal.html`  
**Test:** none  
**Depends:** 2.1

```django
<div x-data="{ showModal: true }" x-show="showModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div @click="showModal = false" class="absolute inset-0 bg-black/60 backdrop-blur-sm"></div>

    <div class="relative bg-surface-container rounded-2xl border border-white/10 shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-200">
        <div class="p-6">
            <div class="flex items-center justify-between mb-6">
                <h3 class="text-xl font-bold text-on-background flex items-center gap-2">
                    <span class="material-symbols-outlined text-jmie-blue">sync_alt</span>
                    Registrar Movimiento
                </h3>
                <button @click="showModal = false" class="text-jmie-gray hover:text-on-background transition-colors">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>

            {% if suministro %}
            <div class="mb-6 p-3 bg-white/5 border border-white/10 rounded-xl">
                <p class="text-[10px] text-jmie-gray uppercase tracking-widest font-black mb-1">Suministro</p>
                <p class="text-xs text-on-background font-bold truncate">{{ suministro.nombre }} (Stock: {{ suministro.stock_actual }})</p>
            </div>
            {% endif %}

            <form hx-post="{% url 'suministros:movimiento_create' %}"
                  hx-target="#modal-container"
                  hx-disabled-elt="this"
                  class="space-y-5">
                {% csrf_token %}
                {{ form.suministro }}

                <div class="space-y-1.5">
                    <label class="text-[10px] font-black uppercase text-jmie-gray tracking-tighter ml-1">Tipo de Movimiento</label>
                    {{ form.tipo_movimiento }}
                    {% if form.tipo_movimiento.errors %}
                        <p class="mt-1 text-xs text-red-400">{{ form.tipo_movimiento.errors.0 }}</p>
                    {% endif %}
                </div>

                <div class="space-y-1.5">
                    <label class="text-[10px] font-black uppercase text-jmie-gray tracking-tighter ml-1">Cantidad</label>
                    {{ form.cantidad }}
                    {% if form.cantidad.errors %}
                        <p class="mt-1 text-xs text-red-400">{{ form.cantidad.errors.0 }}</p>
                    {% endif %}
                </div>

                <div class="space-y-1.5">
                    <label class="text-[10px] font-black uppercase text-jmie-gray tracking-tighter ml-1">Notas / Observaciones</label>
                    {{ form.notas }}
                </div>

                {% if form.non_field_errors %}
                <div class="bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                    <p class="text-xs text-red-400 font-medium">{{ form.non_field_errors.0 }}</p>
                </div>
                {% endif %}

                <div class="flex justify-end gap-3 pt-4 border-t border-white/5">
                    <button type="button" @click="showModal = false"
                            class="px-5 py-2.5 rounded-xl border border-white/10 text-on-background hover:bg-white/5 transition-all text-xs font-bold">
                        Cancelar
                    </button>
                    <button type="submit"
                            class="px-6 py-2.5 rounded-xl bg-jmie-blue text-white font-black uppercase tracking-widest text-[10px] hover:brightness-110 shadow-[0_4px_15px_rgba(0,53,148,0.3)] transition-all flex items-center gap-2">
                        <span>Confirmar</span>
                        <div class="htmx-indicator animate-spin h-3 w-3 border-2 border-white/30 border-t-white rounded-full"></div>
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
```

**Verify:** Clicking "Movimiento" on a row opens the modal; submitting with errors keeps modal open.  
**Commit:** `feat(suministros): add stock movement modal partial`

---

### Task 3.8: Soft-Delete Confirmation Modal
**File:** `suministros/templates/suministros/partials/suministro_confirm_delete.html`  
**Test:** none  
**Depends:** 2.1

```django
<div class="p-6">
    <div class="flex items-center gap-4 mb-6">
        <div class="w-12 h-12 rounded-full bg-error/10 flex items-center justify-center text-error">
            <span class="material-symbols-outlined">delete_forever</span>
        </div>
        <div>
            <h3 class="text-lg font-black tracking-tight text-on-background">Desactivar Suministro</h3>
            <p class="text-xs text-jmie-gray font-bold uppercase tracking-widest mt-0.5">{{ suministro.nombre }}</p>
        </div>
    </div>

    {% if suministro.stock_actual > 0 %}
    <div class="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-4">
        <p class="text-sm text-amber-400 font-medium leading-relaxed">
            Este suministro aún tiene <strong>{{ suministro.stock_actual }}</strong> unidades en stock. Al desactivarlo, desaparecerá del listado pero el historial de movimientos se conservará.
        </p>
    </div>
    {% endif %}

    <div class="bg-surface-container-high/50 border border-white/5 rounded-2xl p-4 mb-6">
        <p class="text-sm text-on-background font-medium leading-relaxed">
            ¿Estás seguro de que deseas desactivar este suministro? Esta acción <span class="text-error font-bold">no elimina</span> los registros históricos.
        </p>
    </div>

    <form hx-post="{% url 'suministros:suministro_delete' suministro.pk %}"
          hx-target="#modal-container"
          class="flex gap-3">
        {% csrf_token %}
        <button type="button"
                @click="showModal = false"
                class="flex-1 px-4 py-3 bg-white/5 hover:bg-white/10 text-on-background font-black text-[10px] uppercase tracking-widest rounded-xl border border-white/10 transition-all">
            Cancelar
        </button>
        <button type="submit"
                class="flex-1 px-4 py-3 bg-error hover:bg-error-container text-white font-black text-[10px] uppercase tracking-widest rounded-xl transition-all shadow-lg shadow-error/20">
            Desactivar
        </button>
    </form>
</div>
```

**Verify:** Delete button opens modal; confirming sets `esta_activo=False` and refreshes list.  
**Commit:** `feat(suministros): add soft-delete confirmation modal`

---

### Task 3.9: Modelo Options Partial (HTMX for form)
**File:** `suministros/templates/suministros/partials/modelo_options.html`  
**Test:** none  
**Depends:** 2.1

```django
{% for modelo in modelos %}
<option value="{{ modelo.pk }}">{{ modelo.nombre }} ({{ modelo.fabricante.nombre }})</option>
{% empty %}
<option value="">No hay modelos compatibles</option>
{% endfor %}
```

**Verify:** Changing categoría in create/update form dynamically loads compatible modelos.  
**Commit:** `feat(suministros): add modelo options HTMX partial`

---

### Task 3.10: Low-Stock Dashboard Widget
**File:** `suministros/templates/suministros/components/low_stock_alert.html`  
**Test:** none  
**Depends:** 2.1, 3.4

```django
{% if bajo_stock_count > 0 %}
<div class="p-4 bg-amber-500/5 border border-amber-500/10 rounded-xl">
    <div class="flex items-center gap-3 mb-3">
        <span class="material-symbols-outlined text-amber-400">warning</span>
        <h4 class="text-sm font-black text-on-background tracking-tight">Alerta de Stock Bajo</h4>
        <span class="ml-auto px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 text-[10px] font-black uppercase tracking-wider">{{ bajo_stock_count }}</span>
    </div>
    <ul class="space-y-2">
        {% for s in bajo_stock_items %}
        <li class="flex items-center justify-between text-xs">
            <a href="{% url 'suministros:suministro_detail' s.pk %}" class="text-jmie-gray hover:text-jmie-orange transition-colors font-bold truncate max-w-[70%]">
                {{ s.nombre }}
            </a>
            {% include "suministros/partials/stock_badge.html" with suministro=s only %}
        </li>
        {% endfor %}
    </ul>
    {% if bajo_stock_count > 5 %}
    <a href="{% url 'suministros:suministro_list' %}?alerta=bajo_stock" class="mt-3 block text-[10px] font-black uppercase tracking-widest text-jmie-orange hover:underline">
        Ver todos los alertas →
    </a>
    {% endif %}
</div>
{% endif %}
```

**Verify:** Include this component in dashboard context where `bajo_stock_items` and `bajo_stock_count` are provided.  
**Commit:** `feat(suministros): add low-stock dashboard widget component`

---

## Batch 4: Unit & Integration Tests (parallel — 2 implementers, depends on Batch 1–3)

### Task 4.1: View Unit & Integration Tests
**File:** `suministros/tests/test_views.py`  
**Test:** self-contained (pytest)  
**Depends:** 1.1, 1.4, 2.1

```python
import pytest
from django.urls import reverse
from suministros.tests.factories import SuministroFactory, CategoriaSuministroFactory, MovimientoStockFactory
from core.tests.factories import ColaboradorFactory


@pytest.mark.django_db
class TestSuministroViews:
    @pytest.fixture
    def admin_user(self):
        user = ColaboradorFactory(username='admin_test', is_staff=True, is_superuser=True)
        user.set_password('pass')
        user.save()
        return user

    @pytest.fixture
    def tecnico_user(self):
        user = ColaboradorFactory(username='tecnico_test')
        user.set_password('pass')
        user.save()
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from suministros.models import Suministro, MovimientoStock
        ct_s = ContentType.objects.get_for_model(Suministro)
        ct_m = ContentType.objects.get_for_model(MovimientoStock)
        user.user_permissions.add(
            Permission.objects.get(codename='view_suministro', content_type=ct_s),
            Permission.objects.get(codename='add_movimientostock', content_type=ct_m),
        )
        return user

    @pytest.fixture
    def auditor_user(self):
        user = ColaboradorFactory(username='auditor_test')
        user.set_password('pass')
        user.save()
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from suministros.models import Suministro
        ct = ContentType.objects.get_for_model(Suministro)
        user.user_permissions.add(Permission.objects.get(codename='view_suministro', content_type=ct))
        return user

    def test_list_standard_request(self, client, admin_user):
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_list'))
        assert response.status_code == 200
        assert '<html' in response.content.decode()

    def test_list_htmx_returns_partial(self, client, admin_user):
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_list'), HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert '<html' not in response.content.decode()
        assert 'suministros/partials/suministro_list_table.html' in [t.name for t in response.templates]

    def test_list_search_filters(self, client, admin_user):
        cat = CategoriaSuministroFactory(nombre="Tintas")
        SuministroFactory(nombre="Tinta Negra", categoria=cat)
        SuministroFactory(nombre="Papel A4", categoria=CategoriaSuministroFactory(nombre="Papel"))
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_list'), {'q': 'Tinta'})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Tinta Negra' in content
        assert 'Papel A4' not in content

    def test_list_pagination(self, client, admin_user):
        cat = CategoriaSuministroFactory()
        for i in range(25):
            SuministroFactory(nombre=f"Suministro {i}", categoria=cat)
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_list'))
        assert response.status_code == 200
        page_obj = response.context['page_obj']
        assert len(page_obj.object_list) == 20
        assert page_obj.has_next()

    def test_create_view_requires_add_permission(self, client, tecnico_user):
        client.login(username='tecnico_test', password='pass')
        response = client.get(reverse('suministros:suministro_create'))
        assert response.status_code == 403

    def test_create_view_as_admin(self, client, admin_user):
        client.login(username='admin_test', password='pass')
        cat = CategoriaSuministroFactory()
        response = client.post(reverse('suministros:suministro_create'), {
            'nombre': 'Nuevo Toner',
            'categoria': cat.pk,
            'codigo_interno': 'TONER-01',
            'unidad_medida': 'Unidades',
            'stock_minimo': 2,
        })
        assert response.status_code == 302 or response.status_code == 204
        from suministros.models import Suministro
        assert Suministro.objects.filter(nombre='Nuevo Toner').exists()

    def test_detail_view_shows_movements(self, client, admin_user):
        s = SuministroFactory()
        MovimientoStockFactory(suministro=s, cantidad=5)
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_detail', args=[s.pk]))
        assert response.status_code == 200
        assert response.context['suministro'] == s
        assert len(response.context['page_obj'].object_list) == 1

    def test_soft_delete_sets_inactive(self, client, admin_user):
        s = SuministroFactory()
        client.login(username='admin_test', password='pass')
        response = client.post(reverse('suministros:suministro_delete', args=[s.pk]))
        assert response.status_code == 204
        s.refresh_from_db()
        assert s.esta_activo is False

    def test_auditor_cannot_create_movement(self, client, auditor_user):
        s = SuministroFactory()
        client.login(username='auditor_test', password='pass')
        response = client.get(reverse('suministros:movimiento_create'), {'suministro': s.pk})
        assert response.status_code == 403

    def test_tecnico_can_create_movement(self, client, tecnico_user):
        s = SuministroFactory(stock_actual=10)
        client.login(username='tecnico_test', password='pass')
        response = client.post(reverse('suministros:movimiento_create'), {
            'suministro': s.pk,
            'tipo_movimiento': 'SALIDA',
            'cantidad': 2,
            'notas': 'Entrega',
        })
        assert response.status_code == 204
        s.refresh_from_db()
        assert s.stock_actual == 8

    def test_movement_validation_error_returns_modal(self, client, tecnico_user):
        s = SuministroFactory(stock_actual=1)
        client.login(username='tecnico_test', password='pass')
        response = client.post(reverse('suministros:movimiento_create'), {
            'suministro': s.pk,
            'tipo_movimiento': 'SALIDA',
            'cantidad': 5,
            'notas': 'Fail',
        })
        assert response.status_code == 200
        content = response.content.decode()
        assert 'modal-container' not in content  # modal HTML returned
        assert 'No hay suficiente stock' in content

    def test_ajax_modelos_compatibles(self, client, admin_user):
        from core.tests.factories import TipoDispositivoFactory, FabricanteFactory, ModeloFactory
        tipo = TipoDispositivoFactory()
        cat = CategoriaSuministroFactory()
        cat.tipos_dispositivo_compatibles.add(tipo)
        fab = FabricanteFactory()
        modelo = ModeloFactory(tipo_dispositivo=tipo, fabricante=fab)
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:ajax_get_modelos_compatibles'), {'categoria': cat.pk})
        assert response.status_code == 200
        assert modelo.nombre in response.content.decode()
```

**Verify:** `pytest suministros/tests/test_views.py -v --reuse-db`  
**Commit:** `test(suministros): add view unit and permission tests`

---

### Task 4.2: Integration Tests (Full Flow)
**File:** `suministros/tests/test_integration.py`  
**Test:** self-contained (pytest)  
**Depends:** 1.1, 1.4, 2.1

```python
import pytest
from django.urls import reverse
from suministros.tests.factories import SuministroFactory, CategoriaSuministroFactory
from core.tests.factories import ColaboradorFactory
from suministros.models import MovimientoStock


@pytest.mark.django_db
class TestSuministrosIntegration:
    @pytest.fixture
    def admin(self):
        u = ColaboradorFactory(username='int_admin', is_superuser=True)
        u.set_password('pass')
        u.save()
        return u

    def test_full_stock_flow(self, client, admin):
        """Crear suministro → entrada → salida → verificar stock → oversale → error"""
        client.login(username='int_admin', password='pass')
        cat = CategoriaSuministroFactory()

        # 1. Crear
        response = client.post(reverse('suministros:suministro_create'), {
            'nombre': 'Tóner X',
            'categoria': cat.pk,
            'codigo_interno': 'TN-X',
            'unidad_medida': 'Unidades',
            'stock_minimo': 2,
        })
        assert response.status_code in (302, 204)
        from suministros.models import Suministro
        s = Suministro.objects.get(nombre='Tóner X')
        assert s.stock_actual == 0

        # 2. Entrada 10
        response = client.post(reverse('suministros:movimiento_create'), {
            'suministro': s.pk,
            'tipo_movimiento': MovimientoStock.TipoMovimiento.ENTRADA,
            'cantidad': 10,
            'notas': 'Compra',
        })
        assert response.status_code == 204
        s.refresh_from_db()
        assert s.stock_actual == 10

        # 3. Salida 3
        response = client.post(reverse('suministros:movimiento_create'), {
            'suministro': s.pk,
            'tipo_movimiento': MovimientoStock.TipoMovimiento.SALIDA,
            'cantidad': 3,
            'notas': 'Entrega',
        })
        assert response.status_code == 204
        s.refresh_from_db()
        assert s.stock_actual == 7

        # 4. Oversale
        response = client.post(reverse('suministros:movimiento_create'), {
            'suministro': s.pk,
            'tipo_movimiento': MovimientoStock.TipoMovimiento.SALIDA,
            'cantidad': 99,
            'notas': 'Fail',
        })
        assert response.status_code == 200
        s.refresh_from_db()
        assert s.stock_actual == 7  # sin cambio

        # 5. Soft delete
        response = client.post(reverse('suministros:suministro_delete', args=[s.pk]))
        assert response.status_code == 204
        s.refresh_from_db()
        assert s.esta_activo is False

    def test_list_excludes_inactive(self, client, admin):
        client.login(username='int_admin', password='pass')
        cat = CategoriaSuministroFactory()
        active = SuministroFactory(nombre="Activo", categoria=cat, esta_activo=True)
        inactive = SuministroFactory(nombre="Inactivo", categoria=cat, esta_activo=False)

        response = client.get(reverse('suministros:suministro_list'))
        content = response.content.decode()
        assert 'Activo' in content
        assert 'Inactivo' not in content

    def test_htmx_partial_vs_full_page(self, client, admin):
        client.login(username='int_admin', password='pass')
        SuministroFactory()

        # Full page
        response = client.get(reverse('suministros:suministro_list'))
        assert '<html' in response.content.decode()

        # HTMX partial
        response = client.get(reverse('suministros:suministro_list'), HTTP_HX_REQUEST='true')
        assert '<html' not in response.content.decode()
        assert '<table' in response.content.decode()
```

**Verify:** `pytest suministros/tests/test_integration.py -v --reuse-db`  
**Commit:** `test(suministros): add end-to-end integration tests for stock flow`

---

## Batch 5: E2E Tests (parallel — 2 implementers, depends on Batch 1–4)

### Task 5.1: E2E Page Objects
**File:** `tests_e2e/pages/suministros_pages.py`  
**Test:** none (supporting code)  
**Depends:** 2.1, 3.1

```python
from playwright.sync_api import Page, expect


class SuministrosListPage:
    def __init__(self, page: Page):
        self.page = page
        self.table = page.locator('table')
        self.search_input = page.locator('input[name="q"]')
        self.new_button = page.locator('a:has-text("Nuevo Suministro")')
        self.modal_container = page.locator('#modal-container')

    def navigate(self, base_url):
        self.page.goto(f"{base_url}/suministros/")

    def search(self, query: str):
        self.search_input.fill(query)
        self.search_input.press('Enter')

    def row_by_name(self, name: str):
        return self.page.locator(f'tr:has-text("{name}")')

    def expect_row_visible(self, name: str):
        expect(self.row_by_name(name)).to_be_visible()

    def open_movement_modal(self, name: str):
        row = self.row_by_name(name)
        row.locator('button:has-text("Movimiento")').click()

    def stock_badge(self, name: str):
        return self.row_by_name(name).locator('span').filter(has_text=re.compile(r'(OK|Bajo|Sin)'))


class MovimientoModal:
    def __init__(self, page: Page):
        self.page = page
        self.modal = page.locator('#modal-container >> div >> div >> div').first
        self.tipo_select = page.locator('select[name="tipo_movimiento"]')
        self.cantidad_input = page.locator('input[name="cantidad"]')
        self.notas_input = page.locator('textarea[name="notas"]')
        self.submit_button = page.locator('button:has-text("Confirmar")')
        self.close_button = page.locator('button:has-text("Cancelar")')

    def fill(self, tipo: str, cantidad: str, notas: str = ""):
        self.page.select_option('select[name="tipo_movimiento"]', tipo)
        self.cantidad_input.fill(cantidad)
        if notas:
            self.notas_input.fill(notas)

    def submit(self):
        self.submit_button.click()

    def expect_visible(self):
        expect(self.modal).to_be_visible()

    def expect_error(self, message: str):
        expect(self.page.locator('text=' + message)).to_be_visible()
```

**Note:** Add `import re` at the top of the file if using `re.compile`.

**Verify:** `pytest tests_e2e/test_suministros_flow.py -v --co` (collect-only to ensure imports work)  
**Commit:** `test(e2e): add page objects for suministros list and movement modal`

---

### Task 5.2: E2E Test Flow
**File:** `tests_e2e/test_suministros_flow.py`  
**Test:** self-contained (pytest-playwright)  
**Depends:** 5.1

```python
import pytest
from playwright.sync_api import Page, expect
from core.tests.factories import ColaboradorFactory
from suministros.tests.factories import CategoriaSuministroFactory, SuministroFactory
from .pages.inventory_pages import LoginPage
from .pages.suministros_pages import SuministrosListPage, MovimientoModal


@pytest.fixture
def test_user(db):
    user = ColaboradorFactory(username='e2e_suministros', is_superuser=True, is_staff=True)
    user.set_password('12345')
    user.save()
    return user


@pytest.mark.e2e
@pytest.mark.django_db
def test_suministros_list_and_stock_badge(live_server, page: Page, test_user):
    cat = CategoriaSuministroFactory(nombre="Tintas")
    SuministroFactory(nombre="Tinta Negra", categoria=cat, stock_actual=10, stock_minimo=2)
    SuministroFactory(nombre="Tinta Cyan", categoria=cat, stock_actual=1, stock_minimo=2)
    SuministroFactory(nombre="Tinta Magenta", categoria=cat, stock_actual=0, stock_minimo=2)

    # Login
    login = LoginPage(page)
    login.navigate(live_server.url + "/login/")
    login.login('e2e_suministros', '12345')
    page.wait_for_url(live_server.url + "/")

    # Navigate
    list_page = SuministrosListPage(page)
    list_page.navigate(live_server.url)
    expect(page.locator('h1')).to_contain_text('Gestión de Suministros')

    # Verify rows and badges
    list_page.expect_row_visible('Tinta Negra')
    list_page.expect_row_visible('Tinta Cyan')
    list_page.expect_row_visible('Tinta Magenta')


@pytest.mark.e2e
@pytest.mark.django_db
def test_register_movement_updates_stock(live_server, page: Page, test_user):
    cat = CategoriaSuministroFactory()
    s = SuministroFactory(nombre="Papel A4", categoria=cat, stock_actual=5, stock_minimo=2)

    login = LoginPage(page)
    login.navigate(live_server.url + "/login/")
    login.login('e2e_suministros', '12345')
    page.wait_for_url(live_server.url + "/")

    list_page = SuministrosListPage(page)
    list_page.navigate(live_server.url)

    # Open modal
    list_page.open_movement_modal('Papel A4')
    modal = MovimientoModal(page)
    modal.expect_visible()

    # Fill and submit
    modal.fill('SALIDA', '2', 'Entrega a operaciones')
    modal.submit()

    # Toast + updated badge (wait for HTMX refresh)
    expect(page.locator('text=Movimiento registrado')).to_be_visible(timeout=5000)
    expect(list_page.row_by_name('Papel A4').locator('text=OK (3)')).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db
def test_oversale_shows_error_in_modal(live_server, page: Page, test_user):
    cat = CategoriaSuministroFactory()
    s = SuministroFactory(nombre="Tóner", categoria=cat, stock_actual=1, stock_minimo=1)

    login = LoginPage(page)
    login.navigate(live_server.url + "/login/")
    login.login('e2e_suministros', '12345')
    page.wait_for_url(live_server.url + "/")

    list_page = SuministrosListPage(page)
    list_page.navigate(live_server.url)
    list_page.open_movement_modal('Tóner')

    modal = MovimientoModal(page)
    modal.fill('SALIDA', '99')
    modal.submit()

    modal.expect_error('No hay suficiente stock')
```

**Verify:** `pytest tests_e2e/test_suministros_flow.py -m e2e --headed --browser chromium`  
**Commit:** `test(e2e): add suministros CRUD and movement flow tests`

---

## Verification Steps (per Phase)

### After Batch 1
- [ ] `python manage.py makemigrations --check` passes (no missing migrations)
- [ ] `python manage.py migrate` applies cleanly
- [ ] `pytest suministros/tests/test_models.py -v` passes

### After Batch 2
- [ ] `python manage.py check` passes
- [ ] All new URL reversals work: `python manage.py shell -c "from django.urls import reverse; [reverse(f'suministros:{n}') for n in ('suministro_list','suministro_create','suministro_update','suministro_detail','suministro_delete','movimiento_create','ajax_get_modelos_compatibles')]"`

### After Batch 3
- [ ] No `TemplateDoesNotExist` errors when accessing any new view
- [ ] HTMX partial responses exclude `<html>` / `<body>`
- [ ] Modal opens and closes correctly
- [ ] Stock badges show correct colors (green/yellow/red)

### After Batch 4
- [ ] `pytest suministros/tests/test_views.py -v --reuse-db` passes
- [ ] `pytest suministros/tests/test_integration.py -v --reuse-db` passes
- [ ] Coverage for `suministros/views.py` ≥ 80%: `pytest --cov=suministros.views --cov-report=term-missing`

### After Batch 5
- [ ] `pytest tests_e2e/test_suministros_flow.py -m e2e --browser chromium` passes
- [ ] Full TDD cycle verified: tests written → fail → implement → pass

---

## Final Checklist

- [ ] All URLs follow `[model_name]_[action]` convention
- [ ] `render_actions` works for `Suministro` (requires `suministro_detail`, `suministro_update`, `suministro_delete`)
- [ ] `BaseStyledForm` reused (existing `SuministroForm` / `MovimientoStockForm`)
- [ ] `core/htmx.py` helpers used (`htmx_trigger_response`, `htmx_render_or_redirect`)
- [ ] Service layer (`registrar_movimiento_stock`) reused; no business logic duplicated in views
- [ ] Soft delete implemented via `esta_activo` (not hard `DELETE`)
- [ ] Permission groups respected: Auditores read-only, Técnicos movements, Administradores full CRUD
- [ ] Low-stock dashboard widget reusable via `{% include "suministros/components/low_stock_alert.html" %}`
