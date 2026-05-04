from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q, OuterRef, Subquery, ProtectedError

from core.models import TipoDispositivo, EstadoDispositivo
from ..models import Dispositivo, HistorialAsignacion
from ..services import DispositivoFactory, DispositivoService
from core.htmx import htmx_redirect_or_redirect, is_htmx, htmx_trigger_response
from core.pagination import paginate_queryset
from .. import helpers


@login_required
@permission_required('dispositivos.add_dispositivo', raise_exception=True)
def dispositivo_create(request):
    """Vista para crear un nuevo dispositivo general o específico."""
    tech_forms = {
        key: FormClass(request.POST if request.method == 'POST' else None)
        for key, FormClass in helpers.TECH_FORMS.items()
    }

    if request.method == 'POST':
        tipo_id = request.POST.get('tipo')
        form = DispositivoFactory.create_form_instance(request.POST, request.FILES, tipo_id)

        if form.is_valid():
            dispositivo, acta = DispositivoService.registrar_dispositivo_con_acta(
                form, request.user
            )

            if acta:
                messages.success(
                    request,
                    f"Equipo registrado y acta {acta.folio} generada correctamente."
                )
                return render(request, 'dispositivos/dispositivo_detail.html', {
                    'd': dispositivo,
                    'show_acta_modal': True,
                    'acta': acta,
                })

            messages.success(request, "Equipo registrado correctamente.")
            return redirect('dispositivos:dispositivo_detail', pk=dispositivo.pk)
    else:
        form = DispositivoFactory.create_form_instance()

    return render(request, 'dispositivos/dispositivo_form.html', {
        'form': form,
        'tech_forms': tech_forms,
        'titulo': 'Registrar Nuevo Equipo'
    })


@login_required
def dispositivo_list(request):
    """Listado de inventario con filtros, búsqueda y ordenamiento HTMX."""
    from dashboard.filters import AnaliticaInventarioFilter

    query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'identificador_interno')
    order = request.GET.get('order', 'asc')

    # Subquery para obtener el estado de firma del acta más reciente
    ultima_acta_firmada = HistorialAsignacion.objects.filter(
        dispositivo=OuterRef('pk')
    ).order_by('-fecha_inicio').values('acta__firmada')[:1]

    dispositivos = Dispositivo.objects.select_related(
        'modelo__tipo_dispositivo', 'modelo__fabricante', 'estado',
        'propietario_actual', 'centro_costo'
    ).annotate(
        acta_firmada=Subquery(ultima_acta_firmada)
    )

    # Aplicar Filtros Avanzados (los mismos del Dashboard)
    filterset = AnaliticaInventarioFilter(request.GET, queryset=dispositivos)
    dispositivos = filterset.qs

    # Filtros por nombre para el Drill-down desde Chart.js
    tipo_nombre = request.GET.get('tipo_nombre')
    estado_nombre = request.GET.get('estado_nombre')
    cc_nombre = request.GET.get('cc_nombre')

    if tipo_nombre:
        dispositivos = dispositivos.filter(modelo__tipo_dispositivo__nombre=tipo_nombre)
    if estado_nombre:
        dispositivos = dispositivos.filter(estado__nombre=estado_nombre)
    if cc_nombre:
        if cc_nombre == 'Central/Stock':
            dispositivos = dispositivos.filter(centro_costo__isnull=True)
        else:
            dispositivos = dispositivos.filter(centro_costo__codigo_contable=cc_nombre)

    # Manejo de alertas desde la Home
    alerta = request.GET.get('alerta')
    if alerta == 'mantenimiento':
        dispositivos = dispositivos.filter(estado__nombre__icontains='Reparación')
    elif alerta == 'sin_acta':
        # Dispositivos que tienen una asignación actual sin acta
        dispositivos = dispositivos.filter(
            historial__isnull=False,
            historial__acta__isnull=True
        ).distinct()

    # Búsqueda textual adicional
    if query:
        dispositivos = dispositivos.filter(
            Q(identificador_interno__icontains=query) |
            Q(numero_serie__icontains=query) |
            Q(modelo__nombre__icontains=query) |
            Q(propietario_actual__first_name__icontains=query) |
            Q(propietario_actual__last_name__icontains=query)
        )

    # Ordenamiento
    sort_field = helpers.SORT_MAP.get(sort, 'identificador_interno')
    if order == 'desc':
        sort_field = f'-{sort_field}'
    dispositivos = dispositivos.order_by(sort_field)

    page_obj = paginate_queryset(request, dispositivos, per_page=20)
    context = {
        'page_obj': page_obj,
        'dispositivos': page_obj,
        'filter': filterset,
        'tipos': TipoDispositivo.objects.all(),
        'estados': EstadoDispositivo.objects.all(),
        'query': query,
        'current_sort': sort,
        'current_order': order,
    }

    if request.headers.get('HX-Request'):
        if request.GET.get('_modal') == 'true':
            # Renderizamos la lista en un panel side-over
            context['drilldown_title'] = (
                f"Equipos: {tipo_nombre or estado_nombre or cc_nombre or 'Listado'}"
            )
            return render(
                request,
                'dispositivos/partials/dispositivo_sideover_list.html',
                context
            )
        return render(
            request,
            'dispositivos/partials/dispositivo_list_table.html',
            context
        )

    return render(request, 'dispositivos/dispositivo_list.html', context)


