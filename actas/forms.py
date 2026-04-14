from django import forms
from .models import Acta
from core.forms import BaseStyledForm
from colaboradores.models import Colaborador

class ActaCrearForm(BaseStyledForm):
    class Meta:
        model = Acta
        fields = ['colaborador', 'tipo_acta', 'ministro_de_fe', 'observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Detalles adicionales, estado de entrega, etc.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar colaboradores activos
        self.fields['colaborador'].queryset = Colaborador.objects.filter(esta_activo=True).order_by('first_name', 'last_name')
        
        # Queryset para Ministro de Fe: Colaboradores activos con cargos administrativos
        # (Se filtrará dinámicamente vía HTMX en el modal, pero aquí ponemos el default)
        from django.db.models import Q
        admin_criterios = Q(cargo__icontains='Administrador') | Q(cargo__icontains='Jefe') | Q(cargo__icontains='Encargado')
        self.fields['ministro_de_fe'].queryset = Colaborador.objects.filter(
            esta_activo=True
        ).filter(admin_criterios).order_by('first_name', 'last_name')
        self.fields['ministro_de_fe'].required = False
        # Atributos para interactividad
        self.fields['tipo_acta'].widget.attrs.update({
            'x-model': 'tipoActa',
            'class': 'form-select-jmie'
        })
        
        self.fields['colaborador'].widget.attrs.update({
            'class': 'form-select-jmie htmx-colaborador-select',
        })

        self.fields['ministro_de_fe'].widget.attrs.update({
            'class': 'form-select-jmie htmx-ministro-select',
        })
        
