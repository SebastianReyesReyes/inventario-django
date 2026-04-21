import pytest
from django.utils import timezone

from dispositivos.services import DispositivoFactory as FormFactory, TrazabilidadService
from dispositivos.forms import (
    DispositivoForm, NotebookForm, SmartphoneForm, MonitorForm,
    AsignacionForm, ReasignacionForm, DevolucionForm, AccesorioForm
)
from dispositivos.tests.factories import TipoDispositivoFactory
from core.tests.factories import (
    ColaboradorFactory, DispositivoFactory, EstadoDispositivoFactory,
    HistorialAsignacionFactory
)


@pytest.mark.django_db
class TestDispositivoService:
    def test_get_form_class_por_nombre(self):
        """El factory de formularios debe mapear adecuadamente el formulario correcto usando el Tipo."""
        tipo_ntbk = TipoDispositivoFactory(nombre="Notebook")
        tipo_smart = TipoDispositivoFactory(nombre="Smartphone")
        tipo_monitor = TipoDispositivoFactory(nombre="Monitor")
        tipo_random = TipoDispositivoFactory(nombre="Router")  # No está en los especializados

        assert FormFactory.get_form_class(tipo_ntbk.id) == NotebookForm
        assert FormFactory.get_form_class(tipo_smart.id) == SmartphoneForm
        assert FormFactory.get_form_class(tipo_monitor.id) == MonitorForm

        # Tipos no mapeados en FORM_MAP caen al default general
        assert FormFactory.get_form_class(tipo_random.id) == DispositivoForm

        # Id nulo o faltante
        assert FormFactory.get_form_class(None) == DispositivoForm

    def test_create_form_instance_vacio(self):
        """Debe instanciar NotebookForm basándose en su ID parametrizado al crear uno nuevo."""
        tipo_ntbk = TipoDispositivoFactory(nombre="Notebook")
        form_instance = FormFactory.create_form_instance(tipo_id=tipo_ntbk.id)

        assert isinstance(form_instance, NotebookForm)
        assert not form_instance.is_bound  # Formulario vacío para GET


@pytest.mark.django_db
class TestTrazabilidadService:
    """Pruebas unitarias para la capa de servicio de trazabilidad."""

    def test_asignar_crea_historial_y_cambia_estado(self):
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Disponible'), propietario_actual=None)
        colaborador = ColaboradorFactory()
        form = AsignacionForm(data={
            'colaborador': colaborador.pk,
            'condicion_fisica': 'Nuevo',
            'generar_acta': ''
        })
        assert form.is_valid()
        movimiento, acta = TrazabilidadService.asignar(dispositivo, form)

        assert movimiento.dispositivo == dispositivo
        assert movimiento.colaborador == colaborador
        dispositivo.refresh_from_db()
        assert dispositivo.propietario_actual == colaborador
        assert dispositivo.estado.nombre == 'Asignado'
        assert acta is None

    def test_asignar_con_acta(self):
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Disponible'), propietario_actual=None)
        colaborador = ColaboradorFactory()
        admin = ColaboradorFactory()
        form = AsignacionForm(data={
            'colaborador': colaborador.pk,
            'condicion_fisica': 'Nuevo',
            'generar_acta': 'on'
        })
        assert form.is_valid()
        movimiento, acta = TrazabilidadService.asignar(dispositivo, form, creado_por=admin)

        assert acta is not None
        assert acta.tipo_acta == 'ENTREGA'
        assert acta.colaborador == colaborador

    def test_reasignar_cierra_anterior_y_crea_nuevo(self):
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Asignado'))
        anterior = ColaboradorFactory()
        nuevo = ColaboradorFactory()
        hist = HistorialAsignacionFactory(dispositivo=dispositivo, colaborador=anterior, fecha_fin=None)

        form = ReasignacionForm(data={
            'colaborador': nuevo.pk,
            'condicion_fisica': 'Usado',
            'generar_acta': ''
        })
        assert form.is_valid()
        nuevo_mov, acta = TrazabilidadService.reasignar(dispositivo, form)

        hist.refresh_from_db()
        assert hist.fecha_fin is not None
        assert hist.fecha_fin == timezone.now().date()
        dispositivo.refresh_from_db()
        assert dispositivo.propietario_actual == nuevo
        assert nuevo_mov.colaborador == nuevo

    def test_devolver_bueno_disponible(self):
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Asignado'))
        colaborador = ColaboradorFactory()
        hist = HistorialAsignacionFactory(dispositivo=dispositivo, colaborador=colaborador, fecha_fin=None)

        form = DevolucionForm(data={
            'condicion_fisica': 'Perfecto',
            'estado_llegada': 'bueno',
            'generar_acta': ''
        })
        assert form.is_valid()
        ultimo_mov, acta = TrazabilidadService.devolver(dispositivo, form)

        dispositivo.refresh_from_db()
        assert dispositivo.estado.nombre == 'Disponible'
        assert dispositivo.propietario_actual is None
        hist.refresh_from_db()
        assert hist.fecha_fin is not None
        assert '[Devolución]: Perfecto' in hist.condicion_fisica

    def test_devolver_danado_reparacion(self):
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Asignado'))
        colaborador = ColaboradorFactory()
        HistorialAsignacionFactory(dispositivo=dispositivo, colaborador=colaborador, fecha_fin=None)

        form = DevolucionForm(data={
            'condicion_fisica': 'Pantalla rota',
            'estado_llegada': 'danado',
            'generar_acta': ''
        })
        assert form.is_valid()
        TrazabilidadService.devolver(dispositivo, form)

        dispositivo.refresh_from_db()
        assert dispositivo.estado.nombre == 'En Reparación'
        assert dispositivo.propietario_actual is None

    def test_devolver_genera_acta_devolucion(self):
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Asignado'))
        colaborador = ColaboradorFactory()
        admin = ColaboradorFactory()
        HistorialAsignacionFactory(dispositivo=dispositivo, colaborador=colaborador, fecha_fin=None)

        form = DevolucionForm(data={
            'condicion_fisica': 'Rayado',
            'estado_llegada': 'bueno',
            'generar_acta': 'on'
        })
        assert form.is_valid()
        _, acta = TrazabilidadService.devolver(dispositivo, form, creado_por=admin)

        assert acta is not None
        assert acta.tipo_acta == 'DEVOLUCION'

    def test_entregar_accesorio(self):
        colaborador = ColaboradorFactory()
        form = AccesorioForm(data={'tipo': 'Teclado', 'cantidad': 1, 'descripcion': ''})
        assert form.is_valid()
        entrega = TrazabilidadService.entregar_accesorio(colaborador, form)

        assert entrega.colaborador == colaborador
        assert entrega.tipo == 'Teclado'
