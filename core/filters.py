import django_filters
from django import forms
from .models import Fabricante, TipoDispositivo, CentroCosto, EstadoDispositivo
from dispositivos.models import Dispositivo

class DashboardFilterSet(django_filters.FilterSet):
    # Rango de fechas para fecha_compra
    fecha_compra = django_filters.DateFromToRangeFilter(
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date', 'class': 'bg-surface-container-high border-none rounded-lg text-xs font-bold text-on-background focus:ring-jmie-orange/50'})
    )
    
    # Filtros por relaciones
    tipo = django_filters.ModelChoiceFilter(
        queryset=TipoDispositivo.objects.all(),
        empty_label="Todos los Tipos",
        widget=forms.Select(attrs={'class': 'bg-surface-container-high border-none rounded-lg text-xs font-bold text-on-background focus:ring-jmie-orange/50'})
    )
    
    estado = django_filters.ModelChoiceFilter(
        queryset=EstadoDispositivo.objects.all(),
        empty_label="Todos los Estados",
        widget=forms.Select(attrs={'class': 'bg-surface-container-high border-none rounded-lg text-xs font-bold text-on-background focus:ring-jmie-orange/50'})
    )
    
    centro_costo = django_filters.ModelChoiceFilter(
        queryset=CentroCosto.objects.all(),
        empty_label="Todos los CC",
        widget=forms.Select(attrs={'class': 'bg-surface-container-high border-none rounded-lg text-xs font-bold text-on-background focus:ring-jmie-orange/50'})
    )
    
    fabricante = django_filters.ModelChoiceFilter(
        field_name='modelo__fabricante',
        queryset=Fabricante.objects.all(),
        empty_label="Todos los Fabricantes",
        widget=forms.Select(attrs={'class': 'bg-surface-container-high border-none rounded-lg text-xs font-bold text-on-background focus:ring-jmie-orange/50'})
    )

    class Meta:
        model = Dispositivo
        fields = ['tipo', 'estado', 'centro_costo', 'modelo']
