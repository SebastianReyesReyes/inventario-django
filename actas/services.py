"""
Capa de servicios para la app Actas.

Contiene toda la lógica de negocio separada de las vistas (HTTP) y los modelos (persistencia).
Siguiendo el patrón Service Layer recomendado por django-patterns skill.
"""
import logging

from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Acta
from dispositivos.models import HistorialAsignacion


class ActaService:
    """Servicio principal para la gestión de actas legales."""

    @staticmethod
    @transaction.atomic
    def crear_acta(colaborador, tipo_acta, asignacion_ids, creado_por, observaciones=None, accesorio_ids=None, metodo_sanitizacion='N/A', ministro_de_fe=None):
        """
        Crea un acta nueva y vincula las asignaciones seleccionadas.

        Args:
            colaborador: Instancia de Colaborador destinatario del acta.
            tipo_acta: Tipo de documento ('ENTREGA' o 'DEVOLUCION').
            asignacion_ids: Lista de PKs de HistorialAsignacion a vincular.
            creado_por: Instancia de Colaborador (usuario autenticado) que genera el acta.
            observaciones: Texto libre opcional.

        Returns:
            Acta: La instancia del acta creada.

        Raises:
            ValidationError: Si no se seleccionan asignaciones o ninguna es válida.
        """
        if not asignacion_ids:
            raise ValidationError("Debe seleccionar al menos una asignación.")

        from django.db import IntegrityError
        
        # Intentar crear el acta manejando posibles colisiones de folio (race conditions)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                acta = Acta(
                    colaborador=colaborador,
                    tipo_acta=tipo_acta,
                    creado_por=creado_por,
                    observaciones=observaciones or '',
                    metodo_sanitizacion=metodo_sanitizacion,
                    ministro_de_fe=ministro_de_fe,
                )
                acta.save()
                break # Éxito
            except IntegrityError:
                if attempt == max_retries - 1:
                    raise ValidationError("Error crítico: No se pudo generar un folio único tras varios intentos. Reintente.")
                continue # Reintentar (el save() buscará un nuevo folio al no tener pk)

        # Vincular solo asignaciones que pertenezcan al colaborador y estén sin acta
        updated = HistorialAsignacion.objects.filter(
            pk__in=asignacion_ids,
            colaborador=colaborador,
            acta__isnull=True,
        ).update(acta=acta)

        if updated == 0:
            raise ValidationError(
                "Las asignaciones seleccionadas ya no están disponibles "
                "o no pertenecen al colaborador."
            )

        # Vincular accesorios si existen
        if accesorio_ids:
            from dispositivos.models import EntregaAccesorio
            EntregaAccesorio.objects.filter(
                pk__in=accesorio_ids,
                colaborador=colaborador,
                acta__isnull=True
            ).update(acta=acta)

        return acta

    @staticmethod
    def firmar_acta(acta_pk):
        """
        Marca un acta como firmada (blindaje legal).

        Args:
            acta_pk: PK del acta a firmar.

        Returns:
            bool: True si se firmó correctamente.

        Raises:
            ValidationError: Si el acta ya estaba firmada o no existe.
        """
        updated = Acta.objects.filter(pk=acta_pk, firmada=False).update(firmada=True)
        if not updated:
            raise ValidationError("El acta ya está firmada o no existe.")
        return True

    @staticmethod
    def obtener_acta_con_relaciones(acta_pk):
        """
        Obtiene un acta con todas sus relaciones cargadas para evitar N+1.

        Args:
            acta_pk: PK del acta.

        Returns:
            tuple: (acta, asignaciones_queryset)
        """
        acta = Acta.objects.select_related(
            'colaborador__centro_costo',
            'colaborador__departamento',
            'creado_por',
            'ministro_de_fe',
        ).prefetch_related(
            'asignaciones__dispositivo__modelo__tipo_dispositivo',
            'asignaciones__dispositivo__modelo__fabricante',
            'accesorios',
        ).get(pk=acta_pk)

        return acta, acta.asignaciones.all()

    @staticmethod
    def obtener_asignaciones_para_pdf(acta):
        """
        Obtiene las asignaciones optimizadas para renderizado PDF.

        Args:
            acta: Instancia de Acta.

        Returns:
            QuerySet de HistorialAsignacion.
        """
        return HistorialAsignacion.objects.filter(acta=acta).select_related(
            'dispositivo__modelo__tipo_dispositivo',
            'dispositivo__modelo__fabricante',
            'dispositivo__modelo',
        )

    @staticmethod
    def generar_pdf(acta):
        """
        Genera el contenido binario del PDF corporativo para un acta persistida.

        Delega en ActaPDFService._playwright() para mantener compatibilidad
        con código legacy que llama a este método directamente.

        Args:
            acta: Instancia de Acta (debe tener relaciones cargadas).

        Returns:
            bytes: El contenido del PDF generado.
        """
        return ActaPDFService._playwright(acta)

    @staticmethod
    def generar_preview_pdf(colaborador, tipo_acta, asignacion_ids, creado_por,
                             observaciones=None, accesorio_ids=None, ministro_de_fe=None):
        """
        Genera un PDF de preview (sin persistir) delegando en ActaPDFService.

        Args:
            colaborador, tipo_acta, asignacion_ids, creado_por: mismos que generar_preview_html.
            observaciones, accesorio_ids, ministro_de_fe: opcionales.

        Returns:
            bytes: Contenido binario del PDF.
        """
        return ActaPDFService.generar_preview_pdf(
            colaborador, tipo_acta, asignacion_ids, creado_por,
            observaciones, accesorio_ids, ministro_de_fe,
        )

    @staticmethod
    def generar_preview_html(colaborador, tipo_acta, asignacion_ids, creado_por,
                              observaciones=None, accesorio_ids=None, ministro_de_fe=None):
        """
        Construye el contexto completo para renderizar la vista previa del acta
        SIN persistir en base de datos.

        Args:
            colaborador: Instancia de Colaborador destinatario.
            tipo_acta: Tipo de documento ('ENTREGA' o 'DEVOLUCION').
            asignacion_ids: Lista de PKs de HistorialAsignacion a mostrar.
            creado_por: Instancia de Colaborador que genera el preview.
            observaciones: Texto libre opcional.
            accesorio_ids: Lista de PKs de EntregaAccesorio opcional.
            ministro_de_fe: Instancia de Colaborador opcional.

        Returns:
            str: HTML renderizado del acta en modo preview.

        Raises:
            ValidationError: Si no se seleccionan asignaciones o no son válidas.
        """
        if not asignacion_ids:
            raise ValidationError("Debe seleccionar al menos una asignación.")

        from dispositivos.models import HistorialAsignacion, EntregaAccesorio

        asignaciones = HistorialAsignacion.objects.filter(
            pk__in=asignacion_ids,
            colaborador=colaborador,
            acta__isnull=True,
        ).select_related(
            'dispositivo__modelo__tipo_dispositivo',
            'dispositivo__modelo__fabricante',
            'dispositivo__modelo',
        )

        if not asignaciones.exists():
            raise ValidationError(
                "Las asignaciones seleccionadas ya no están disponibles "
                "o no pertenecen al colaborador."
            )

        accesorios = []
        if accesorio_ids:
            accesorios = list(EntregaAccesorio.objects.filter(
                pk__in=accesorio_ids,
                colaborador=colaborador,
                acta__isnull=True
            ))

        # Construir un "acta fantasma" (unsaved) para el template
        acta_preview = Acta(
            colaborador=colaborador,
            tipo_acta=tipo_acta,
            creado_por=creado_por,
            observaciones=observaciones or '',
            ministro_de_fe=ministro_de_fe,
            fecha=timezone.now(),
        )
        acta_preview.folio = f"ACT-{timezone.now().year}-PENDIENTE"

        from django.templatetags.static import static
        logo_path = static('img/LogoColor.png')

        context = {
            'acta': acta_preview,
            'asignaciones': asignaciones,
            'accesorios': accesorios,
            'logo_path': logo_path,
            'fecha_actual': timezone.now(),
            'preview': True,
        }

        return render_to_string('actas/partials/acta_preview_content.html', context)

    @staticmethod
    def obtener_pendientes(colaborador_pk):
        """
        Retorna las asignaciones activas sin acta de un colaborador.

        Args:
            colaborador_pk: PK del colaborador.

        Returns:
            QuerySet de HistorialAsignacion.
        """
        return HistorialAsignacion.objects.filter(
            colaborador_id=colaborador_pk,
            acta__isnull=True,
            fecha_fin__isnull=True,
        ).select_related(
            'dispositivo__modelo__tipo_dispositivo',
            'dispositivo__modelo__fabricante',
        )

    @staticmethod
    def obtener_accesorios_pendientes(colaborador_pk):
        """Retorna accesorios entregados sin acta."""
        from dispositivos.models import EntregaAccesorio
        return EntregaAccesorio.objects.filter(
            colaborador_id=colaborador_pk,
            acta__isnull=True
        )


