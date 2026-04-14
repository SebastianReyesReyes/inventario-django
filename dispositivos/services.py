from django.core.exceptions import ObjectDoesNotExist
from .forms import DispositivoForm, NotebookForm, SmartphoneForm, MonitorForm
from core.models import TipoDispositivo

class DispositivoFactory:
    """Fábrica para resolver el formulario adecuado según el tipo de dispositivo."""
    
    FORM_MAP = {
        'Notebook': NotebookForm,
        'Smartphone': SmartphoneForm,
        'Monitor': MonitorForm,
    }

    @classmethod
    def get_form_class(cls, tipo_id=None):
        if not tipo_id:
            return DispositivoForm
            
        try:
            tipo = TipoDispositivo.objects.get(pk=tipo_id)
            return cls.FORM_MAP.get(tipo.nombre, DispositivoForm)
        except TipoDispositivo.DoesNotExist:
            return DispositivoForm

    @classmethod
    def create_form_instance(cls, post_data=None, files_data=None, tipo_id=None, instance=None):
        """Retorna una instancia del formulario correcto inicializado, soportando creación o edición."""
        if instance:
            # Para edición, el tipo ya viene en la instancia
            tipo = getattr(instance, 'tipo', None)
            FormClass = cls.FORM_MAP.get(tipo.nombre, DispositivoForm) if tipo else DispositivoForm
            # Intentamos obtener la instancia de la clase hija si existe
            sub_instance = instance
            if tipo:
                sub_attr = tipo.nombre.lower()
                if hasattr(instance, sub_attr):
                    sub_instance = getattr(instance, sub_attr)
            
            if post_data is not None:
                return FormClass(post_data, files_data, instance=sub_instance)
            return FormClass(instance=sub_instance)

        # Para creación
        FormClass = cls.get_form_class(tipo_id)
        if post_data is not None:
            return FormClass(post_data, files_data)
        return FormClass()
