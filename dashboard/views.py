from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from dispositivos.models import Dispositivo
from .filters import AnaliticaInventarioFilter
from dispositivos.resources import DispositivoResource
from .services import DashboardMetricsService

@login_required
@permission_required('dispositivos.view_dispositivo', raise_exception=True)
def dashboard_principal(request):
    """
    Vista principal del Centro de Mando (Dashboard).
    Calcula métricas y datos para gráficos basados en filtros avanzados.
    """
    # Inicializar el filtro avanzado
    queryset = Dispositivo.objects.select_related('modelo__tipo_dispositivo', 'estado', 'centro_costo', 'modelo__fabricante').all()
    filterset = AnaliticaInventarioFilter(request.GET, queryset=queryset)
    filtered_qs = filterset.qs

    top10_metric = request.GET.get('top10_metric', 'cantidad')
    context = DashboardMetricsService.build_context(
        filtered_qs=filtered_qs,
        filterset=filterset,
        top10_metric=top10_metric,
    )

    if request.headers.get('HX-Request'):
        return render(request, 'dashboard/partials/dashboard_content.html', context)

    return render(request, 'dashboard/index.html', context)


@login_required
@permission_required('dispositivos.view_dispositivo', raise_exception=True)
def exportar_dispositivos_excel(request):
    """
    Exporta el listado actual de dispositivos (respetando filtros) a formato Excel.
    """
    queryset = Dispositivo.objects.all()
    filterset = AnaliticaInventarioFilter(request.GET, queryset=queryset)
    
    dataset = DispositivoResource().export(filterset.qs)
    # Usamos .export('xlsx') para mayor compatibilidad con tablib
    response = HttpResponse(dataset.export('xlsx'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Inventario_JMIE_{timezone.now().date()}.xlsx"'
    return response


@login_required
def reportes_lista(request):
    """
    Vista de la central de reportes (página maestra).
    """
    return render(request, 'dashboard/reportes.html')

