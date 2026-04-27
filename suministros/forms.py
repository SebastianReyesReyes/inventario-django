from django import forms
from django.urls import reverse_lazy
from .models import Suministro, CategoriaSuministro, MovimientoStock
from core.models import Modelo
from core.forms import BaseStyledForm

class SuministroForm(BaseStyledForm):
    class Meta:
        model = Suministro
        fields = ['nombre', 'categoria', 'codigo_interno', 'marca', 'es_alternativo', 'unidad_medida', 'stock_minimo', 'modelos_compatibles']
        widgets = {
            'categoria': forms.Select(attrs={
                'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background',
                'hx-get': reverse_lazy('suministros:ajax_get_modelos_compatibles'),
                'hx-target': '#id_modelos_compatibles',
                'hx-trigger': 'change',
            }),
            'modelos_compatibles': forms.SelectMultiple(attrs={
                'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background h-32',
            }),
            'nombre': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'codigo_interno': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'marca': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'es_alternativo': forms.CheckboxInput(attrs={'class': 'rounded border-white/10 bg-white/5 text-jmie-orange focus:ring-jmie-orange'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'categoria' in self.data:
            try:
                categoria_id = int(self.data.get('categoria'))
                categoria = CategoriaSuministro.objects.get(id=categoria_id)
                tipos = categoria.tipos_dispositivo_compatibles.all()
                if tipos.exists():
                    self.fields['modelos_compatibles'].queryset = Modelo.objects.filter(tipo_dispositivo__in=tipos).order_by('nombre')
                else:
                    self.fields['modelos_compatibles'].queryset = Modelo.objects.all().order_by('nombre')
            except (ValueError, TypeError, CategoriaSuministro.DoesNotExist):
                pass
        elif self.instance.pk and self.instance.categoria:
            tipos = self.instance.categoria.tipos_dispositivo_compatibles.all()
            if tipos.exists():
                self.fields['modelos_compatibles'].queryset = Modelo.objects.filter(tipo_dispositivo__in=tipos).order_by('nombre')
            else:
                self.fields['modelos_compatibles'].queryset = Modelo.objects.all().order_by('nombre')

class MovimientoStockForm(BaseStyledForm):
    class Meta:
        model = MovimientoStock
        fields = ['suministro', 'tipo_movimiento', 'cantidad', 'costo_unitario', 'numero_factura', 'colaborador_destino', 'centro_costo', 'notas']
        widgets = {
            'suministro': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'tipo_movimiento': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'cantidad': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'numero_factura': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'colaborador_destino': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'centro_costo': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'notas': forms.Textarea(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background', 'rows': 3}),
        }
