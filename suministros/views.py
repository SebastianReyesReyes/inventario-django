from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django import forms

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
