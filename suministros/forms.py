from django import forms
from django.urls import reverse_lazy
from django.utils import timezone
from .models import Suministro, CategoriaSuministro, MovimientoStock
from core.models import Modelo, Fabricante
from core.forms import BaseStyledForm


class CategoriaSuministroForm(BaseStyledForm):
    class Meta:
        model = CategoriaSuministro
        fields = ['nombre', 'descripcion', 'tipos_dispositivo_compatibles']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Tóner, Cartucho, Resma...'}),
            'descripcion': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descripción breve de la categoría'}),
            'tipos_dispositivo_compatibles': forms.SelectMultiple(attrs={
                'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background h-28',
            }),
        }


class SuministroForm(BaseStyledForm):
    class Meta:
        model = Suministro
        fields = ['nombre', 'categoria', 'codigo_interno', 'fabricante', 'es_alternativo', 'unidad_medida', 'stock_minimo', 'modelos_compatibles']
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
            'fabricante': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
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
    seguir_ingresando = forms.BooleanField(
        required=False,
        label="Guardar y seguir registrando esta factura",
        widget=forms.CheckboxInput(attrs={'class': 'rounded border-white/10 bg-white/5 text-jmie-orange focus:ring-jmie-orange'})
    )

    class Meta:
        model = MovimientoStock
        fields = ['suministro', 'tipo_movimiento', 'cantidad', 'costo_unitario', 'numero_factura', 'colaborador_destino', 'centro_costo', 'dispositivo_destino', 'notas']
        widgets = {
            'suministro': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'tipo_movimiento': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'cantidad': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'numero_factura': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'colaborador_destino': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'centro_costo': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'dispositivo_destino': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'notas': forms.Textarea(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Auto-llenar centro de costo vía HTMX al cambiar destinatario
        self.fields['colaborador_destino'].widget.attrs.update({
            'hx-get': reverse_lazy('suministros:ajax_colaborador_centro_costo'),
            'hx-target': '#id_centro_costo',
            'hx-trigger': 'change',
        })


class FacturaCabeceraForm(forms.Form):
    numero_factura = forms.CharField(
        label="Número de Factura",
        widget=forms.TextInput(attrs={'placeholder': 'Ej: F001-00001234'})
    )
    fecha = forms.DateField(
        label="Fecha de Factura",
        initial=timezone.now,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            base_classes = 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background placeholder:text-jmie-gray focus:ring-1 focus:border-jmie-blue focus:ring-jmie-blue/40 transition-all'
            field.widget.attrs.update({'class': base_classes})


class MovimientoFacturaForm(BaseStyledForm):
    class Meta:
        model = MovimientoStock
        fields = ['suministro', 'cantidad', 'costo_unitario', 'notas']
        widgets = {
            'notas': forms.Textarea(attrs={'rows': 1, 'placeholder': 'Opcional...'}),
            'suministro': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-2 text-on-background text-sm'}),
            'cantidad': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-2 text-on-background text-sm text-center'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-2 text-on-background text-sm text-center'}),
        }
