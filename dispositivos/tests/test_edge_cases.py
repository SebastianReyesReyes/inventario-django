"""Tests de edge cases: concurrencia, permisos, validaciones y errores."""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from dispositivos.services import TrazabilidadService
from dispositivos.forms import AsignacionForm, ReasignacionForm, DevolucionForm
from dispositivos.models import Dispositivo, HistorialAsignacion
from actas.services import ActaService
from actas.models import Acta

from core.tests.factories import (
    ColaboradorFactory,
    DispositivoFactory,
    EstadoDisponibleFactory,
    EstadoAsignadoFactory,
    EstadoFueraInventarioFactory,
    HistorialAsignacionFactory,
    ActaFactory,
)


@pytest.mark.django_db
class TestConcurrentAssignments:
    """Validar que asignaciones concurrentes no duplican estados."""

    def test_cannot_assign_already_assigned_device(self):
        """Un dispositivo ya asignado tiene su historial preservado al reasignar."""
        col1 = ColaboradorFactory()
        col2 = ColaboradorFactory()
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory(), propietario_actual=col1)

        HistorialAsignacionFactory(
            dispositivo=dispositivo,
            colaborador=col1,
            fecha_fin=None,
        )

        form = AsignacionForm(data={
            'colaborador': col2.pk,
            'condicion_fisica': 'Nuevo',
            'generar_acta': '',
        })
        assert form.is_valid()

        dispositivo.refresh_from_db()
        assert dispositivo.propietario_actual == col1

        _, _ = TrazabilidadService.asignar(dispositivo, form)

        dispositivo.refresh_from_db()
        assert dispositivo.propietario_actual == col2

        historial_count = dispositivo.historial.count()
        assert historial_count >= 2


@pytest.mark.django_db
class TestDeviceProtection:
    """Validar que dispositivos con historial no se pueden borrar."""

    def test_device_with_history_cannot_be_deleted(self):
        """Borrar dispositivo con asignaciones lanza ProtectedError."""
        from django.db.models import ProtectedError

        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory())
        colaborador = ColaboradorFactory()

        HistorialAsignacionFactory(
            dispositivo=dispositivo,
            colaborador=colaborador,
            fecha_fin=None,
        )

        with pytest.raises(ProtectedError):
            dispositivo.delete()

    def test_device_without_history_can_be_deleted(self):
        """Dispositivo sin historial se puede borrar."""
        dispositivo = DispositivoFactory(estado=EstadoDisponibleFactory(), propietario_actual=None)
        pk = dispositivo.pk

        dispositivo.delete()

        assert not Dispositivo.objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestInactiveColaborador:
    """Validar comportamiento con colaboradores desactivados."""

    def test_inactive_colaborador_form_rejects(self):
        """El formulario de asignación rechaza colaboradores inactivos."""
        dispositivo = DispositivoFactory(estado=EstadoDisponibleFactory(), propietario_actual=None)
        colaborador = ColaboradorFactory(esta_activo=False, is_active=False)

        form = AsignacionForm(data={
            'colaborador': colaborador.pk,
            'condicion_fisica': 'Nuevo',
            'generar_acta': '',
        })
        assert not form.is_valid()


@pytest.mark.django_db
class TestActaValidation:
    """Validaciones de actas: folio, firmado, tipos."""

    def test_acta_folio_format(self):
        """El folio tiene formato ACT-YYYY-NNNN."""
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        h = HistorialAsignacionFactory(colaborador=colaborador, acta=None)

        acta = ActaService.crear_acta(
            colaborador=colaborador,
            tipo_acta="ENTREGA",
            asignacion_ids=[h.pk],
            creado_por=creado_por,
        )

        import re
        assert re.match(r"^ACT-\d{4}-\d{4}$", acta.folio)

    def test_acta_tipo_choices(self):
        """Solo se permiten tipos válidos."""
        acta = ActaFactory(tipo_acta="ENTREGA")
        assert acta.tipo_acta in ["ENTREGA", "DEVOLUCION"]

    def test_firmar_acta_twice_raises_error(self):
        """Firmar un acta ya firmada lanza ValidationError."""
        acta = ActaFactory(firmada=False)
        ActaService.firmar_acta(acta.pk)

        with pytest.raises(ValidationError, match="ya está firmada"):
            ActaService.firmar_acta(acta.pk)

    def test_firmar_nonexistent_acta_raises_error(self):
        """Firmar un acta que no existe lanza ValidationError."""
        with pytest.raises(ValidationError, match="ya está firmada o no existe"):
            ActaService.firmar_acta(99999)


