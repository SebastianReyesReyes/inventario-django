from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction

from core.models import EstadoDispositivo
from ..models import Dispositivo, BitacoraMantenimiento
from ..forms import MantenimientoForm


@login_required
@permission_required('dispositivos.add_bitacoramantenimiento', raise_exception=True)
@transaction.atomic
def mantenimiento_create(request, pk):
    """Registra una entrada de mantenimiento."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    if request.method == 'POST':
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            mantenimiento = form.save(commit=False)
            mantenimiento.dispositivo = dispositivo
            mantenimiento.save()

            # Si se marcó cambio automático y el equipo estaba en reparación
            if mantenimiento.cambio_estado_automatico:
                estado_disponible, _ = EstadoDispositivo.objects.get_or_create(nombre='Disponible')
                dispositivo.estado = estado_disponible
                dispositivo.save()

            return render(request, 'dispositivos/partials/mantenimiento_success.html')
    else:
        form = MantenimientoForm()

    return render(request, 'dispositivos/partials/mantenimiento_form_modal.html', {
        'form': form,
        'dispositivo': dispositivo
    })


@login_required
@permission_required('dispositivos.change_bitacoramantenimiento', raise_exception=True)
def mantenimiento_update(request, pk):
    """Actualiza un registro de mantenimiento."""
    mantenimiento = get_object_or_404(BitacoraMantenimiento, pk=pk)
    if request.method == 'POST':
        form = MantenimientoForm(request.POST, instance=mantenimiento)
        if form.is_valid():
            form.save()
            return render(request, 'dispositivos/partials/mantenimiento_success.html')
    else:
        form = MantenimientoForm(instance=mantenimiento)

    return render(request, 'dispositivos/partials/mantenimiento_form_modal.html', {
        'form': form,
        'dispositivo': mantenimiento.dispositivo,
        'edit_mode': True
    })
