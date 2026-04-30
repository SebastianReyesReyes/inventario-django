from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django import forms

from core.htmx import htmx_trigger_response, htmx_render_or_redirect, htmx_success_or_redirect
from core.models import Modelo, Fabricante
from .models import Suministro, MovimientoStock, CategoriaSuministro
from .forms import SuministroForm, MovimientoStockForm, CategoriaSuministroForm
from .services import registrar_movimiento_stock


@login_required
def suministro_list(request):
    """Listado de suministros con búsqueda, filtro por categoría/fabricante y paginación."""
    query = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')
    fabricante_id = request.GET.get('fabricante', '')

    suministros = Suministro.objects.activos().select_related('categoria', 'fabricante')

    if categoria_id:
        suministros = suministros.filter(categoria_id=categoria_id)

    if fabricante_id:
        suministros = suministros.filter(fabricante_id=fabricante_id)

    if query:
        suministros = suministros.filter(
            Q(nombre__icontains=query) |
            Q(codigo_interno__icontains=query) |
            Q(fabricante__nombre__icontains=query)
        )

    # Paginación: 20 items por página
    paginator = Paginator(suministros, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'suministros': page_obj.object_list,
        'categorias': CategoriaSuministro.objects.all(),
        'fabricantes_list': Fabricante.objects.all().order_by('nombre'),
        'query': query,
        'categoria_id': categoria_id,
        'fabricante_id': fabricante_id,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'suministros/partials/suministro_list_table.html', context)

    return render(request, 'suministros/suministro_list.html', context)


@login_required
@permission_required('suministros.add_suministro', raise_exception=True)
def suministro_create(request):
    """Crear suministro — HTMX modal o página completa."""
    if request.method == 'POST':
        form = SuministroForm(request.POST)
        if form.is_valid():
            suministro = form.save()
            return htmx_success_or_redirect(
                request,
                redirect_url='suministros:suministro_list',
                trigger={'refreshSuministroList': '', 'showToast': {'message': f'Suministro "{suministro.nombre}" creado', 'type': 'success'}},
            )
    else:
        form = SuministroForm()

    context = {
        'form': form,
        'titulo': 'Nuevo Suministro',
        'action': 'Crear',
    }

    if request.headers.get('HX-Request'):
        return render(request, 'suministros/partials/suministro_form_modal.html', context)
    return render(request, 'suministros/suministro_form.html', context)


@login_required
@permission_required('suministros.change_suministro', raise_exception=True)
def suministro_update(request, pk):
    """Editar suministro — HTMX modal o página completa."""
    suministro = get_object_or_404(Suministro, pk=pk)
    if request.method == 'POST':
        form = SuministroForm(request.POST, instance=suministro)
        if form.is_valid():
            form.save()
            return htmx_success_or_redirect(
                request,
                redirect_url='suministros:suministro_list',
                trigger={'refreshSuministroList': '', 'showToast': {'message': f'Suministro "{suministro.nombre}" actualizado', 'type': 'success'}},
            )
    else:
        form = SuministroForm(instance=suministro)

    context = {
        'form': form,
        'suministro': suministro,
        'titulo': 'Editar Suministro',
        'action': 'Guardar Cambios',
    }

    if request.headers.get('HX-Request'):
        return render(request, 'suministros/partials/suministro_form_modal.html', context)
    return render(request, 'suministros/suministro_form.html', context)


@login_required
def suministro_detail(request, pk):
    """Detalle de suministro con historial de movimientos paginado."""
    suministro = get_object_or_404(
        Suministro.objects.select_related('categoria').prefetch_related('modelos_compatibles'),
        pk=pk
    )

    movimientos = suministro.movimientos.select_related('registrado_por', 'colaborador_destino', 'centro_costo', 'dispositivo_destino')
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
                    dispositivo_destino_id=cd.get('dispositivo_destino').id if cd.get('dispositivo_destino') else None,
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


@login_required
def ajax_get_dispositivos_compatibles(request):
    """Retorna dispositivos compatibles con un suministro (para campo dispositivo_destino en movimientos)."""
    from dispositivos.models import Dispositivo
    
    suministro_id = request.GET.get('suministro')
    dispositivos = Dispositivo.objects.select_related('modelo', 'modelo__tipo_dispositivo').all().order_by('modelo__nombre')
    
    if suministro_id:
        try:
            suministro = Suministro.objects.get(pk=suministro_id)
            modelos_ids = suministro.modelos_compatibles.values_list('id', flat=True)
            if modelos_ids:
                dispositivos = dispositivos.filter(modelo_id__in=modelos_ids)
        except (ValueError, TypeError, Suministro.DoesNotExist):
            pass
    
    return render(request, 'suministros/partials/dispositivo_options.html', {'dispositivos': dispositivos})


# ── Categoría de Suministro: CRUD inline (HTMX modal) ──────────────────────

@login_required
@permission_required('suministros.add_categoriasuministro', raise_exception=True)
def categoriasuministro_create(request):
    """Crear categoría — HTMX modal o página completa."""
    if request.method == 'POST':
        form = CategoriaSuministroForm(request.POST)
        if form.is_valid():
            categoria = form.save()
            return htmx_success_or_redirect(
                request,
                redirect_url='suministros:suministro_list',
                trigger={'categoriaListChanged': True, 'showToast': {'message': f'Categoría "{categoria.nombre}" creada', 'type': 'success'}},
            )
    else:
        form = CategoriaSuministroForm()

    context = {'form': form, 'titulo': 'Nueva Categoría'}
    if request.headers.get('HX-Request'):
        return render(request, 'suministros/partials/categoria_form.html', context)
    return render(request, 'suministros/categoria_form.html', context)


@login_required
@permission_required('suministros.change_categoriasuministro', raise_exception=True)
def categoriasuministro_update(request, pk):
    """Editar categoría — HTMX modal o página completa."""
    categoria = get_object_or_404(CategoriaSuministro, pk=pk)
    if request.method == 'POST':
        form = CategoriaSuministroForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            return htmx_success_or_redirect(
                request,
                redirect_url='suministros:suministro_list',
                trigger={'categoriaListChanged': True, 'showToast': {'message': 'Categoría actualizada', 'type': 'success'}},
            )
    else:
        form = CategoriaSuministroForm(instance=categoria)

    context = {'form': form, 'categoria': categoria, 'titulo': 'Editar Categoría'}
    if request.headers.get('HX-Request'):
        return render(request, 'suministros/partials/categoria_form.html', context)
    return render(request, 'suministros/categoria_form.html', context)


@login_required
def ajax_categoria_options(request):
    """HTMX: retorna opciones <option> para refrescar el select de categoría."""
    categorias = CategoriaSuministro.objects.all().order_by('nombre')
    selected = request.GET.get('selected', '')
    return render(request, 'suministros/partials/categoria_options.html', {
        'categorias': categorias,
        'selected': selected,
    })