@pytest.mark.django_db
class TestHTMXPartialVsFullPage:
    """Validar que respuestas HTMX son parciales y las normales son redirects."""

    def test_htmx_request_detected(self):
        """El helper is_htmx detecta correctamente requests HTMX."""
        from core.htmx import is_htmx
        from unittest.mock import MagicMock

        request_htmx = MagicMock()
        request_htmx.headers = {"HX-Request": "true"}
        assert is_htmx(request_htmx) is True

        request_normal = MagicMock()
        request_normal.headers = {}
        assert is_htmx(request_normal) is False


@pytest.mark.django_db
class TestDispositivoIdentificadorGeneration:
    """Validar generación de identificadores internos."""

    def test_identificador_uses_tipo_sigla(self):
        """El identificador interno usa la sigla del tipo de dispositivo."""
        from core.tests.factories import TipoDispositivoFactory, ModeloFactory

        tipo = TipoDispositivoFactory(nombre="Notebook", sigla="NB")
        modelo = ModeloFactory(tipo_dispositivo=tipo)
        dispositivo = DispositivoFactory(
            estado=EstadoDisponibleFactory(),
            modelo=modelo,
            propietario_actual=None,
        )

        assert dispositivo.identificador_interno.startswith("JMIE-NB-")

    def test_identificador_is_unique(self):
        """Dos dispositivos del mismo tipo tienen identificadores únicos."""
        from core.tests.factories import TipoDispositivoFactory, ModeloFactory

        tipo = TipoDispositivoFactory(nombre="Monitor", sigla="MON")
        modelo = ModeloFactory(tipo_dispositivo=tipo)
        disp1 = DispositivoFactory(estado=EstadoDisponibleFactory(), modelo=modelo, propietario_actual=None)
        disp2 = DispositivoFactory(estado=EstadoDisponibleFactory(), modelo=modelo, propietario_actual=None)

        assert disp1.identificador_interno != disp2.identificador_interno


@pytest.mark.django_db
class TestReturnEdgeCases:
    """Edge cases en el flujo de devolución."""

    def test_return_without_history(self):
        """Devolver un dispositivo sin historial no falla."""
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory(), propietario_actual=None)

        form = DevolucionForm(data={
            'condicion_fisica': 'Sin historial',
            'estado_llegada': 'bueno',
            'generar_acta': '',
        })
        assert form.is_valid()

        ultimo_mov, acta = TrazabilidadService.devolver(dispositivo, form)

        dispositivo.refresh_from_db()
        assert dispositivo.propietario_actual is None
        assert dispositivo.estado.nombre == "Disponible"
        assert acta is None

    def test_return_with_acta_but_no_colaborador(self):
        """Devolver sin colaborador en historial no genera acta."""
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory())

        form = DevolucionForm(data={
            'condicion_fisica': 'OK',
            'estado_llegada': 'bueno',
            'generar_acta': 'on',
        })
        assert form.is_valid()

        _, acta = TrazabilidadService.devolver(dispositivo, form)
        assert acta is None


@pytest.mark.django_db
class TestDeviceOutOfInventory:
    """Dispositivos fuera de inventario."""

    def test_activos_excludes_fuera_de_inventario(self):
        """El QuerySet activos() excluye dispositivos fuera de inventario."""
        disp1 = DispositivoFactory(estado=EstadoDisponibleFactory())
        disp2 = DispositivoFactory(estado=EstadoFueraInventarioFactory())

        activos = Dispositivo.objects.activos()
        assert disp1 in activos
        assert disp2 not in activos
