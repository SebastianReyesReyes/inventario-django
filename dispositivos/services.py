from django.core.exceptions import ObjectDoesNotExist
from .forms import DispositivoForm, NotebookForm, SmartphoneForm, MonitorForm
from core.models import TipoDispositivo

class DispositivoFactory:
    """Fábrica para resolver el formulario adecuado según el tipo de dispositivo."""

    @classmethod
    def get_form_class_for_tipo(cls, tipo):
        if not tipo:
            return DispositivoForm
        nombre = tipo.nombre.lower()
        if 'notebook' in nombre or 'laptop' in nombre:
            return NotebookForm
        elif 'smartphone' in nombre or 'celular' in nombre:
            return SmartphoneForm
        elif 'monitor' in nombre:
            return MonitorForm
        return DispositivoForm

    @classmethod
    def get_form_class(cls, tipo_id=None):
        if not tipo_id:
            return DispositivoForm
            
        try:
            tipo = TipoDispositivo.objects.get(pk=tipo_id)
            return cls.get_form_class_for_tipo(tipo)
        except TipoDispositivo.DoesNotExist:
            return DispositivoForm

    @classmethod
    def create_form_instance(cls, post_data=None, files_data=None, tipo_id=None, instance=None):
        """Retorna una instancia del formulario correcto inicializado, soportando creación o edición."""
        if instance:
            # Para edición, el tipo ya viene en la instancia
            tipo = getattr(instance, 'tipo', None)
            FormClass = cls.get_form_class_for_tipo(tipo)
            
            sub_instance = instance
            if FormClass != DispositivoForm:
                model_name = FormClass.Meta.model.__name__.lower()
                try:
                    sub_instance = getattr(instance, model_name)
                except ObjectDoesNotExist:
                    # El registro base existe pero no la extensión especializada
                    # Instanciamos la clase hija y enlazamos el puntero a la clase padre
                    sub_instance = FormClass.Meta.model(dispositivo_ptr_id=instance.id)
                    sub_instance.__dict__.update(instance.__dict__)
                except Exception:
                    pass
            
            if post_data is not None:
                return FormClass(post_data, files_data, instance=sub_instance)
            return FormClass(instance=sub_instance)

        # Para creación
        FormClass = cls.get_form_class(tipo_id)
        if post_data is not None:
            return FormClass(post_data, files_data)
        return FormClass()