@login_required
def dispositivo_detail(request, pk):
    """Vista detallada con carga Ajax de specs técnicos."""
    dispositivo = get_object_or_404(
        Dispositivo.objects.select_related(
            'modelo__tipo_dispositivo', 'modelo__fabricante',
            'estado', 'propietario_actual', 'centro_costo'
        ),
        pk=pk
    )

    if request.headers.get('HX-Request'):
        # Si es HTMX, devolvemos solo el sideover
        return render(
            request,
            'dispositivos/partials/dispositivo_detail_sideover.html',
            {'d': dispositivo}
        )

    return render(request, 'dispositivos/dispositivo_detail.html', {'d': dispositivo})


@login_required
@permission_required('dispositivos.change_dispositivo', raise_exception=True)
def dispositivo_update(request, pk):
    """Actualiza la información de un dispositivo."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    propietario_anterior = dispositivo.propietario_actual

    tech_forms = {
        key: FormClass(
            request.POST if request.method == 'POST' else None,
            instance=getattr(dispositivo, key, None)
            if hasattr(dispositivo, key) else None
        )
        for key, FormClass in helpers.TECH_FORMS.items()
    }

    if request.method == 'POST':
        form = DispositivoFactory.create_form_instance(
            request.POST, request.FILES, instance=dispositivo
        )
        if form.is_valid():
            dispositivo, acta = DispositivoService.registrar_dispositivo_con_acta(
                form, request.user, propietario_anterior=propietario_anterior
            )

            if acta:
                messages.success(
                    request,
                    f"Equipo actualizado y acta {acta.folio} generada correctamente."
                )
                return render(request, 'dispositivos/dispositivo_detail.html', {
                    'd': dispositivo,
                    'show_acta_modal': True,
                    'acta': acta,
                })

            messages.success(request, "Equipo actualizado correctamente.")
            return redirect('dispositivos:dispositivo_detail', pk=pk)
        else:
            return render(request, 'dispositivos/dispositivo_form.html', {
                'form': form,
                'tech_forms': tech_forms,
                'titulo': f'Editar {dispositivo.identificador_interno}'
            })
    else:
        form = DispositivoFactory.create_form_instance(instance=dispositivo)

    return render(request, 'dispositivos/dispositivo_form.html', {
        'form': form,
        'tech_forms': tech_forms,
        'titulo': f'Editar {dispositivo.identificador_interno}'
    })


@login_required
@permission_required('dispositivos.delete_dispositivo', raise_exception=True)
def dispositivo_delete(request, pk):
    """Elimina un dispositivo (confirmación vía modal)."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    if request.method in ['POST', 'DELETE']:
        try:
            dispositivo.delete()
            return htmx_redirect_or_redirect(
                request,
                redirect_url=reverse('dispositivos:dispositivo_list'),
            )
        except (ProtectedError, IntegrityError):
            error_msg = (
                "No se puede eliminar este equipo porque tiene un historial de "
                "asignaciones, actas o mantenimientos asociados."
            )
            if is_htmx(request):
                # Devolvemos 204 para no alterar el DOM y disparamos el toast de error
                return htmx_trigger_response(
                    trigger={'show-notification': {'message': error_msg, 'type': 'error'}},
                    status=204
                )

            messages.error(request, error_msg)
            return redirect('dispositivos:dispositivo_list')

    return render(
        request,
        'dispositivos/partials/dispositivo_confirm_delete.html',
        {'dispositivo': dispositivo}
    )
