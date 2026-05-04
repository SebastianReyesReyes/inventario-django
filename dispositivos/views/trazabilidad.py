from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required

from ..models import Dispositivo
from ..forms import AsignacionForm, ReasignacionForm, DevolucionForm
from ..services import TrazabilidadService
from core.htmx import htmx_render_or_redirect


@login_required
@permission_required('dispositivos.add_historialasignacion', raise_exception=True)
def dispositivo_asignar(request, pk):
    """Asigna un dispositivo que está actualmente Disponible."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    if request.method == 'POST':
        form = AsignacionForm(request.POST)
        if form.is_valid():
            creado_por = getattr(request.user, 'colaborador', None)
            movimiento, acta = TrazabilidadService.asignar(dispositivo, form, creado_por=creado_por)
            return htmx_render_or_redirect(
                request,
                'dispositivos/partials/trazabilidad_success.html',
                {'mensaje': 'Equipo asignado correctamente.', 'acta': acta},
                redirect_url=reverse('dispositivos:dispositivo_detail', kwargs={'pk': pk}),
                trigger='asignacion-saved',
            )
    else:
        form = AsignacionForm()

    return render(request, 'dispositivos/partials/asignacion_form_modal.html', {
        'form': form,
        'dispositivo': dispositivo
    })


@login_required
@permission_required('dispositivos.add_historialasignacion', raise_exception=True)
def dispositivo_reasignar(request, pk):
    """Reasigna un dispositivo de un colaborador a otro."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    ultimo_mov = dispositivo.historial.filter(fecha_fin__isnull=True).first()

    if request.method == 'POST':
        form = ReasignacionForm(request.POST)
        if form.is_valid():
            creado_por = getattr(request.user, 'colaborador', None)
            nuevo_mov, acta = TrazabilidadService.reasignar(dispositivo, form, creado_por=creado_por)
            return htmx_render_or_redirect(
                request,
                'dispositivos/partials/trazabilidad_success.html',
                {'mensaje': 'Equipo reasignado correctamente.', 'acta': acta},
                redirect_url=reverse('dispositivos:dispositivo_detail', kwargs={'pk': pk}),
                trigger='asignacion-saved',
            )
    else:
        form = ReasignacionForm()

    return render(request, 'dispositivos/partials/reasignacion_form_modal.html', {
        'form': form,
        'dispositivo': dispositivo,
        'anterior': ultimo_mov.colaborador if ultimo_mov else None
    })


@login_required
@permission_required('dispositivos.add_historialasignacion', raise_exception=True)
def dispositivo_devolver(request, pk):
    """Registra la devolución de un equipo a bodega."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    ultimo_mov = dispositivo.historial.filter(fecha_fin__isnull=True).first()

    if request.method == 'POST':
        form = DevolucionForm(request.POST)
        if form.is_valid():
            creado_por = getattr(request.user, 'colaborador', None)
            ultimo_mov, acta = TrazabilidadService.devolver(dispositivo, form, creado_por=creado_por)
            return htmx_render_or_redirect(
                request,
                'dispositivos/partials/trazabilidad_success.html',
                {'mensaje': 'Devolución registrada correctamente.', 'acta': acta},
                redirect_url=reverse('dispositivos:dispositivo_detail', kwargs={'pk': pk}),
                trigger='asignacion-saved',
            )
    else:
        form = DevolucionForm()

    return render(request, 'dispositivos/partials/devolucion_form_modal.html', {
        'form': form,
        'dispositivo': dispositivo,
        'colaborador': ultimo_mov.colaborador if ultimo_mov else None
    })


@login_required
def dispositivo_historial(request, pk):
    """Carga el timeline del historial de movimientos (Lazy load)."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    historial = dispositivo.historial.select_related('colaborador').all().order_by('-fecha_inicio')
    return render(request, 'dispositivos/partials/historial_timeline.html', {
        'historial': historial
    })
