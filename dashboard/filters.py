import django_filters
from django import forms
from core.models import Fabricante, TipoDispositivo, CentroCosto, EstadoDispositivo
from dispositivos.models import Dispositivo

class AnaliticaInventarioFilter(django_filters.FilterSet):
    """
    Filtro avanzado para el Dashboard de Analítica.
    """
    # Rango de fechas para fecha_compra - Simplificado para evitar errores de widget
    fecha_compra = django_filters.DateFromToRangeFilter(
        widget=django_filters.widgets.RangeWidget(attrs={
            'type': 'date', 
            'class': 'bg-surface-container-high border-none rounded-lg text-[10px] font-black uppercase tracking-widest text-on-background focus:ring-jmie-orange/50 px-3 py-2'
        })
    )
    
    # Filtros por relaciones
    tipo = django_filters.ModelChoiceFilter(
        field_name='modelo__tipo_dispositivo',
        queryset=TipoDispositivo.objects.all(),
        empty_label="Todos los Tipos",
        widget=forms.Select(attrs={'class': 'bg-surface-container-high border-none rounded-lg text-[10px] font-black uppercase tracking-widest text-on-background focus:ring-jmie-orange/50 px-3 py-2'})
    )
    
    estado = django_filters.ModelChoiceFilter(
        queryset=EstadoDispositivo.objects.all(),
        empty_label="Todos los Estados",
        widget=forms.Select(attrs={'class': 'bg-surface-container-high border-none rounded-lg text-[10px] font-black uppercase tracking-widest text-on-background focus:ring-jmie-orange/50 px-3 py-2'})
    )
    
    centro_costo = django_filters.ModelChoiceFilter(
        queryset=CentroCosto.objects.all(),
        empty_label="Todas las Obras/CC",
        widget=forms.Select(attrs={'class': 'bg-surface-container-high border-none rounded-lg text-[10px] font-black uppercase tracking-widest text-on-background focus:ring-jmie-orange/50 px-3 py-2'})
    )
    
    fabricante = django_filters.ModelChoiceFilter(
        field_name='modelo__fabricante',
        queryset=Fabricante.objects.all(),
        empty_label="Todos los Fabricantes",
        widget=forms.Select(attrs={'class': 'bg-surface-container-high border-none rounded-lg text-[10px] font-black uppercase tracking-widest text-on-background focus:ring-jmie-orange/50 px-3 py-2'})
    )

    class Meta:
        model = Dispositivo
        fields = ['tipo', 'estado', 'centro_costo', 'fabricante']
