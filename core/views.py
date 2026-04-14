from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
import json

from .models import Fabricante, TipoDispositivo, Modelo, CentroCosto, EstadoDispositivo
from .forms import FabricanteForm, TipoDispositivoForm, ModeloForm, CentroCostoForm, EstadoDispositivoForm
from dispositivos.models import Dispositivo

@login_required
def home(request):
    from colaboradores.models import Colaborador
    from dispositivos.models import BitacoraMantenimiento
    from django.utils import timezone
    from datetime import timedelta
    
    # Métricas principales por estado (incluyendo sinónimos encontrados en la BD)
    total_disponibles = Dispositivo.objects.filter(estado__nombre__in=['Disponible', 'Reservado']).count()
    total_asignados = Dispositivo.objects.filter(estado__nombre__in=['Asignado', 'En uso']).count()
    total_mantenimiento = Dispositivo.objects.filter(estado__nombre__icontains='Reparación').count()
    total_baja = Dispositivo.objects.filter(estado__nombre__in=['Fuera de Inventario', 'De Baja', 'Inactivo']).count()

    
    total_dispositivos = Dispositivo.objects.count()
    total_activos = total_dispositivos - total_baja  # Activos = todo menos baja
    porcentaje_asignados = round((total_asignados / total_activos * 100) if total_activos > 0 else 0)
    
    # Métricas complementarias
    total_colaboradores = Colaborador.objects.filter(esta_activo=True).count()
    mantenimientos_recientes = BitacoraMantenimiento.objects.filter(
        fecha__gte=timezone.now() - timedelta(days=30)
    ).count()

    context = {
        'total_disponibles': total_disponibles,
        'total_asignados': total_asignados,
        'total_mantenimiento': total_mantenimiento,
        'total_baja': total_baja,
        'total_dispositivos': total_dispositivos,
        'total_colaboradores': total_colaboradores,
        'porcentaje_asignados': porcentaje_asignados,
        'mantenimientos_recientes': mantenimientos_recientes,
    }
    return render(request, 'core/home.html', context)


# --- FABRICANTES ---

@login_required
def fabricante_list(request):
    fabricantes = Fabricante.objects.prefetch_related('modelos').all().order_by('nombre')
    return render(request, 'core/fabricante_list.html', {'fabricantes': fabricantes})

@login_required
@permission_required('core.add_fabricante', raise_exception=True)
def fabricante_create(request):
    if request.method == 'POST':
        form = FabricanteForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"fabricanteListChanged": True, "showNotification": "Fabricante creado con éxito"})})
            return redirect('core:fabricante_list')
    else:
        form = FabricanteForm()

    template = 'core/partials/fabricante_form.html'
    return render(request, template, {'form': form})

@login_required
@permission_required('core.change_fabricante', raise_exception=True)
def fabricante_edit(request, pk):
    fabricante = get_object_or_404(Fabricante, pk=pk)
    if request.method == 'POST':
        form = FabricanteForm(request.POST, instance=fabricante)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"fabricanteListChanged": True, "showNotification": "Fabricante actualizado"})})
            return redirect('core:fabricante_list')
    else:
        form = FabricanteForm(instance=fabricante)

    return render(request, 'core/partials/fabricante_form.html', {'form': form, 'fabricante': fabricante})

@login_required
@permission_required('core.delete_fabricante', raise_exception=True)
def fabricante_delete(request, pk):
    fabricante = get_object_or_404(Fabricante, pk=pk)
    if fabricante.modelos.exists():
        return HttpResponse("No se puede eliminar: tiene modelos asociados", status=400)
    
    fabricante.delete()
    return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"fabricanteListChanged": True, "showNotification": "Fabricante eliminado"})})

# --- MODELOS ---

@login_required
def modelo_list(request):
    fabricante_id = request.GET.get('fabricante_id')
    modelos = Modelo.objects.select_related('fabricante').all().order_by('fabricante__nombre', 'nombre')
    
    if fabricante_id:
        modelos = modelos.filter(fabricante_id=fabricante_id)
        
    fabricantes = Fabricante.objects.all().order_by('nombre')
    return render(request, 'core/modelo_list.html', {
        'modelos': modelos, 
        'fabricantes': fabricantes,
        'selected_fabricante': int(fabricante_id) if fabricante_id else None
    })

@login_required
@permission_required('core.add_modelo', raise_exception=True)
def modelo_create(request):
    initial = {}
    if request.GET.get('fabricante_id'):
        initial['fabricante'] = request.GET.get('fabricante_id')
        
    if request.method == 'POST':
        form = ModeloForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"modeloListChanged": True, "fabricanteListChanged": True, "showNotification": "Modelo creado"})})
            return redirect('core:modelo_list')
    else:
        form = ModeloForm(initial=initial)

    return render(request, 'core/partials/modelo_form.html', {'form': form})

@login_required
@permission_required('core.change_modelo', raise_exception=True)
def modelo_edit(request, pk):
    modelo = get_object_or_404(Modelo, pk=pk)
    if request.method == 'POST':
        form = ModeloForm(request.POST, instance=modelo)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"modeloListChanged": True, "fabricanteListChanged": True, "showNotification": "Modelo actualizado"})})
            return redirect('core:modelo_list')
    else:
        form = ModeloForm(instance=modelo)

    return render(request, 'core/partials/modelo_form.html', {'form': form, 'modelo': modelo})

