import pytest
from django.core.exceptions import ValidationError
from actas.services import ActaService
from actas.models import Acta
from dispositivos.models import HistorialAsignacion, EntregaAccesorio
from core.tests.factories import (
    ColaboradorFactory, HistorialAsignacionFactory, 
    EntregaAccesorioFactory, ActaFactory
)

@pytest.mark.django_db
class TestActaService:
    def test_crear_acta_success(self):
        """Verificar creación exitosa de acta vinculando asignaciones"""
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        h1 = HistorialAsignacionFactory(colaborador=colaborador, acta=None)
        h2 = HistorialAsignacionFactory(colaborador=colaborador, acta=None)
        
        acta = ActaService.crear_acta(
            colaborador=colaborador,
            tipo_acta='ENTREGA',
            asignacion_ids=[h1.pk, h2.pk],
            creado_por=creado_por
        )
        
        assert isinstance(acta, Acta)
        assert acta.colaborador == colaborador
        assert h1 in acta.asignaciones.all()
        
        h1.refresh_from_db()
        assert h1.acta == acta

    def test_crear_acta_con_accesorios(self):
        """Verificar que el acta vincula también accesorios seleccionados"""
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        h1 = HistorialAsignacionFactory(colaborador=colaborador)
        acc1 = EntregaAccesorioFactory(colaborador=colaborador)
        
        acta = ActaService.crear_acta(
            colaborador=colaborador,
            tipo_acta='ENTREGA',
            asignacion_ids=[h1.pk],
            creado_por=creado_por,
            accesorio_ids=[acc1.pk]
        )
        
        assert acc1 in acta.accesorios.all()
        acc1.refresh_from_db()
        assert acc1.acta == acta

    def test_crear_acta_no_asignaciones_raises_error(self):
        """Verificar que falla si no se envían IDs de asignación"""
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        
        with pytest.raises(ValidationError, match="Debe seleccionar al menos una asignación"):
            ActaService.crear_acta(colaborador, 'ENTREGA', [], creado_por)

    def test_crear_acta_wrong_owner_raises_error(self):
        """Verificar que falla si las asignaciones no pertenecen al colaborador"""
        colaborador = ColaboradorFactory()
        otro_colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        h1 = HistorialAsignacionFactory(colaborador=otro_colaborador)
        
        with pytest.raises(ValidationError, match="no pertenecen al colaborador"):
            ActaService.crear_acta(colaborador, 'ENTREGA', [h1.pk], creado_por)

    def test_firmar_acta(self):
        """Verificar que se puede firmar un acta y queda bloqueada"""
        acta = ActaFactory(firmada=False)
        result = ActaService.firmar_acta(acta.pk)
        
        assert result is True
        acta.refresh_from_db()
        assert acta.firmada is True
        
        # Intentar firmar de nuevo falla
        with pytest.raises(ValidationError, match="El acta ya está firmada"):
            ActaService.firmar_acta(acta.pk)

    def test_obtener_pendientes(self):
        """Verificar que solo obtiene asignaciones sin acta y vigentes"""
        colaborador = ColaboradorFactory()
        h_pendiente = HistorialAsignacionFactory(colaborador=colaborador, acta=None, fecha_fin=None)
        h_con_acta = HistorialAsignacionFactory(colaborador=colaborador, acta=ActaFactory())
        
        pendientes = ActaService.obtener_pendientes(colaborador.pk)
        assert h_pendiente in pendientes
        assert h_con_acta not in pendientes
    def test_generar_pdf(self):
        """Verificar que el servicio genera contenido PDF sin errores"""
        acta = ActaFactory()
        # Necesitamos que tenga al menos una asignación para que el PDF no esté vacío/falle
        HistorialAsignacionFactory(acta=acta)

        # El servicio usa select_related internamente, así que pasamos el objeto
        pdf_content = ActaService.generar_pdf(acta)

        assert isinstance(pdf_content, bytes)
        assert len(pdf_content) > 0
        # Los PDFs suelen empezar con %PDF
        assert pdf_content.startswith(b"%PDF")

    def test_generar_preview_html_success(self):
        """Verificar que genera HTML preview sin persistir en BD"""
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        h1 = HistorialAsignacionFactory(colaborador=colaborador, acta=None)

        html = ActaService.generar_preview_html(
            colaborador=colaborador,
            tipo_acta='ENTREGA',
            asignacion_ids=[h1.pk],
            creado_por=creado_por,
            observaciones='Test preview',
        )

        assert isinstance(html, str)
        assert len(html) > 0
        # Debe contener datos del colaborador y el equipo
        assert colaborador.nombre_completo in html
        assert str(h1.dispositivo.numero_serie) in html
        # Debe marcar como preliminar
        assert 'PRELIMINAR' in html or 'PENDIENTE' in html
        # No debe haberse creado ningún acta en BD
        assert Acta.objects.count() == 0

    def test_generar_preview_html_con_accesorios(self):
        """Verificar que el preview incluye accesorios seleccionados"""
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        h1 = HistorialAsignacionFactory(colaborador=colaborador, acta=None)
        acc1 = EntregaAccesorioFactory(colaborador=colaborador, tipo='Mouse')

        html = ActaService.generar_preview_html(
            colaborador=colaborador,
            tipo_acta='ENTREGA',
            asignacion_ids=[h1.pk],
            creado_por=creado_por,
            accesorio_ids=[acc1.pk],
        )

        assert 'Mouse' in html
        assert Acta.objects.count() == 0

    def test_generar_preview_html_sin_asignaciones_raises_error(self):
        """Verificar que falla si no se envían IDs de asignación"""
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()

        with pytest.raises(ValidationError, match="Debe seleccionar al menos una asignación"):
            ActaService.generar_preview_html(colaborador, 'ENTREGA', [], creado_por)

    def test_generar_preview_html_asignaciones_no_disponibles_raises_error(self):
        """Verificar que falla si las asignaciones ya no están disponibles"""
        colaborador = ColaboradorFactory()
        otro_colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        h1 = HistorialAsignacionFactory(colaborador=otro_colaborador)

        with pytest.raises(ValidationError, match="no pertenecen al colaborador"):
            ActaService.generar_preview_html(colaborador, 'ENTREGA', [h1.pk], creado_por)

    def test_generar_preview_html_no_crea_acta_ni_vincula(self):
        """Verificar que el preview no vincula asignaciones a ningún acta"""
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        h1 = HistorialAsignacionFactory(colaborador=colaborador, acta=None)

        ActaService.generar_preview_html(
            colaborador=colaborador,
            tipo_acta='ENTREGA',
            asignacion_ids=[h1.pk],
            creado_por=creado_por,
        )

        h1.refresh_from_db()
        assert h1.acta is None
        assert Acta.objects.count() == 0
