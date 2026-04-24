"""Tests de integración cross-app para el flujo completo de trazabilidad.

Cubre: dispositivos → actas → dashboard, validando que los servicios
coordinen correctamente entre apps.
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from dispositivos.services import TrazabilidadService
from dispositivos.forms import AsignacionForm, ReasignacionForm, DevolucionForm
from dispositivos.models import Dispositivo, HistorialAsignacion
from actas.services import ActaService
from actas.models import Acta
from dashboard.services import DashboardMetricsService

from core.tests.factories import (
    ColaboradorFactory,
    DispositivoFactory,
    EstadoDisponibleFactory,
    EstadoAsignadoFactory,
    EstadoReparacionFactory,
    HistorialAsignacionFactory,
    ActaFactory,
)


@pytest.mark.integration
@pytest.mark.django_db
class TestFullDeliveryFlow:
    """Flujo completo: crear dispositivo → asignar → generar acta → firmar."""

    def test_assign_device_creates_acta_and_pdf(self):
        """Asignar un dispositivo con generar_acta=True crea acta vinculada y PDF válido."""
        dispositivo = DispositivoFactory(
            estado=EstadoDisponibleFactory(),
            propietario_actual=None,
        )
        colaborador = ColaboradorFactory(first_name="Juan", last_name="Pérez")
        admin = ColaboradorFactory()

        form = AsignacionForm(data={
            'colaborador': colaborador.pk,
            'condicion_fisica': 'Nuevo en caja',
            'generar_acta': 'on',
        })
        assert form.is_valid()

        movimiento, acta = TrazabilidadService.asignar(dispositivo, form, creado_por=admin)

        dispositivo.refresh_from_db()
        movimiento.refresh_from_db()
        assert dispositivo.propietario_actual == colaborador
        assert dispositivo.estado.nombre == "Asignado"
        assert movimiento.acta == acta
        assert acta.tipo_acta == "ENTREGA"
        assert acta.folio.startswith("ACT-")

        pdf_content = ActaService.generar_pdf(acta)
        assert isinstance(pdf_content, bytes)
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b"%PDF")

    def test_assign_without_acta_skips_document(self):
        """Asignar sin generar_acta no crea acta."""
        dispositivo = DispositivoFactory(
            estado=EstadoDisponibleFactory(),
            propietario_actual=None,
        )
        colaborador = ColaboradorFactory()

        form = AsignacionForm(data={
            'colaborador': colaborador.pk,
            'condicion_fisica': 'Buen estado',
            'generar_acta': '',
        })
        assert form.is_valid()

        movimiento, acta = TrazabilidadService.asignar(dispositivo, form)

        assert acta is None
        assert movimiento.acta is None


@pytest.mark.integration
@pytest.mark.django_db
class TestReassignmentChain:
    """Flujo de reasignación: A → B, preservando historial."""

    def test_reassignment_preserves_history(self):
        """Reasignar cierra el historial anterior y crea uno nuevo."""
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory())
        anterior = ColaboradorFactory(first_name="Ana")
        nuevo = ColaboradorFactory(first_name="Carlos")
        admin = ColaboradorFactory()

        hist = HistorialAsignacionFactory(
            dispositivo=dispositivo,
            colaborador=anterior,
            fecha_fin=None,
        )

        form = ReasignacionForm(data={
            'colaborador': nuevo.pk,
            'condicion_fisica': 'Usado, sin daños',
            'generar_acta': 'on',
        })
        assert form.is_valid()

        nuevo_mov, acta = TrazabilidadService.reasignar(dispositivo, form, creado_por=admin)

        hist.refresh_from_db()
        assert hist.fecha_fin is not None

        dispositivo.refresh_from_db()
        assert dispositivo.propietario_actual == nuevo

        assert nuevo_mov.dispositivo == dispositivo
        assert nuevo_mov.colaborador == nuevo
        assert nuevo_mov.fecha_fin is None

        assert acta is not None
        assert acta.tipo_acta == "ENTREGA"

        total_historial = dispositivo.historial.count()
        assert total_historial == 2

    def test_reassignment_without_acta(self):
        """Reasignar sin generar_acta no crea documento."""
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory())
        anterior = ColaboradorFactory()
        nuevo = ColaboradorFactory()

        HistorialAsignacionFactory(
            dispositivo=dispositivo,
            colaborador=anterior,
            fecha_fin=None,
        )

        form = ReasignacionForm(data={
            'colaborador': nuevo.pk,
            'condicion_fisica': 'OK',
            'generar_acta': '',
        })
        assert form.is_valid()

        _, acta = TrazabilidadService.reasignar(dispositivo, form)
        assert acta is None


@pytest.mark.integration
@pytest.mark.django_db
class TestReturnFlow:
    """Flujo de devolución: asignado → bodega, con acta de devolución."""

    def test_return_good_device_becomes_available(self):
        """Devolver en buen estado pone dispositivo como Disponible."""
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory())
        colaborador = ColaboradorFactory()

        hist = HistorialAsignacionFactory(
            dispositivo=dispositivo,
            colaborador=colaborador,
            fecha_fin=None,
        )

        form = DevolucionForm(data={
            'condicion_fisica': 'Perfecto estado',
            'estado_llegada': 'bueno',
            'generar_acta': '',
        })
        assert form.is_valid()

        ultimo_mov, acta = TrazabilidadService.devolver(dispositivo, form)

        dispositivo.refresh_from_db()
        assert dispositivo.estado.nombre == "Disponible"
        assert dispositivo.propietario_actual is None

        hist.refresh_from_db()
        assert hist.fecha_fin is not None
        assert "[Devolución]: Perfecto estado" in hist.condicion_fisica

    def test_return_damaged_device_goes_to_repair(self):
        """Devolver dañado pone dispositivo en En Reparación."""
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory())
        colaborador = ColaboradorFactory()

        HistorialAsignacionFactory(
            dispositivo=dispositivo,
            colaborador=colaborador,
            fecha_fin=None,
        )

        form = DevolucionForm(data={
            'condicion_fisica': 'Pantalla rota, no enciende',
            'estado_llegada': 'danado',
            'generar_acta': '',
        })
        assert form.is_valid()

        TrazabilidadService.devolver(dispositivo, form)

        dispositivo.refresh_from_db()
        assert dispositivo.estado.nombre == "En Reparación"
        assert dispositivo.propietario_actual is None

    def test_return_generates_devolucion_acta(self):
        """Devolver con generar_acta crea acta de DEVOLUCION."""
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory())
        colaborador = ColaboradorFactory()
        admin = ColaboradorFactory()

        HistorialAsignacionFactory(
            dispositivo=dispositivo,
            colaborador=colaborador,
            fecha_fin=None,
        )

        form = DevolucionForm(data={
            'condicion_fisica': 'Rayado en carcasa',
            'estado_llegada': 'bueno',
            'generar_acta': 'on',
        })
        assert form.is_valid()

        _, acta = TrazabilidadService.devolver(dispositivo, form, creado_por=admin)

        assert acta is not None
        assert acta.tipo_acta == "DEVOLUCION"
        assert acta.colaborador == colaborador


@pytest.mark.integration
@pytest.mark.django_db
class TestActaImmutability:
    """Verificar que actas firmadas son inmutables."""

    def test_signed_acta_cannot_be_modified(self):
        """Intentar modificar un acta firmada lanza ValidationError."""
        acta = ActaFactory(firmada=False)
        ActaService.firmar_acta(acta.pk)

        acta.refresh_from_db()
        assert acta.firmada is True

        acta.observaciones = "Intento de modificación"
        with pytest.raises(ValidationError, match="FIRMADA"):
            acta.save()

    def test_unsigned_acta_can_be_modified(self):
        """Un acta no firmada se puede modificar."""
        acta = ActaFactory(firmada=False)
        acta.observaciones = "Nueva observación"
        acta.save()

        acta.refresh_from_db()
        assert acta.observaciones == "Nueva observación"


@pytest.mark.integration
@pytest.mark.django_db
class TestDashboardMetricsAccuracy:
    """Verificar que el dashboard refleja el estado real de la BD."""

    def test_metrics_reflect_device_states(self):
        """Las métricas del dashboard coinciden con los dispositivos creados."""
        disp1 = DispositivoFactory(estado=EstadoDisponibleFactory())
        disp2 = DispositivoFactory(estado=EstadoDisponibleFactory())
        disp3 = DispositivoFactory(estado=EstadoAsignadoFactory())

        qs = Dispositivo.objects.all()

        context = DashboardMetricsService.build_context(qs, filterset=None, top10_metric="cantidad")

        assert context["total_dispositivos"] == 3
        assert context["total_disponibles"] == 2
        assert context["total_asignados"] == 1

    def test_metrics_update_after_assignment(self):
        """Asignar un dispositivo actualiza las métricas correctamente."""
        disp = DispositivoFactory(estado=EstadoDisponibleFactory(), propietario_actual=None)
        colaborador = ColaboradorFactory()

        qs = Dispositivo.objects.all()
        context_before = DashboardMetricsService.build_context(qs, filterset=None, top10_metric="cantidad")
        assert context_before["total_disponibles"] == 1
        assert context_before["total_asignados"] == 0

        form = AsignacionForm(data={
            'colaborador': colaborador.pk,
            'condicion_fisica': 'Nuevo',
            'generar_acta': '',
        })
        assert form.is_valid()
        TrazabilidadService.asignar(disp, form)

        qs = Dispositivo.objects.all()
        context_after = DashboardMetricsService.build_context(qs, filterset=None, top10_metric="cantidad")
        assert context_after["total_disponibles"] == 0
        assert context_after["total_asignados"] == 1

    def test_metrics_update_after_return(self):
        """Devolver un dispositivo actualiza las métricas."""
        disp = DispositivoFactory(estado=EstadoAsignadoFactory())
        colaborador = ColaboradorFactory()

        HistorialAsignacionFactory(
            dispositivo=disp,
            colaborador=colaborador,
            fecha_fin=None,
        )

        qs = Dispositivo.objects.all()
        context_before = DashboardMetricsService.build_context(qs, filterset=None, top10_metric="cantidad")
        assert context_before["total_asignados"] == 1

        form = DevolucionForm(data={
            'condicion_fisica': 'OK',
            'estado_llegada': 'bueno',
            'generar_acta': '',
        })
        assert form.is_valid()
        TrazabilidadService.devolver(disp, form)

        qs = Dispositivo.objects.all()
        context_after = DashboardMetricsService.build_context(qs, filterset=None, top10_metric="cantidad")
        assert context_after["total_disponibles"] == 1
        assert context_after["total_asignados"] == 0


@pytest.mark.integration
@pytest.mark.django_db
class TestFolioSequence:
    """Verificar que los folios de actas son secuenciales y únicos."""

    def test_folios_are_sequential(self):
        """Crear 5 actas consecutivas genera folios incrementales."""
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()

        folios = []
        for i in range(5):
            h = HistorialAsignacionFactory(colaborador=colaborador, acta=None)
            acta = ActaService.crear_acta(
                colaborador=colaborador,
                tipo_acta="ENTREGA",
                asignacion_ids=[h.pk],
                creado_por=creado_por,
            )
            folios.append(acta.folio)

        numeros = [int(f.split("-")[-1]) for f in folios]
        assert numeros == [1, 2, 3, 4, 5]

    def test_folios_are_unique(self):
        """No hay folios duplicados."""
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()

        folios = set()
        for _ in range(10):
            h = HistorialAsignacionFactory(colaborador=colaborador, acta=None)
            acta = ActaService.crear_acta(
                colaborador=colaborador,
                tipo_acta="ENTREGA",
                asignacion_ids=[h.pk],
                creado_por=creado_por,
            )
            assert acta.folio not in folios
            folios.add(acta.folio)
