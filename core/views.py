import json

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required


from .models import Fabricante, TipoDispositivo, Modelo, CentroCosto, EstadoDispositivo, Departamento
from .filters import DashboardFilterSet
from dispositivos.models import Dispositivo, BitacoraMantenimiento, HistorialAsignacion
from .htmx import htmx_trigger_response
from core.pagination import paginate_queryset
from .catalog_views import (
    CentroCostoCreateView,
    CentroCostoUpdateView,
    DepartamentoCreateView,
    DepartamentoDeleteView,
    DepartamentoUpdateView,
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
    page_obj = paginate_queryset(request, fabricantes, per_page=10)
    return render(request, 'core/fabricante_list.html', {'page_obj': page_obj, 'fabricantes': page_obj})


@login_required
def ajax_fabricante_options(request):
    """HTMX: retorna opciones <option> para refrescar el select de fabricante."""
    fabricantes = Fabricante.objects.all().order_by('nombre')
    selected = request.GET.get('selected', '')
    return render(request, 'core/partials/fabricante_options.html', {
        'fabricantes': fabricantes,
        'selected': selected,
    })

fabricante_create = FabricanteCreateView.as_view()
fabricante_edit = FabricanteUpdateView.as_view()
fabricante_delete = FabricanteDeleteView.as_view()


@login_required
@permission_required('core.add_modelo', raise_exception=True)
@login_required
@permission_required('core.add_modelo', raise_exception=True)
def ajax_modelo_create_inline(request, pk):
    """Compatibilidad: redirige al modal estándar de creación de modelo."""
    response = HttpResponse(status=204)
    response['HX-Redirect'] = f"/catalogos/modelos/crear/?fabricante_id={pk}"
    return response


@login_required
@permission_required('core.change_modelo', raise_exception=True)
def ajax_modelo_update_inline(request, pk):
    """Actualiza el nombre de un modelo desde el inline de fabricantes."""
    modelo = get_object_or_404(Modelo, pk=pk)
    nombre = request.POST.get('nombre', '').strip()
    if nombre:
        modelo.nombre = nombre
        modelo.save()
    return render(request, 'core/partials/fabricante_modelos_inline.html', {'fabricante': modelo.fabricante})


@login_required
@permission_required('core.delete_modelo', raise_exception=True)
def ajax_modelo_delete_inline(request, pk):
    """Elimina un modelo desde el inline de fabricantes."""
    modelo = get_object_or_404(Modelo, pk=pk)
    fabricante = modelo.fabricante
    if Dispositivo.objects.filter(modelo=modelo).exists():
        return htmx_trigger_response({"showNotification": {"message": "Protegido: Existen dispositivos de este modelo", "type": "error"}})
    modelo.delete()
    response = render(request, 'core/partials/fabricante_modelos_inline.html', {'fabricante': fabricante})
    response["HX-Trigger"] = json.dumps({"showNotification": {"message": f"Modelo '{modelo.nombre}' eliminado", "type": "success"}})
    return response

# --- MODELOS ---

@login_required
def modelo_list(request):
    fabricante_id = request.GET.get('fabricante_id')
    modelos = Modelo.objects.select_related('fabricante').all().order_by('fabricante__nombre', 'nombre')
    if fabricante_id:
        modelos = modelos.filter(fabricante_id=fabricante_id)
    page_obj = paginate_queryset(request, modelos, per_page=10)
    fabricantes = Fabricante.objects.all().order_by('nombre')
    return render(request, 'core/modelo_list.html', {
        'page_obj': page_obj,
        'modelos': page_obj,
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
    page_obj = paginate_queryset(request, tipos, per_page=10)
    return render(request, 'core/tipo_list.html', {'page_obj': page_obj, 'tipos': page_obj})

tipo_create = TipoCreateView.as_view()
tipo_edit = TipoUpdateView.as_view()
tipo_delete = TipoDeleteView.as_view()

# --- CENTROS DE COSTO ---

@login_required
def cc_list(request):
    ccs = CentroCosto.objects.all().order_by('-activa', 'nombre')
    page_obj = paginate_queryset(request, ccs, per_page=10)
    return render(request, 'core/cc_list.html', {'page_obj': page_obj, 'ccs': page_obj})

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
    page_obj = paginate_queryset(request, estados, per_page=10)
    return render(request, 'core/estado_list.html', {'page_obj': page_obj, 'estados': page_obj})

estado_create = EstadoCreateView.as_view()
estado_edit = EstadoUpdateView.as_view()
estado_delete = EstadoDeleteView.as_view()

# --- DEPARTAMENTOS ---

@login_required
def departamento_list(request):
    departamentos = Departamento.objects.all().order_by('nombre')
    page_obj = paginate_queryset(request, departamentos, per_page=10)
    return render(request, 'core/departamento_list.html', {'page_obj': page_obj, 'departamentos': page_obj})

departamento_create = DepartamentoCreateView.as_view()
departamento_edit = DepartamentoUpdateView.as_view()
departamento_delete = DepartamentoDeleteView.as_view()

@login_required
def catalogo_import_modal(request):
    """Modal para importar catálogos desde CSV."""
    return render(request, 'core/partials/catalogo_import_modal.html')


@login_required
@permission_required('core.add_fabricante', raise_exception=True)
def catalogo_import_process(request):
    """Procesa el archivo CSV subido desde la UI."""
    if request.method != 'POST':
        return HttpResponse("Método no permitido", status=405)

    archivo = request.FILES.get('archivo_csv')
    if not archivo:
        return render(request, 'core/partials/catalogo_import_result.html', {
            'error': 'No se seleccionó ningún archivo.',
        })

    if not archivo.name.lower().endswith('.csv'):
        return render(request, 'core/partials/catalogo_import_result.html', {
            'error': 'El archivo debe tener extensión .csv',
        })

    try:
        from core.services import importar_catalogos_desde_csv
        resultado = importar_catalogos_desde_csv(archivo)
    except Exception as e:
        return render(request, 'core/partials/catalogo_import_result.html', {
            'error': f'Error al procesar el archivo: {e}',
        })

    return render(request, 'core/partials/catalogo_import_result.html', {
        'resultado': resultado,
    })


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
