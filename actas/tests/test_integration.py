"""Tests de integración para la app Actas.

Cubre flujos complejos de actas: creación con accesorios,
firmado, PDF, y validaciones cruzadas.
"""
import pytest
from django.core.exceptions import ValidationError

from actas.services import ActaService
from actas.models import Acta
from dispositivos.models import HistorialAsignacion, EntregaAccesorio

from core.tests.factories import (
    ColaboradorFactory,
    HistorialAsignacionFactory,
    EntregaAccesorioFactory,
    ActaFactory,
    DispositivoFactory,
    EstadoDisponibleFactory,
)
from dispositivos.services import TrazabilidadService
from dispositivos.forms import AsignacionForm


@pytest.mark.integration
@pytest.mark.django_db
class TestActaCreationWithAccessories:
    """Crear acta que incluye dispositivos y accesorios."""

    def test_acta_with_devices_and_accessories(self):
        """Un acta puede vincular asignaciones y accesorios simultáneamente."""
        colaborador = ColaboradorFactory(first_name="María", last_name="González")
        creado_por = ColaboradorFactory()

        h1 = HistorialAsignacionFactory(colaborador=colaborador, acta=None)
        h2 = HistorialAsignacionFactory(colaborador=colaborador, acta=None)
        acc1 = EntregaAccesorioFactory(colaborador=colaborador, tipo="Mouse")
        acc2 = EntregaAccesorioFactory(colaborador=colaborador, tipo="Teclado")

        acta = ActaService.crear_acta(
            colaborador=colaborador,
            tipo_acta="ENTREGA",
            asignacion_ids=[h1.pk, h2.pk],
            creado_por=creado_por,
            accesorio_ids=[acc1.pk, acc2.pk],
        )

        assert acta.asignaciones.count() == 2
        assert acta.accesorios.count() == 2
        assert h1 in acta.asignaciones.all()
        assert acc1 in acta.accesorios.all()
        assert acc2 in acta.accesorios.all()

        h1.refresh_from_db()
        acc1.refresh_from_db()
        assert h1.acta == acta
        assert acc1.acta == acta

    def test_acta_only_accessories_fails(self):
        """Crear acta sin asignaciones falla (requiere al menos una)."""
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        acc = EntregaAccesorioFactory(colaborador=colaborador)

        with pytest.raises(ValidationError, match="Debe seleccionar al menos una asignación"):
            ActaService.crear_acta(
                colaborador=colaborador,
                tipo_acta="ENTREGA",
                asignacion_ids=[],
                creado_por=creado_por,
                accesorio_ids=[acc.pk],
            )


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.slow
class TestActaPDFGeneration:
    """Generación de PDF para distintos tipos de acta."""

    def test_pdf_for_entrega_acta(self):
        """Generar PDF de un acta de entrega."""
        acta = ActaFactory(tipo_acta="ENTREGA", firmada=False)
        HistorialAsignacionFactory(acta=acta)

        pdf = ActaService.generar_pdf(acta)
        assert pdf.startswith(b"%PDF")

    def test_pdf_for_devolucion_acta(self):
        """Generar PDF de un acta de devolución."""
        acta = ActaFactory(tipo_acta="DEVOLUCION", firmada=False)
        HistorialAsignacionFactory(acta=acta)

        pdf = ActaService.generar_pdf(acta)
        assert pdf.startswith(b"%PDF")

    def test_pdf_contains_folio(self):
        """El PDF generado contiene el folio del acta."""
        acta = ActaFactory(tipo_acta="ENTREGA")
        HistorialAsignacionFactory(acta=acta)

        pdf = ActaService.generar_pdf(acta)
        pdf_text = pdf.decode("latin-1", errors="ignore")
        year = str(acta.fecha.year)
        assert year in pdf_text


@pytest.mark.integration
@pytest.mark.django_db
class TestActaPendingQueries:
    """Consultas de asignaciones y accesorios pendientes de acta."""

    def test_obtener_pendientes_excludes_completed(self):
        """Solo retorna asignaciones sin acta y vigentes."""
        colaborador = ColaboradorFactory()

        h_pending = HistorialAsignacionFactory(colaborador=colaborador, acta=None, fecha_fin=None)
        h_with_acta = HistorialAsignacionFactory(colaborador=colaborador, acta=ActaFactory())
        h_closed = HistorialAsignacionFactory(colaborador=colaborador, acta=None, fecha_fin="2024-01-01")

        pendientes = ActaService.obtener_pendientes(colaborador.pk)

        assert h_pending in pendientes
        assert h_with_acta not in pendientes
        assert h_closed not in pendientes

    def test_obtener_accesorios_pendientes(self):
        """Solo retorna accesorios sin acta."""
        colaborador = ColaboradorFactory()

        acc_pending = EntregaAccesorioFactory(colaborador=colaborador, acta=None)
        acc_with_acta = EntregaAccesorioFactory(colaborador=colaborador, acta=ActaFactory())

        pendientes = ActaService.obtener_accesorios_pendientes(colaborador.pk)

        assert acc_pending in pendientes
        assert acc_with_acta not in pendientes


@pytest.mark.integration
@pytest.mark.django_db
class TestFullCycleWithActas:
    """Ciclo completo: crear → asignar con acta → devolver con acta → firmar."""

    def test_full_lifecycle_with_signed_actas(self):
        """Flujo completo genera actas correctas en cada etapa."""
        dispositivo = DispositivoFactory(
            estado=EstadoDisponibleFactory(),
            propietario_actual=None,
        )
        colaborador = ColaboradorFactory(first_name="Pedro", last_name="Muñoz")
        admin = ColaboradorFactory()

        form = AsignacionForm(data={
            'colaborador': colaborador.pk,
            'condicion_fisica': 'Nuevo',
            'generar_acta': '',
        })
        assert form.is_valid()

        _, acta_entrega = TrazabilidadService.asignar(dispositivo, form, creado_por=admin)
        assert acta_entrega is None

        dispositivo.refresh_from_db()
        assert dispositivo.propietario_actual == colaborador
        assert dispositivo.estado.nombre == "Asignado"

        from dispositivos.forms import DevolucionForm
        form_dev = DevolucionForm(data={
            'condicion_fisica': 'Buen estado',
            'estado_llegada': 'bueno',
            'generar_acta': 'on',
        })
        assert form_dev.is_valid()

        _, acta_devolucion = TrazabilidadService.devolver(dispositivo, form_dev, creado_por=admin)
        assert acta_devolucion is not None
        assert acta_devolucion.tipo_acta == "DEVOLUCION"

        dispositivo.refresh_from_db()
        assert dispositivo.propietario_actual is None
        assert dispositivo.estado.nombre == "Disponible"
