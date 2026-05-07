from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django import forms
from django.forms import formset_factory
from django.http import HttpResponse
from django.utils import timezone

from core.htmx import htmx_trigger_response, htmx_render_or_redirect, htmx_success_or_redirect
from core.models import Modelo, Fabricante, CentroCosto
from colaboradores.models import Colaborador
from .models import Suministro, MovimientoStock, CategoriaSuministro
from .forms import SuministroForm, MovimientoStockForm, CategoriaSuministroForm, FacturaCabeceraForm, MovimientoFacturaForm
from .services import registrar_movimiento_stock, get_pack_siblings, registrar_movimiento_pack
from .resources import SuministroResource, MovimientoStockResource


@login_required
def ajax_get_pack_siblings(request):
    """HTMX: retorna los suministros hermanos de un pack basado en compatibilidad."""
    suministro_id = request.GET.get('suministro')
    if not suministro_id:
        return HttpResponse("")
    
    suministro = get_object_or_404(Suministro, pk=suministro_id)
    siblings = get_pack_siblings(suministro)
    
    return render(request, 'suministros/partials/pack_siblings_rows.html', {
        'siblings': siblings,
        'suministro_base': suministro,
    })


@login_required
@permission_required('suministros.add_movimientostock', raise_exception=True)
def movimiento_pack_create(request):
    """Carga modal para movimiento de múltiples suministros (Pack)."""
    ids_str = request.GET.get('ids', '') or request.POST.get('ids', '')
    suministro_ids = [int(sid) for sid in ids_str.split(',') if sid.strip().isdigit()]
    
    if not suministro_ids:
        # Si no hay IDs, quizás se disparó desde un solo suministro pidiendo pack
        base_id = request.GET.get('base_id')
        if base_id:
            base_sum = get_object_or_404(Suministro, pk=base_id)
            suministro_ids = [base_sum.id] + list(get_pack_siblings(base_sum).values_list('id', flat=True))
    
    suministros = Suministro.objects.filter(id__in=suministro_ids).select_related('categoria', 'fabricante')
    
    if request.method == 'POST':
        # Procesamiento manual de datos de pack para evitar complejidad de formsets en modal Alpine
        tipo = request.POST.get('tipo_movimiento')
        colaborador_id = request.POST.get('colaborador_destino')
        centro_costo_id = request.POST.get('centro_costo')
        dispositivo_id = request.POST.get('dispositivo_destino')
        notas = request.POST.get('notas', '')
        
        movimientos_data = []
        for s in suministros:
            qty = request.POST.get(f'qty_{s.id}', 0)
            if qty and int(qty) > 0:
                movimientos_data.append({
                    'suministro_id': s.id,
                    'cantidad': int(qty),
                })
        
        if not movimientos_data:
            messages.error(request, "Debe ingresar al menos una cantidad válida.")
        else:
            try:
                registrar_movimiento_pack(
                    movimientos_data=movimientos_data,
                    tipo_movimiento=tipo,
                    registrado_por_id=request.user.id,
                    colaborador_destino_id=colaborador_id or None,
                    centro_costo_id=centro_costo_id or None,
                    dispositivo_destino_id=dispositivo_id or None,
                    notas_comunes=notas
                )
                return htmx_trigger_response(
                    trigger={
                        'refreshSuministroList': '',
                        'show-notification': {'message': 'Movimientos de pack registrados', 'type': 'success'}
                    },
                    status=204
                )
            except ValidationError as e:
                messages.error(request, f"Error: {str(e)}")
            except Exception as e:
                messages.error(request, f"Error inesperado: {str(e)}")

    # GET o POST con error
    # Usamos MovimientoStockForm solo para renderizar los campos comunes (destinatario, etc)
    form = MovimientoStockForm()
    
    return render(request, 'suministros/partials/movimiento_pack_modal.html', {
        'suministros': suministros,
        'form': form,
        'ids_str': ",".join(map(str, suministro_ids)),
    })