@login_required
@permission_required('core.delete_modelo', raise_exception=True)
def modelo_delete(request, pk):
    modelo = get_object_or_404(Modelo, pk=pk)
    if Dispositivo.objects.filter(modelo=modelo).exists():
        return HttpResponse("Protegido: Existen dispositivos de este modelo", status=400)
    
    modelo.delete()
    return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"modeloListChanged": True, "fabricanteListChanged": True, "showNotification": "Modelo eliminado"})})

# --- TIPOS DE DISPOSITIVO ---

@login_required
def tipo_list(request):
    tipos = TipoDispositivo.objects.all().order_by('nombre')
    return render(request, 'core/tipo_list.html', {'tipos': tipos})

@login_required
@permission_required('core.add_tipodispositivo', raise_exception=True)
def tipo_create(request):
    if request.method == 'POST':
        form = TipoDispositivoForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"tipoListChanged": True, "showNotification": "Tipo de dispositivo creado"})})
            return redirect('core:tipo_list')
    else:
        form = TipoDispositivoForm()

    return render(request, 'core/partials/tipo_form.html', {'form': form})

@login_required
@permission_required('core.change_tipodispositivo', raise_exception=True)
def tipo_edit(request, pk):
    tipo = get_object_or_404(TipoDispositivo, pk=pk)
    if request.method == 'POST':
        form = TipoDispositivoForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"tipoListChanged": True, "showNotification": "Tipo de dispositivo actualizado"})})
            return redirect('core:tipo_list')
    else:
        form = TipoDispositivoForm(instance=tipo)

    return render(request, 'core/partials/tipo_form.html', {'form': form, 'tipo': tipo})

@login_required
@permission_required('core.delete_tipodispositivo', raise_exception=True)
def tipo_delete(request, pk):
    tipo = get_object_or_404(TipoDispositivo, pk=pk)
    # Verificar si hay dispositivos asociados
    if Dispositivo.objects.filter(tipo=tipo).exists():
        return HttpResponse("Protegido: Existen dispositivos de este tipo", status=400)
    
    tipo.delete()
    return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"tipoListChanged": True, "showNotification": "Tipo de dispositivo eliminado"})})

# --- CENTROS DE COSTO ---

@login_required
def cc_list(request):
    ccs = CentroCosto.objects.all().order_by('-activa', 'nombre')
    return render(request, 'core/cc_list.html', {'ccs': ccs})

@login_required
@permission_required('core.add_centrocosto', raise_exception=True)
def cc_create(request):
    if request.method == 'POST':
        form = CentroCostoForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"ccListChanged": True, "showNotification": "Centro de costo creado"})})
            return redirect('core:cc_list')
    else:
        form = CentroCostoForm()

    return render(request, 'core/partials/cc_form.html', {'form': form})

@login_required
@permission_required('core.change_centrocosto', raise_exception=True)
def cc_edit(request, pk):
    cc = get_object_or_404(CentroCosto, pk=pk)
    if request.method == 'POST':
        form = CentroCostoForm(request.POST, instance=cc)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"ccListChanged": True, "showNotification": "Centro de costo actualizado"})})
            return redirect('core:cc_list')
    else:
        form = CentroCostoForm(instance=cc)

    return render(request, 'core/partials/cc_form.html', {'form': form, 'cc': cc})

@login_required
@permission_required('core.change_centrocosto', raise_exception=True)
def cc_toggle_activa(request, pk):
    cc = get_object_or_404(CentroCosto, pk=pk)
    cc.activa = not cc.activa
    cc.save()
    
    # Retornar partial del badge o toda la fila? Por ahora, disparamos recarga de lista para simplicidad
    return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"ccListChanged": True, "showNotification": f"Centro de costo {'activado' if cc.activa else 'desactivado'}"})})

# --- ESTADOS DE DISPOSITIVO ---

@login_required
def estado_list(request):
    estados = EstadoDispositivo.objects.all().order_by('nombre')
    return render(request, 'core/estado_list.html', {'estados': estados})

@login_required
@permission_required('core.add_estadodispositivo', raise_exception=True)
def estado_create(request):
    if request.method == 'POST':
        form = EstadoDispositivoForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"estadoListChanged": True, "showNotification": "Estado creado"})})
            return redirect('core:estado_list')
    else:
        form = EstadoDispositivoForm()

    return render(request, 'core/partials/estado_form.html', {'form': form})

@login_required
@permission_required('core.change_estadodispositivo', raise_exception=True)
def estado_edit(request, pk):
    estado = get_object_or_404(EstadoDispositivo, pk=pk)
    if request.method == 'POST':
        form = EstadoDispositivoForm(request.POST, instance=estado)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"estadoListChanged": True, "showNotification": "Estado actualizado"})})
            return redirect('core:estado_list')
    else:
        form = EstadoDispositivoForm(instance=estado)

    return render(request, 'core/partials/estado_form.html', {'form': form, 'estado': estado})

@login_required
@permission_required('core.delete_estadodispositivo', raise_exception=True)
def estado_delete(request, pk):
    estado = get_object_or_404(EstadoDispositivo, pk=pk)
    if Dispositivo.objects.filter(estado=estado).exists():
        return HttpResponse("Protegido: Existen dispositivos en este estado", status=400)
    
    estado.delete()
    return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"estadoListChanged": True, "showNotification": "Estado eliminado"})})

def error_403(request, exception=None):
    """
    Vista para manejar errores 403 (Acceso Denegado).
    """
    return render(request, '403.html', status=403)

def error_404(request, exception=None):
    """
    Vista para manejar errores 404 (Página no encontrada).
    """
    return render(request, '404.html', status=404)