class ActaPDFService:
    """
    Servicio de generación de PDFs de actas usando Playwright/Chromium headless.

    El motor por defecto es Playwright (CSS moderno, pixel-perfect).
    El parámetro PDF_ENGINE en settings permite compatibilidad con código
    que aún referencia valores legacy ('xhtml2pdf', 'both'), en cuyo caso
    se usa Playwright en todos los casos.
    """

    _logger = logging.getLogger('actas')

    @staticmethod
    def generar_pdf(acta, engine=None):
        """
        Punto de entrada único para generación de PDF.

        Args:
            acta: Instancia de Acta con relaciones cargadas.
            engine: Ignorado (mantenido por compatibilidad). Siempre usa Playwright.

        Returns:
            bytes: PDF binario.
        """
        return ActaPDFService._playwright(acta)

    @staticmethod
    def generar_pdf_con_info(acta, engine=None):
        """
        Igual que generar_pdf() pero retorna también el motor real usado.

        Returns:
            tuple: (bytes, str) — PDF binario y motor real ('playwright')
        """
        return ActaPDFService._playwright(acta), 'playwright'

    @staticmethod
    def _xhtml2pdf(acta):
        """[DEPRECATED] Shim de compatibilidad — delega en Playwright."""
        return ActaPDFService._playwright(acta)

    @staticmethod
    def _encode_logo_to_base64(logo_path):
        """Convierte el logo a data URI base64 para embedding en HTML."""
        if not logo_path:
            return None
        try:
            import base64
            import mimetypes
            mime, _ = mimetypes.guess_type(logo_path)
            with open(logo_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode('ascii')
            return f"data:{mime or 'image/png'};base64,{data}"
        except Exception as e:
            ActaPDFService._logger.warning(f"No se pudo codificar logo a base64: {e}")
            return None

    @staticmethod
    def _playwright(acta, asignaciones=None, accesorios=None):
        """Genera PDF usando Playwright/Chromium headless (ejecutado en un thread separado).

        Usa el mismo HTML que la vista previa (acta_preview_content.html) para que
        el PDF sea pixel-perfect con lo que el usuario ve en el navegador.
        """
        from django.template.loader import render_to_string
        import concurrent.futures
        from django.conf import settings

        if asignaciones is None:
            asignaciones = ActaService.obtener_asignaciones_para_pdf(acta)
        if accesorios is None:
            accesorios = acta.accesorios.all()
        logo_path = finders.find('img/LogoColor.png')

        # Playwright: embedder logo como base64 para evitar problemas de rutas/URLs
        logo_data_uri = ActaPDFService._encode_logo_to_base64(logo_path)

        # Renderizar el mismo HTML que la preview, pero sin watermark (pdf_mode=True)
        preview_html = render_to_string('actas/partials/acta_preview_content.html', {
            'acta': acta,
            'asignaciones': asignaciones,
            'accesorios': accesorios,
            'logo_path': logo_data_uri,
            'fecha_actual': timezone.now(),
            'pdf_mode': True,
        })

        # Wrap en HTML completo para Playwright
        html = render_to_string('actas/playwright/pdf_wrapper.html', {
            'preview_html': preview_html,
        })

        ActaPDFService._logger.info(
            f"Iniciando generación Playwright para acta {acta.folio} "
            f"(HTML={len(html)} chars, logo={'OK' if logo_data_uri else 'MISSING'})"
        )

        def _render_in_thread(html_content):
            from playwright.sync_api import sync_playwright
            try:
                with sync_playwright() as pw:
                    ActaPDFService._logger.debug("Playwright: lanzando Chromium...")
                    browser = pw.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-gpu',
                            '--disable-dev-shm-usage',
                            '--disable-setuid-sandbox',
                            '--font-render-hinting=none',
                        ],
                    )
                    ActaPDFService._logger.debug("Playwright: navegador listo, creando página...")
                    page = browser.new_page()
                    page.set_content(html_content, wait_until='networkidle')
                    ActaPDFService._logger.debug("Playwright: contenido cargado, generando PDF...")
                    pdf_bytes = page.pdf(
                        format='Letter',
                        margin={'top': '1.5cm', 'bottom': '1.5cm',
                                'left': '1.5cm', 'right': '1.5cm'},
                        print_background=True,
                    )
                    ActaPDFService._logger.info(
                        f"Playwright: PDF generado ({len(pdf_bytes)} bytes)"
                    )
                    page.close()
                    browser.close()
                    return pdf_bytes
            except Exception as e:
                ActaPDFService._logger.error(f"Playwright error en thread: {e}")
                raise

        timeout = getattr(settings, 'PLAYWRIGHT_BROWSER_TIMEOUT', 15000) / 1000
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_render_in_thread, html)
            return future.result(timeout=timeout + 5)

    @staticmethod
    def generar_preview_pdf(colaborador, tipo_acta, asignacion_ids, creado_por,
                             observaciones=None, accesorio_ids=None, ministro_de_fe=None):
        """
        Genera un PDF de preview (sin persistir) usando Playwright/Chromium.

        Args:
            colaborador, tipo_acta, asignacion_ids, creado_por: mismos que generar_preview_html.
            observaciones, accesorio_ids, ministro_de_fe: opcionales.

        Returns:
            bytes: Contenido binario del PDF.
        """
        from dispositivos.models import HistorialAsignacion, EntregaAccesorio

        asignaciones = HistorialAsignacion.objects.filter(
            pk__in=asignacion_ids,
            colaborador=colaborador,
            acta__isnull=True,
        ).select_related(
            'dispositivo__modelo__tipo_dispositivo',
            'dispositivo__modelo__fabricante',
            'dispositivo__modelo',
        )

        accesorios = []
        if accesorio_ids:
            accesorios = list(EntregaAccesorio.objects.filter(
                pk__in=accesorio_ids,
                colaborador=colaborador,
                acta__isnull=True
            ))

        acta_preview = Acta(
            colaborador=colaborador,
            tipo_acta=tipo_acta,
            creado_por=creado_por,
            observaciones=observaciones or '',
            ministro_de_fe=ministro_de_fe,
            fecha=timezone.now(),
        )
        acta_preview.folio = f"ACT-{timezone.now().year}-PENDIENTE"

        return ActaPDFService._playwright(acta_preview, asignaciones=asignaciones, accesorios=accesorios)