@login_required
def suministro_list(request):
    """Listado de suministros con búsqueda, filtro por categoría/fabricante y paginación."""
    query = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')
    fabricante_id = request.GET.get('fabricante', '')

    suministros = Suministro.objects.activos().select_related('categoria', 'fabricante')

    modelos_list = Modelo.objects.all().order_by('nombre')
    if categoria_id:
        suministros = suministros.filter(categoria_id=categoria_id)
        # Filtrar modelos que pertenecen a tipos compatibles con esta categoría
        try:
            categoria = CategoriaSuministro.objects.get(pk=categoria_id)
            tipos = categoria.tipos_dispositivo_compatibles.all()
            if tipos.exists():
                modelos_list = modelos_list.filter(tipo_dispositivo__in=tipos)
        except CategoriaSuministro.DoesNotExist:
            pass

    if fabricante_id:
        suministros = suministros.filter(fabricante_id=fabricante_id)

    modelos_ids_str = request.GET.get('modelos', '')
    if modelos_ids_str:
        modelos_ids = [m_id for m_id in modelos_ids_str.split(',') if m_id.strip().isdigit()]
        if modelos_ids:
            suministros = suministros.filter(modelos_compatibles__id__in=modelos_ids).distinct()

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
        'modelos_list': Modelo.objects.all().select_related('fabricante').order_by('nombre'),
        'query': query,
        'categoria_id': categoria_id,
        'fabricante_id': fabricante_id,
        'modelos_seleccionados': request.GET.get('modelos', ''),
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
                trigger={
                    'refreshSuministroList': '', 
                    'show-notification': {'message': f'Suministro "{suministro.nombre}" creado', 'type': 'success'},
                    'suministroCreated': {'id': suministro.id, 'nombre': suministro.nombre}
                },
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
def ajax_suministro_options(request):
    """HTMX: retorna opciones <option> para refrescar los select de suministros."""
    suministros = Suministro.objects.activos().order_by('nombre')
    selected_id = request.GET.get('selected', '')
    return render(request, 'suministros/partials/suministro_options.html', {
        'suministros': suministros,
        'selected_id': selected_id,
    })


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
                trigger={'refreshSuministroList': '', 'show-notification': {'message': f'Suministro "{suministro.nombre}" actualizado', 'type': 'success'}},
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
            trigger={'refreshSuministroList': '', 'show-notification': {'message': 'Suministro desactivado', 'type': 'info'}},
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

                if cd.get('seguir_ingresando'):
                    params = f"?tipo_movimiento={cd['tipo_movimiento']}"
                    if cd.get('numero_factura'):
                        params += f"&numero_factura={cd['numero_factura']}"
                    if suministro:
                        params += f"&suministro={suministro.pk}"
                    
                    return redirect(reverse('suministros:movimiento_create') + params)

                return htmx_trigger_response(
                    trigger={
                        'refreshSuministroList': '',
                        'show-notification': {'message': 'Movimiento registrado', 'type': 'success'}
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
    initial = request.GET.dict()
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


@login_required
def ajax_colaborador_centro_costo(request):
    """HTMX: retorna opciones de centro de costo con el del colaborador pre-seleccionado."""
    colaborador_id = request.GET.get('colaborador_destino') or request.GET.get('colaborador')
    selected = None
    if colaborador_id:
        try:
            colaborador = Colaborador.objects.get(pk=colaborador_id)
            selected = colaborador.centro_costo_id
        except (ValueError, TypeError, Colaborador.DoesNotExist):
            pass

    return render(request, 'suministros/partials/centro_costo_options.html', {
        'centros_costo': CentroCosto.objects.filter(activa=True).order_by('nombre'),
        'selected': selected,
    })


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
                trigger={'categoriaListChanged': True, 'show-notification': {'message': f'Categoría "{categoria.nombre}" creada', 'type': 'success'}},
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
                trigger={'categoriaListChanged': True, 'show-notification': {'message': 'Categoría actualizada', 'type': 'success'}},
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


@login_required
@permission_required('suministros.add_movimientostock', raise_exception=True)
def factura_create(request):
    """Carga masiva de facturas usando formsets."""
    MovimientoFormSet = formset_factory(MovimientoFacturaForm, extra=3, min_num=1, validate_min=True)
    
    if request.method == 'POST':
        cabecera_form = FacturaCabeceraForm(request.POST)
        formset = MovimientoFormSet(request.POST)
        
        if cabecera_form.is_valid() and formset.is_valid():
            numero_factura = cabecera_form.cleaned_data['numero_factura']
            
            try:
                with transaction.atomic():
                    for form in formset:
                        if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                            cd = form.cleaned_data
                            registrar_movimiento_stock(
                                suministro_id=cd['suministro'].id,
                                tipo_movimiento=MovimientoStock.TipoMovimiento.ENTRADA,
                                cantidad=cd['cantidad'],
                                registrado_por_id=request.user.id,
                                costo_unitario=cd.get('costo_unitario'),
                                numero_factura=numero_factura,
                                notas=cd.get('notas', ''),
                            )
                
                messages.success(request, f"Factura {numero_factura} registrada con éxito.")
                return redirect('suministros:suministro_list')
            except ValidationError as e:
                messages.error(request, f"Error de validación: {str(e)}")
            except Exception as e:
                messages.error(request, f"Error al registrar la factura: {str(e)}")
    else:
        cabecera_form = FacturaCabeceraForm()
        formset = MovimientoFormSet()
        
    context = {
        'cabecera_form': cabecera_form,
        'formset': formset,
        'titulo': 'Ingreso de Factura',
    }
    
    return render(request, 'suministros/factura_form.html', context)


# ── Exportaciones Excel ────────────────────────────────────────────────────

@login_required
@permission_required('suministros.view_suministro', raise_exception=True)
def suministro_export_excel(request):
    """Exporta el catálogo de suministros a Excel respetando los filtros aplicados."""
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

    dataset = SuministroResource().export(suministros)
    response = HttpResponse(
        dataset.export('xlsx'),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="Suministros_JMIE_{timezone.now().date()}.xlsx"'
    return response


@login_required
@permission_required('suministros.view_movimientostock', raise_exception=True)
def suministro_movimientos_export_excel(request, pk):
    """Exporta el historial de movimientos de un suministro específico a Excel."""
    suministro = get_object_or_404(Suministro, pk=pk)
    movimientos = suministro.movimientos.select_related(
        'registrado_por', 'colaborador_destino', 'centro_costo', 'dispositivo_destino'
    ).order_by('-fecha')

    dataset = MovimientoStockResource().export(movimientos)
    response = HttpResponse(
        dataset.export('xlsx'),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="Movimientos_{suministro.nombre.replace(" ", "_")}_{timezone.now().date()}.xlsx"'
    return response
