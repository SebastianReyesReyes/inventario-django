from django import forms
from django.urls import reverse_lazy
from .models import Dispositivo, HistorialAsignacion, EntregaAccesorio
from core.models import Fabricante, Modelo
from core.forms import BaseStyledForm
from colaboradores.models import Colaborador

class DispositivoForm(BaseStyledForm):
    # Campo extra no persistido para filtrar por marca en la UI
    fabricante = forms.ModelChoiceField(
        queryset=Fabricante.objects.all(),
        required=False,
        label="Marca/Fabricante",
        widget=forms.Select(attrs={
            'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background focus:border-jmie-blue transition-all',
            'hx-get': reverse_lazy('dispositivos:ajax_get_modelos'),
            'hx-target': '#id_modelo',
            'hx-trigger': 'change'
        })
    )
    
    generar_acta = forms.BooleanField(
        required=False,
        label="Generar Acta de Entrega automáticamente",
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-jmie-orange focus:ring-jmie-orange/20',
        })
    )

    class Meta:
        model = Dispositivo
        fields = [
            'numero_serie', 'tipo', 
            'fabricante', 'modelo', 'estado', 'propietario_actual', 
            'centro_costo', 'fecha_compra', 'valor_contable', 'notas_condicion',
            'generar_acta'
        ]
        widgets = {

            'numero_serie': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background', 'placeholder': 'Número de serie único'}),
            'tipo': forms.Select(attrs={
                'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background',
                'x-model': 'tipoEquipoId',
                '@change': 'updateTipoEquipo()'
            }),
            'modelo': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'estado': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'propietario_actual': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'centro_costo': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'fecha_compra': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background', 'type': 'date'}),
            'valor_contable': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'notas_condicion': forms.Textarea(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background', 'rows': 3}),
        }

    def clean_numero_serie(self):
        serie = self.cleaned_data.get('numero_serie')
        qs = Dispositivo.objects.filter(numero_serie=serie)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Este número de serie ya está registrado.")
        return serie



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si no hay fabricante seleccionado todavía (o no es un POST con data), 
        # dejamos los modelos vacíos para obligar a seleccionar marca primero.
        if 'fabricante' in self.data:
            try:
                fabricante_id = int(self.data.get('fabricante'))
                self.fields['modelo'].queryset = Modelo.objects.filter(fabricante_id=fabricante_id).order_by('nombre')
            except (ValueError, TypeError):
                self.fields['modelo'].queryset = Modelo.objects.none()
        elif self.instance.pk:
            self.fields['modelo'].queryset = self.instance.modelo.fabricante.modelos.order_by('nombre')
            self.initial['fabricante'] = self.instance.modelo.fabricante
        else:
            self.fields['modelo'].queryset = Modelo.objects.none()

    def save(self, commit=True):
        is_new = self.instance.pk is None
        dispositivo = super().save(commit=commit)
        
        # Si el equipo es nuevo, tiene propietario y se guardó en BD, registramos el historial
        if is_new and dispositivo.propietario_actual and commit:
            HistorialAsignacion.objects.create(
                dispositivo=dispositivo,
                colaborador=dispositivo.propietario_actual,
                condicion_fisica="Asignación inicial directa desde el registro del equipo."
            )
            
        return dispositivo

class NotebookForm(DispositivoForm):
    class Meta(DispositivoForm.Meta):
        from .models import Notebook
        model = Notebook
        fields = DispositivoForm.Meta.fields + [
            'procesador', 'ram_gb', 'almacenamiento', 'sistema_operativo', 'mac_address', 'ip_asignada'
        ]
        widgets = {
            **DispositivoForm.Meta.widgets,
            'procesador': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'ram_gb': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'almacenamiento': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'sistema_operativo': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'mac_address': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'ip_asignada': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
        }

class NotebookTechForm(forms.ModelForm):
    """Solo para renderizado de UI mediante HTMX"""
    class Meta:
        from .models import Notebook
        model = Notebook
        fields = ['procesador', 'ram_gb', 'almacenamiento', 'sistema_operativo', 'mac_address']
        widgets = {
            'procesador': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'ram_gb': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'almacenamiento': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'sistema_operativo': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'mac_address': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
        }

class SmartphoneForm(DispositivoForm):
    class Meta(DispositivoForm.Meta):
        from .models import Smartphone
        model = Smartphone
        fields = DispositivoForm.Meta.fields + [
            'imei_1', 'imei_2', 'numero_telefono'
        ]
        widgets = {
            **DispositivoForm.Meta.widgets,
            'imei_1': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'imei_2': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'numero_telefono': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
        }

class MonitorForm(DispositivoForm):
    class Meta(DispositivoForm.Meta):
        from .models import Monitor
        model = Monitor
        fields = DispositivoForm.Meta.fields + [
            'pulgadas', 'resolucion'
        ]
        widgets = {
            **DispositivoForm.Meta.widgets,
            'pulgadas': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background', 'step': '0.1'}),
            'resolucion': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background', 'placeholder': 'Ej: 1920x1080'}),
        }

class SmartphoneTechForm(forms.ModelForm):
    """Solo para renderizado de UI mediante HTMX"""
    class Meta:
        from .models import Smartphone
        model = Smartphone
        fields = ['imei_1', 'imei_2', 'numero_telefono']
        widgets = {
            'imei_1': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'imei_2': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'numero_telefono': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
        }

class MonitorTechForm(forms.ModelForm):
    """Solo para renderizado de UI"""
    class Meta:
        from .models import Monitor
        model = Monitor
        fields = ['pulgadas', 'resolucion']
        widgets = {
            'pulgadas': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background', 'step': '0.1'}),
            'resolucion': forms.TextInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background', 'placeholder': 'Ej: 1920x1080'}),
        }

class MantenimientoForm(forms.ModelForm):
    class Meta:
        from .models import BitacoraMantenimiento
        model = BitacoraMantenimiento
        fields = ['falla_reportada', 'reparacion_realizada', 'costo_reparacion', 'tecnico_responsable', 'cambio_estado_automatico']
        widgets = {
            'falla_reportada': forms.Textarea(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background', 'rows': 3}),
            'reparacion_realizada': forms.Textarea(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background', 'rows': 3}),
            'costo_reparacion': forms.NumberInput(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'tecnico_responsable': forms.Select(attrs={'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background'}),
            'cambio_estado_automatico': forms.CheckboxInput(attrs={'class': 'rounded border-white/10 bg-white/5 text-jmie-orange focus:ring-jmie-orange'}),
        }


class AsignacionForm(BaseStyledForm):
    generar_acta = forms.BooleanField(
        required=False, 
        initial=True, 
        label="Generar Acta de Entrega automáticamente",
        widget=forms.CheckboxInput(attrs={'class': 'rounded border-white/10 bg-white/5 text-jmie-orange focus:ring-jmie-orange'})
    )

    class Meta:
        model = HistorialAsignacion
        fields = ['colaborador', 'condicion_fisica', 'generar_acta']
        widgets = {
            'condicion_fisica': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descripción del estado físico actual del equipo...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['colaborador'].queryset = Colaborador.objects.filter(esta_activo=True).order_by('first_name')
        self.fields['colaborador'].label = 'Asignar a Colaborador'
        self.fields['condicion_fisica'].label = 'Condición Física al Momento de la Entrega'

class ReasignacionForm(BaseStyledForm):
    generar_acta = forms.BooleanField(
        required=False, 
        initial=True, 
        label="Generar Acta de Entrega automáticamente",
        widget=forms.CheckboxInput(attrs={'class': 'rounded border-white/10 bg-white/5 text-jmie-orange focus:ring-jmie-orange'})
    )

    class Meta:
        model = HistorialAsignacion
        fields = ['colaborador', 'condicion_fisica', 'generar_acta']
        widgets = {
            'condicion_fisica': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Condición física al momento de la reasignación...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['colaborador'].queryset = Colaborador.objects.filter(esta_activo=True).order_by('first_name')
        self.fields['colaborador'].label = 'Reasignar a Colaborador'
        self.fields['condicion_fisica'].label = 'Condición Física al Momento de la Reasignación'

class DevolucionForm(forms.Form):
    """Formulario para devolución — no crea HistorialAsignacion directamente."""
    ESTADO_OPCIONES = [
        ('bueno', 'Equipo en buen estado → Disponible'),
        ('danado', 'Equipo dañado → Enviar a Reparación'),
    ]
    condicion_fisica = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Descripción del estado físico al momento de la devolución...',
            'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background placeholder:text-jmie-gray focus:ring-1 focus:border-jmie-blue focus:ring-jmie-blue/40 transition-all'
        }),
        label='Condición Física al Devolver'
    )
    estado_llegada = forms.ChoiceField(
        choices=ESTADO_OPCIONES,
        widget=forms.RadioSelect(attrs={'class': 'text-jmie-orange'}),
        label='Estado del Equipo al Llegar'
    )
    generar_acta = forms.BooleanField(
        required=False, 
        initial=True, 
        label="Generar Acta de Devolución automáticamente",
        widget=forms.CheckboxInput(attrs={'class': 'rounded border-white/10 bg-white/5 text-jmie-orange focus:ring-jmie-orange'})
    )

class AccesorioForm(BaseStyledForm):
    class Meta:
        model = EntregaAccesorio
        fields = ['tipo', 'cantidad', 'descripcion']
        widgets = {
            'tipo': forms.TextInput(attrs={
                'list': 'tipos-comunes-list',
                'placeholder': 'Ej: Mouse, Teclado, Mochila...'
            }),
            'descripcion': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descripción opcional...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].label = 'Tipo de Accesorio'
        self.fields['cantidad'].label = 'Cantidad'
        self.fields['descripcion'].label = 'Descripción (Opcional)'
