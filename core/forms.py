from django import forms
from .models import TipoDispositivo, Fabricante, Modelo, CentroCosto, EstadoDispositivo, Departamento

class BaseStyledForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            current_classes = field.widget.attrs.get('class', '')
            base_classes = 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background placeholder:text-jmie-gray focus:ring-1 focus:border-jmie-blue focus:ring-jmie-blue/40 transition-all'
            
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'w-5 h-5 rounded border-white/10 bg-surface-container-high text-jmie-orange focus:ring-jmie-orange/40 transition-all'})
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.update({'class': f'{base_classes} appearance-none'})
            else:
                field.widget.attrs.update({'class': base_classes})

class TipoDispositivoForm(BaseStyledForm):
    class Meta:
        model = TipoDispositivo
        fields = ['nombre', 'sigla']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Notebook, Smartphone...'}),
            'sigla': forms.TextInput(attrs={'placeholder': 'Ej: NTBK, SMPH...'}),
        }

class FabricanteForm(BaseStyledForm):
    class Meta:
        model = Fabricante
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Lenovo, Dell, Apple...'}),
        }

class ModeloForm(BaseStyledForm):
    class Meta:
        model = Modelo
        fields = ['nombre', 'fabricante', 'tipo_dispositivo']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: ThinkPad X1 Carbon...'}),
            'fabricante': forms.Select(),
            'tipo_dispositivo': forms.Select(),
        }

class CentroCostoForm(BaseStyledForm):
    class Meta:
        model = CentroCosto
        fields = ['nombre', 'codigo_contable', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Operaciones, Administración...'}),
            'codigo_contable': forms.TextInput(attrs={'placeholder': 'Ej: CC-1001...'}),
        }

class EstadoDispositivoForm(BaseStyledForm):
    class Meta:
        model = EstadoDispositivo
        fields = ['nombre', 'color']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Disponible, En Reparación...'}),
            'color': forms.HiddenInput(),
        }


class DepartamentoForm(BaseStyledForm):
    class Meta:
        model = Departamento
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Operaciones, TI, Administración...'}),
        }
