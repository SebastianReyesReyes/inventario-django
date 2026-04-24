from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError

from .models import Fabricante, TipoDispositivo, Modelo, CentroCosto, EstadoDispositivo
from .filters import DashboardFilterSet
from dispositivos.models import Dispositivo, BitacoraMantenimiento, HistorialAsignacion
from .htmx import htmx_trigger_response
from .catalog_views import (
    CentroCostoCreateView,
    CentroCostoUpdateView,
    EstadoCreateView,
    EstadoDeleteView,
    EstadoUpdateView,
    FabricanteCreateView,
    FabricanteDeleteView,
    FabricanteUpdateView,
    ModeloCreateView,
    ModeloDeleteView,
    ModeloUpdateView,
    TipoCreateView,
    TipoDeleteView,
    TipoUpdateView,
)

@login_required
def home(request):
    """
    Landing Page Operativa.
    Punto de entrada rápido con alertas y accesos directos.
    """
    # Alertas rápidas (Queries ligeros)
    mantenimientos_pendientes = BitacoraMantenimiento.objects.filter(reparacion_realizada__isnull=True).count()
    asignaciones_sin_acta = HistorialAsignacion.objects.filter(acta__isnull=True).count()
    
    context = {
        'mantenimientos_pendientes': mantenimientos_pendientes,
        'asignaciones_sin_acta': asignaciones_sin_acta,
        'total_dispositivos': Dispositivo.objects.count(),
    }

    return render(request, 'core/home.html', context)

@login_required
def dashboard_drill_down(request):
    """View to return a detailed list of devices based on filters for a side-over."""
    from django.db.models import Q
    
    filter_type = request.GET.get('filter_type')
    filterset = DashboardFilterSet(request.GET, queryset=Dispositivo.objects.all())
    qs = filterset.qs
    
    title = "Detalle de Activos"
    
    if filter_type == 'disponibles':
        qs = qs.filter(estado__nombre__in=['Disponible', 'Reservado'])
        title = "Equipos Disponibles"
    elif filter_type == 'asignados':
        qs = qs.filter(estado__nombre__in=['Asignado', 'En uso'])
        title = "Equipos Asignados"
    elif filter_type == 'mantenimiento':
        qs = qs.filter(estado__nombre__icontains='Reparación')
        title = "Equipos en Mantención"
    elif filter_type == 'baja':
        qs = qs.filter(estado__nombre__in=['Fuera de Inventario', 'De Baja', 'Inactivo'])
        title = "Equipos Fuera de Inventario"
    
    context = {
        'dispositivos': qs[:100],  # Limit to 100 for performance
        'title': title,
        'results_count': qs.count()
    }
    return render(request, 'core/partials/dashboard_drill_down.html', context)


# --- FABRICANTES ---

@login_required
def fabricante_list(request):
    fabricantes = Fabricante.objects.prefetch_related('modelos').all().order_by('nombre')
    return render(request, 'core/fabricante_list.html', {'fabricantes': fabricantes})

fabricante_create = FabricanteCreateView.as_view()
fabricante_edit = FabricanteUpdateView.as_view()
fabricante_delete = FabricanteDeleteView.as_view()


@login_required
@permission_required('dispositivos.add_dispositivo', raise_exception=True)
def ajax_modelo_create_inline(request, pk):
    """Crea un modelo nuevo asociado a un fabricante desde la lista de fabricantes."""
    fabricante = get_object_or_404(Fabricante, pk=pk)
    nombre = request.POST.get('nuevo_modelo_nombre', '').strip()

    if nombre:
        modelo = Modelo.objects.filter(fabricante=fabricante, nombre__iexact=nombre).first()
        if not modelo:
            try:
                Modelo.objects.create(nombre=nombre, fabricante=fabricante)
            except IntegrityError:
                pass

    return render(request, 'core/partials/fabricante_modelos_inline.html', {'fabricante': fabricante})

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

modelo_create = ModeloCreateView.as_view()
modelo_edit = ModeloUpdateView.as_view()
modelo_delete = ModeloDeleteView.as_view()

# --- TIPOS DE DISPOSITIVO ---

@login_required
def tipo_list(request):
    tipos = TipoDispositivo.objects.all().order_by('nombre')
    return render(request, 'core/tipo_list.html', {'tipos': tipos})

tipo_create = TipoCreateView.as_view()
tipo_edit = TipoUpdateView.as_view()
tipo_delete = TipoDeleteView.as_view()

# --- CENTROS DE COSTO ---

@login_required
def cc_list(request):
    ccs = CentroCosto.objects.all().order_by('-activa', 'nombre')
    return render(request, 'core/cc_list.html', {'ccs': ccs})

cc_create = CentroCostoCreateView.as_view()
cc_edit = CentroCostoUpdateView.as_view()

@login_required
@permission_required('core.change_centrocosto', raise_exception=True)
def cc_toggle_activa(request, pk):
    cc = get_object_or_404(CentroCosto, pk=pk)
    cc.activa = not cc.activa
    cc.save()
    
    # Retornar partial del badge o toda la fila? Por ahora, disparamos recarga de lista para simplicidad
    return htmx_trigger_response({"ccListChanged": True, "showNotification": f"Centro de costo {'activado' if cc.activa else 'desactivado'}"})

# --- ESTADOS DE DISPOSITIVO ---

@login_required
def estado_list(request):
    estados = EstadoDispositivo.objects.all().order_by('nombre')
    return render(request, 'core/estado_list.html', {'estados': estados})

estado_create = EstadoCreateView.as_view()
estado_edit = EstadoUpdateView.as_view()
estado_delete = EstadoDeleteView.as_view()

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

def error_500(request):
    """
    Vista para manejar errores 500 (Error de Servidor).
    """
    return render(request, '500.html', status=500)
