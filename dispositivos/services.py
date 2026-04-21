from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from .forms import DispositivoForm, NotebookForm, SmartphoneForm, MonitorForm
from core.models import TipoDispositivo, EstadoDispositivo


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


class TrazabilidadService:
    """Servicio para encapsular la lógica transaccional de asignaciones, reasignaciones, devoluciones y entregas de accesorios."""

    @staticmethod
    @transaction.atomic
    def asignar(dispositivo, form, creado_por=None):
        """
        Asigna un dispositivo disponible a un colaborador.
        Retorna (movimiento, acta).
        """
        movimiento = form.save(commit=False)
        movimiento.dispositivo = dispositivo
        movimiento.save()

        estado_asignado, _ = EstadoDispositivo.objects.get_or_create(nombre='Asignado')
        dispositivo.estado = estado_asignado
        dispositivo.propietario_actual = movimiento.colaborador
        dispositivo.save()

        acta = None
        if form.cleaned_data.get('generar_acta'):
            from actas.services import ActaService
            acta = ActaService.crear_acta(
                colaborador=movimiento.colaborador,
                tipo_acta='ENTREGA',
                asignacion_ids=[movimiento.pk],
                creado_por=creado_por,
                observaciones=f"Acta generada automáticamente al asignar equipo {dispositivo.identificador_interno}."
            )
        return movimiento, acta

    @staticmethod
    @transaction.atomic
    def reasignar(dispositivo, form, creado_por=None):
        """
        Reasigna un dispositivo de un colaborador a otro.
        Retorna (nuevo_movimiento, acta).
        """
        ultimo_mov = dispositivo.historial.filter(fecha_fin__isnull=True).first()
        if ultimo_mov:
            ultimo_mov.fecha_fin = timezone.now().date()
            ultimo_mov.save()

        nuevo_mov = form.save(commit=False)
        nuevo_mov.dispositivo = dispositivo
        nuevo_mov.save()

        dispositivo.propietario_actual = nuevo_mov.colaborador
        dispositivo.save()

        acta = None
        if form.cleaned_data.get('generar_acta'):
            from actas.services import ActaService
            acta = ActaService.crear_acta(
                colaborador=nuevo_mov.colaborador,
                tipo_acta='ENTREGA',
                asignacion_ids=[nuevo_mov.pk],
                creado_por=creado_por,
                observaciones=f"Acta generada automáticamente al reasignar equipo {dispositivo.identificador_interno}."
            )
        return nuevo_mov, acta

    @staticmethod
    @transaction.atomic
    def devolver(dispositivo, form, creado_por=None):
        """
        Registra la devolución de un dispositivo a bodega.
        Retorna (ultimo_movimiento, acta).
        """
        ultimo_mov = dispositivo.historial.filter(fecha_fin__isnull=True).first()
        colaborador_que_devuelve = ultimo_mov.colaborador if ultimo_mov else None

        if ultimo_mov:
            ultimo_mov.fecha_fin = timezone.now().date()
            condicion = form.cleaned_data['condicion_fisica']
            ultimo_mov.condicion_fisica += f"\n[Devolución]: {condicion}"
            ultimo_mov.save()

        estado_slug = form.cleaned_data['estado_llegada']
        if estado_slug == 'danado':
            nuevo_estado, _ = EstadoDispositivo.objects.get_or_create(nombre='En Reparación')
        else:
            nuevo_estado, _ = EstadoDispositivo.objects.get_or_create(nombre='Disponible')

        dispositivo.estado = nuevo_estado
        dispositivo.propietario_actual = None
        dispositivo.save()

        acta = None
        if form.cleaned_data.get('generar_acta') and colaborador_que_devuelve:
            from actas.services import ActaService
            acta = ActaService.crear_acta(
                colaborador=colaborador_que_devuelve,
                tipo_acta='DEVOLUCION',
                asignacion_ids=[ultimo_mov.pk] if ultimo_mov else [],
                creado_por=creado_por,
                observaciones=f"Acta de devolución generada automáticamente para equipo {dispositivo.identificador_interno}."
            )
        return ultimo_mov, acta

    @staticmethod
    @transaction.atomic
    def entregar_accesorio(colaborador, form, creado_por=None):
        """
        Registra la entrega de un accesorio a un colaborador.
        Retorna la instancia de EntregaAccesorio.
        """
        entrega = form.save(commit=False)
        entrega.colaborador = colaborador
        entrega.save()
        return entrega
