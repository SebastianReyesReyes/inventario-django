from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from dispositivos.models import Dispositivo, BitacoraMantenimiento
from colaboradores.models import Colaborador
from core.models import EstadoDispositivo, TipoDispositivo
from .filters import AnaliticaInventarioFilter
from dispositivos.resources import DispositivoResource

@login_required
@permission_required('dispositivos.view_dispositivo', raise_exception=True)
def dashboard_principal(request):
    """
    Vista principal del Centro de Mando (Dashboard).
    Calcula métricas y datos para gráficos basados en filtros avanzados.
    """
    # Inicializar el Filtro avanzado
    queryset = Dispositivo.objects.select_related('tipo', 'estado', 'centro_costo', 'modelo__fabricante').all()
    filterset = AnaliticaInventarioFilter(request.GET, queryset=queryset)
    filtered_qs = filterset.qs
    
    # --- MÉTRICAS PRINCIPALES (BASADAS EN FILTRO) ---
    total_dispositivos = filtered_qs.count()
    
    # Definición de estados (agrupación lógica)
    disponible_estado = EstadoDispositivo.objects.filter(nombre__in=['Disponible', 'Reservado']).first()
    mantenimiento_estado = EstadoDispositivo.objects.filter(nombre__icontains='Reparación').first()
    
    tipo_notebook = TipoDispositivo.objects.filter(nombre__icontains='Notebook').first()
    tipo_smartphone = TipoDispositivo.objects.filter(nombre__icontains='Smartphone').first()

    total_disponibles = filtered_qs.filter(estado__nombre__in=['Disponible', 'Reservado']).count()
    total_asignados = filtered_qs.filter(estado__nombre__in=['Asignado', 'En uso']).count()
    total_mantenimiento = filtered_qs.filter(estado__nombre__icontains='Reparación').count()
    total_baja = filtered_qs.filter(estado__nombre__in=['Fuera de Inventario', 'De Baja', 'Inactivo']).count()
    
    # Métricas financieras
    total_valor = filtered_qs.aggregate(total=Sum('valor_contable'))['total'] or 0
    costo_mantenimiento = BitacoraMantenimiento.objects.filter(dispositivo__in=filtered_qs).aggregate(total=Sum('costo_reparacion'))['total'] or 0
    
    # Métricas calculadas
    total_activos = total_dispositivos - total_baja
    porcentaje_asignados = round((total_asignados / total_activos * 100) if total_activos > 0 else 0)

    # Métricas específicas (Drill-Down sugerido por usuario)
    total_notebooks_disponibles = filtered_qs.filter(
        tipo__nombre__icontains='Notebook', 
        estado__nombre__in=['Disponible', 'Reservado']
    ).count()
    total_smartphones_disponibles = filtered_qs.filter(
        tipo__nombre__icontains='Smartphone', 
        estado__nombre__in=['Disponible', 'Reservado']
    ).count()
    
    # Colaboradores activos
    total_colaboradores = Colaborador.objects.filter(esta_activo=True).count()
    
    # Mantenciones recientes
    mantenimientos_recientes = BitacoraMantenimiento.objects.filter(
        dispositivo__in=filtered_qs,
        fecha__gte=timezone.now() - timedelta(days=30)
    ).count()

    # --- DATOS PARA GRÁFICOS (CHART.JS) ---
    # 1. Distribución por Categoría (Tipo)
    chart_tipo_data = list(filtered_qs.values('tipo__nombre').annotate(total=Count('id')).order_by('-total'))
    
    # 2. Distribución por Estados Operativos
    chart_estado_data = list(filtered_qs.values('estado__nombre').annotate(total=Count('id')).order_by('-total'))
    
    # 3. Distribución por Centro de Costo (Obra)
    chart_cc_data = list(filtered_qs.values('centro_costo__codigo_contable').annotate(total=Count('id')).order_by('-total')[:10])

    # 4. Tendencia de Adquisiciones (por Año)
    chart_adquisiciones_data = list(filtered_qs.filter(fecha_compra__isnull=False).values('fecha_compra__year').annotate(total=Count('id')).order_by('fecha_compra__year'))

    import json
    context = {
        'filter': filterset,
        'total_disponibles': total_disponibles,
        'total_disponibles_id': disponible_estado.id if disponible_estado else '',
        'total_asignados': total_asignados,
        'total_mantenimiento': total_mantenimiento,
        'total_mantenimiento_id': mantenimiento_estado.id if mantenimiento_estado else '',
        'total_baja': total_baja,
        'total_dispositivos': total_dispositivos,
        'total_colaboradores': total_colaboradores,
        'porcentaje_asignados': porcentaje_asignados,
        'mantenimientos_recientes': mantenimientos_recientes,
        'total_valor': total_valor,
        'costo_mantenimiento': costo_mantenimiento,
        'total_notebooks_disponibles': total_notebooks_disponibles,
        'total_smartphones_disponibles': total_smartphones_disponibles,
        'tipo_notebook_id': tipo_notebook.id if tipo_notebook else '',
        'tipo_smartphone_id': tipo_smartphone_id if 'tipo_smartphone_id' in locals() else (tipo_smartphone.id if tipo_smartphone else ''),
        
        # Datos para Charts (Serializados a JSON)
        'chart_tipo_labels': json.dumps([item['tipo__nombre'] or 'Sin Categoría' for item in chart_tipo_data]),
        'chart_tipo_values': json.dumps([item['total'] for item in chart_tipo_data]),
        
        'chart_estado_labels': json.dumps([item['estado__nombre'] or 'Estado Desconocido' for item in chart_estado_data]),
        'chart_estado_values': json.dumps([item['total'] for item in chart_estado_data]),
        
        'chart_cc_labels': json.dumps([item['centro_costo__codigo_contable'] or 'Central/Stock' for item in chart_cc_data]),
        'chart_cc_values': json.dumps([item['total'] for item in chart_cc_data]),

        'chart_adq_labels': json.dumps([item['fecha_compra__year'] for item in chart_adquisiciones_data]),
        'chart_adq_values': json.dumps([item['total'] for item in chart_adquisiciones_data]),
    }

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

