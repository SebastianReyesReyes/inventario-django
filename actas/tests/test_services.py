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


class TestActaPDFService:
    """Tests unitarios para ActaPDFService (feature flag de PDF engine)."""

    @pytest.fixture
    def acta_para_pdf(self, db):
        """Crea un acta con relaciones completas para pruebas de PDF."""
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        acta = ActaFactory(
            colaborador=colaborador,
            creado_por=creado_por,
            tipo_acta='ENTREGA',
        )
        HistorialAsignacionFactory(acta=acta, colaborador=colaborador)
        return acta

    def test_defaults_to_xhtml2pdf(self, acta_para_pdf, settings):
        """Verifica que el engine por defecto es xhtml2pdf."""
        settings.PDF_ENGINE = 'xhtml2pdf'
        from actas.services import ActaPDFService
        pdf = ActaPDFService.generar_pdf(acta_para_pdf)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 0

    def test_xhtml2pdf_delegates_to_acta_service(self, acta_para_pdf, monkeypatch, settings):
        """Verifica que el engine xhtml2pdf delega en ActaService.generar_pdf()."""
        from actas.services import ActaPDFService, ActaService
        
        called = []
        def spy(*args, **kwargs):
            called.append(True)
            return b'fake-pdf'
        monkeypatch.setattr(ActaService, 'generar_pdf', spy)
        settings.PDF_ENGINE = 'xhtml2pdf'

        ActaPDFService.generar_pdf(acta_para_pdf)

        assert len(called) == 1

    def test_both_mode_returns_dict(self, acta_para_pdf, monkeypatch, settings):
        """Verifica que 'both' devuelve un dict con ambos PDFs."""
        from actas.services import ActaPDFService
        monkeypatch.setattr(ActaPDFService, '_playwright', lambda acta: b'playwright-pdf')
        monkeypatch.setattr(ActaPDFService, '_xhtml2pdf', lambda acta: b'xhtml2pdf-pdf')
        settings.PDF_ENGINE = 'both'

        result = ActaPDFService.generar_pdf(acta_para_pdf)

        assert isinstance(result, dict)
        assert result == {'xhtml2pdf': b'xhtml2pdf-pdf', 'playwright': b'playwright-pdf'}

    def test_playwright_generates_pdf(self, acta_para_pdf, monkeypatch, settings):
        """Verifica que el engine playwright genera un PDF binario."""
        from actas.services import ActaPDFService
        monkeypatch.setattr(ActaPDFService, '_playwright', lambda acta: b'playwright-output')
        settings.PDF_ENGINE = 'playwright'

        pdf = ActaPDFService.generar_pdf(acta_para_pdf)

        assert pdf == b'playwright-output'

    def test_playwright_fallback_on_error(self, acta_para_pdf, monkeypatch, settings):
        """Verifica que si Playwright falla, se revierte a xhtml2pdf."""
        from actas.services import ActaPDFService
        monkeypatch.setattr(ActaPDFService, '_xhtml2pdf', lambda acta: b'fallback-pdf')
        monkeypatch.setattr(
            ActaPDFService, '_playwright',
            lambda acta: (_ for _ in ()).throw(RuntimeError('Browser crash'))
        )
        settings.PDF_ENGINE = 'playwright'

        pdf = ActaPDFService.generar_pdf(acta_para_pdf)

        assert pdf == b'fallback-pdf'

    def test_engine_param_overrides_setting(self, acta_para_pdf, monkeypatch, settings):
        """Verifica que el parámetro engine sobrescribe settings.PDF_ENGINE."""
        settings.PDF_ENGINE = 'playwright'
        from actas.services import ActaPDFService, ActaService

        called = []
        monkeypatch.setattr(ActaService, 'generar_pdf', lambda acta: called.append(True) or b'ok')

        ActaPDFService.generar_pdf(acta_para_pdf, engine='xhtml2pdf')

        assert len(called) == 1

    def test_no_acta_instance_leaks(self, acta_para_pdf, settings):
        """Verifica que generar_pdf() no crea ni modifica actas en BD."""
        initial_count = Acta.objects.count()
        settings.PDF_ENGINE = 'xhtml2pdf'
        from actas.services import ActaPDFService

        ActaPDFService.generar_pdf(acta_para_pdf)

        assert Acta.objects.count() == initial_count


class TestPlaywrightBrowserPool:
    """Tests unitarios para el pool de Chromium."""

    def setup_method(self):
        """Limpia el pool antes de cada test."""
        from actas.playwright_browser import shutdown_pool
        shutdown_pool()

    def teardown_method(self):
        """Limpia el pool después de cada test."""
        from actas.playwright_browser import shutdown_pool
        shutdown_pool()

    def test_get_browser_returns_playwright_browser(self):
        """Verifica que get_browser() devuelve una instancia de Chromium usable."""
        from actas.playwright_browser import get_browser
        browser = get_browser()
        assert browser is not None
        page = browser.new_page()
        page.close()
        assert browser.is_connected()

    def test_browser_reuse_same_instance(self):
        """Verifica que la misma instancia se reusa en llamadas sucesivas."""
        from actas.playwright_browser import get_browser, _browser_pool
        b1 = get_browser()
        b2 = get_browser()
        assert b1 is b2
        assert len(_browser_pool) == 1

    def test_shutdown_pool_clears_all(self):
        """Verifica que shutdown_pool() cierra todas las instancias y vacía el pool."""
        from actas.playwright_browser import get_browser, shutdown_pool, _browser_pool

        b1 = get_browser()
        assert len(_browser_pool) == 1
        assert b1.is_connected()

        shutdown_pool()

        assert len(_browser_pool) == 0
        assert not b1.is_connected()
