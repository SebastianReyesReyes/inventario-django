from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError

from core.models import Modelo, Fabricante, TipoDispositivo
from ..forms import NotebookTechForm, SmartphoneTechForm, MonitorTechForm


def ajax_get_modelos(request):
    """Retorna opciones de modelos filtrados por fabricante y tipo para el formulario."""
    fabricante_id = request.GET.get('fabricante')
    tipo_id = request.GET.get('tipo')

    modelos = Modelo.objects.all()

    if fabricante_id:
        modelos = modelos.filter(fabricante_id=fabricante_id)
    if tipo_id:
        modelos = modelos.filter(tipo_dispositivo_id=tipo_id)

    if not fabricante_id and not tipo_id:
        modelos = Modelo.objects.none()
    else:
        modelos = modelos.order_by('nombre')

    return render(request, 'dispositivos/partials/modelo_options.html', {'modelos': modelos})


@login_required
@permission_required('dispositivos.add_dispositivo', raise_exception=True)
def ajax_crear_modelo(request):
    """Crea un modelo nuevo para un fabricante y tipo desde el formulario de dispositivos."""
    fabricante_id = request.POST.get('fabricante')
    tipo_id = request.POST.get('tipo')
    nombre = request.POST.get('nuevo_modelo_nombre', '').strip()

    modelos = Modelo.objects.all()
    if fabricante_id:
        modelos = modelos.filter(fabricante_id=fabricante_id)
    if tipo_id:
        modelos = modelos.filter(tipo_dispositivo_id=tipo_id)

    if not fabricante_id or not tipo_id or not nombre:
        return render(request, 'dispositivos/partials/modelo_options.html', {'modelos': modelos.order_by('nombre') if (fabricante_id or tipo_id) else Modelo.objects.none()})

    fabricante = get_object_or_404(Fabricante, pk=fabricante_id)
    tipo_dispositivo = get_object_or_404(TipoDispositivo, pk=tipo_id)

    # Normalización: evitar duplicados por diferencia de mayúsculas
    modelo = Modelo.objects.filter(fabricante=fabricante, tipo_dispositivo=tipo_dispositivo, nombre__iexact=nombre).first()

    if not modelo:
        try:
            modelo = Modelo.objects.create(nombre=nombre, fabricante=fabricante, tipo_dispositivo=tipo_dispositivo)
        except IntegrityError:
            modelo = Modelo.objects.get(fabricante=fabricante, tipo_dispositivo=tipo_dispositivo, nombre__iexact=nombre)

    modelos = Modelo.objects.filter(fabricante=fabricante, tipo_dispositivo=tipo_dispositivo).order_by('nombre')
    return render(request, 'dispositivos/partials/modelo_options.html', {
        'modelos': modelos,
        'selected_modelo_id': modelo.id
    })


@login_required
def ajax_get_tech_fields(request):
    """Retorna los campos técnicos específicos según el tipo de dispositivo."""
    tipo_id = request.GET.get('tipo')
    if not tipo_id:
        return HttpResponse("")

    tipo = get_object_or_404(TipoDispositivo, pk=tipo_id)
    nombre = tipo.nombre.lower()
    form = None

    if 'notebook' in nombre or 'laptop' in nombre:
        form = NotebookTechForm()
    elif 'smartphone' in nombre or 'celular' in nombre:
        form = SmartphoneTechForm()
    elif 'monitor' in nombre:
        form = MonitorTechForm()

    if form:
        return render(request, 'dispositivos/partials/tipo_especifico_fields.html', {'form': form})
    return HttpResponse("")
