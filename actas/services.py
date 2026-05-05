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
    def crear_acta(colaborador, tipo_acta, asignacion_ids=None, movimiento_ids=None, 
                   creado_por=None, observaciones=None, accesorio_ids=None, 
                   metodo_sanitizacion='N/A', ministro_de_fe=None):
        """
        Crea un acta nueva y vincula las asignaciones o movimientos seleccionados.

        Args:
            colaborador: Instancia de Colaborador destinatario del acta.
            tipo_acta: Tipo de documento ('ENTREGA', 'DEVOLUCION', 'ENTREGA_SUMINISTROS').
            asignacion_ids: Lista de PKs de HistorialAsignacion (para dispositivos).
            movimiento_ids: Lista de PKs de MovimientoStock (para suministros).
            creado_por: Instancia de Colaborador que genera el acta.
            observaciones: Texto libre opcional.

        Returns:
            Acta: La instancia del acta creada.

        Raises:
            ValidationError: Si no se seleccionan items o ninguno es válido.
        """
        from suministros.models import MovimientoStock

        # Validar según tipo de acta
        if tipo_acta == 'ENTREGA_SUMINISTROS':
            if not movimiento_ids:
                raise ValidationError("Debe seleccionar al menos un movimiento de stock.")
        else:
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

        # Vincular según tipo de acta
        if tipo_acta == 'ENTREGA_SUMINISTROS':
            from suministros.models import MovimientoStock
            movimientos = MovimientoStock.objects.filter(
                pk__in=movimiento_ids,
                colaborador_destino=colaborador,
                tipo_movimiento=MovimientoStock.TipoMovimiento.SALIDA,
            )
            
            if not movimientos.exists():
                raise ValidationError(
                    "Los movimientos seleccionados ya no están disponibles "
                    "o no pertenecen al colaborador."
                )
            
            # Crear instancias del modelo intermedio manualmente
            from actas.models import MovimientoStockActa
            MovimientoStockActa.objects.bulk_create([
                MovimientoStockActa(acta=acta, movimiento=mov)
                for mov in movimientos
            ])
        else:
            # Vincular asignaciones de dispositivos
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
    @transaction.atomic
    def firmar_acta(acta_pk, firmado_por):
        """
        Marca un acta como firmada (blindaje legal) y registra auditoría.

        Args:
            acta_pk: PK del acta a firmar.
            firmado_por: Instancia de Colaborador que firma.

        Returns:
            bool: True si se firmó correctamente.

        Raises:
            ValidationError: Si el acta ya estaba firmada o no existe.
        """
        try:
            acta = Acta.objects.select_for_update().get(pk=acta_pk)
        except Acta.DoesNotExist:
            raise ValidationError("El acta no existe.")

        if acta.firmada:
            raise ValidationError("El acta ya está firmada.")

        if acta.anulada:
            raise ValidationError("No se puede firmar un acta que ha sido anulada.")

        acta.firmada = True
        acta.firmada_por = firmado_por
        acta.fecha_firma = timezone.now()
        acta.save()
        
        return True

    @staticmethod
    def obtener_acta_con_relaciones(acta_pk):
        """
        Obtiene un acta con todas sus relaciones cargadas para evitar N+1.

        Args:
            acta_pk: PK del acta.

        Returns:
            tuple: (acta, items) donde items es asignaciones o movimientos según tipo.
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
            'movimientos_stock__movimiento__suministro__categoria',
            'movimientos_stock__movimiento__suministro__fabricante',
        ).get(pk=acta_pk)

        if acta.tipo_acta == 'ENTREGA_SUMINISTROS':
            from suministros.models import MovimientoStock
            movimientos = MovimientoStock.objects.filter(
                actas__acta=acta
            ).select_related('suministro__categoria', 'suministro__fabricante')
            return acta, movimientos
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

        logo_path = ActaPDFService._encode_logo_to_base64(finders.find('img/LogoColor.png'))

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
    def generar_preview_html_suministros(colaborador, tipo_acta, movimiento_ids, creado_por,
                                          observaciones=None, pdf_mode=False):
        """
        Construye el contexto para renderizar la vista previa de acta de suministros
        SIN persistir en base de datos.
        """
        from suministros.models import MovimientoStock

        if not movimiento_ids:
            raise ValidationError("Debe seleccionar al menos un movimiento.")

        movimientos = MovimientoStock.objects.filter(
            pk__in=movimiento_ids,
            colaborador_destino=colaborador,
            tipo_movimiento=MovimientoStock.TipoMovimiento.SALIDA,
        ).select_related(
            'suministro__categoria',
            'suministro__fabricante',
            'centro_costo',
            'dispositivo_destino',
        )

        if not movimientos.exists():
            raise ValidationError(
                "Los movimientos seleccionados ya no están disponibles."
            )

        acta_preview = Acta(
            colaborador=colaborador,
            tipo_acta=tipo_acta,
            creado_por=creado_por,
            observaciones=observaciones or '',
            fecha=timezone.now(),
        )
        acta_preview.folio = f"ACT-{timezone.now().year}-PENDIENTE"

        logo_path = ActaPDFService._encode_logo_to_base64(finders.find('img/LogoColor.png'))

        # Obtener costo unitario desde la última ENTRADA de cada suministro
        suministro_ids = [m.suministro_id for m in movimientos]
        # SQLite no soporta .distinct('suministro_id'), usamos valores agrupados por suministro
        entradas = MovimientoStock.objects.filter(
            suministro_id__in=suministro_ids,
            tipo_movimiento=MovimientoStock.TipoMovimiento.ENTRADA,
            costo_unitario__isnull=False,
        ).order_by('-fecha')
        seen = set()
        costos_entrada = {}
        for e in entradas:
            if e.suministro_id not in seen:
                seen.add(e.suministro_id)
                costos_entrada[e.suministro_id] = e.costo_unitario
        # Construir lista con costo efectivo (propio o heredado de ENTRADA)
        movimientos_data = []
        for m in movimientos:
            costo = m.costo_unitario or costos_entrada.get(m.suministro_id) or 0
            movimientos_data.append({
                'movimiento': m,
                'costo_efectivo': costo,
                'subtotal': costo * m.cantidad,
            })

        # Calcular valor total
        valor_total = sum(d['subtotal'] for d in movimientos_data)

        context = {
            'acta': acta_preview,
            'movimientos': movimientos,
            'movimientos_data': movimientos_data,
            'logo_path': logo_path,
            'fecha_actual': timezone.now(),
            'preview': True,
            'valor_total': valor_total,
            'es_suministros': True,
            'pdf_mode': pdf_mode,
        }

        return render_to_string('actas/partials/acta_suministro_preview_content.html', context)

    @staticmethod
    def generar_preview_pdf_suministros(colaborador, tipo_acta, movimiento_ids, creado_por,
                                         observaciones=None):
        """Genera PDF preview para acta de suministros."""
        preview_html = ActaService.generar_preview_html_suministros(
            colaborador, tipo_acta, movimiento_ids, creado_por, observaciones,
            pdf_mode=True
        )
        
        acta_preview = Acta(
            colaborador=colaborador,
            tipo_acta=tipo_acta,
            creado_por=creado_por,
            observaciones=observaciones or '',
            fecha=timezone.now(),
        )
        acta_preview.folio = f"ACT-{timezone.now().year}-PENDIENTE"
        
        return ActaPDFService.generar_pdf_suministros(acta_preview, preview_html)

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

    @staticmethod
    def obtener_movimientos_pendientes(colaborador_pk):
        """
        Retorna los movimientos de stock tipo SALIDA sin acta de un colaborador.

        Args:
            colaborador_pk: PK del colaborador.

        Returns:
            QuerySet de MovimientoStock.
        """
        from suministros.models import MovimientoStock
        return MovimientoStock.objects.filter(
            colaborador_destino_id=colaborador_pk,
            tipo_movimiento=MovimientoStock.TipoMovimiento.SALIDA,
            actas__isnull=True,
        ).select_related(
            'suministro__categoria',
            'suministro__fabricante',
            'centro_costo',
            'dispositivo_destino',
        ).order_by('-fecha')

    @staticmethod
    def obtener_movimientos_para_pdf(acta):
        """
        Obtiene los movimientos de stock optimizados para renderizado PDF.

        Args:
            acta: Instancia de Acta.

        Returns:
            QuerySet de MovimientoStock.
        """
        from suministros.models import MovimientoStock
        return MovimientoStock.objects.filter(
            actas=acta
        ).select_related(
            'suministro__categoria',
            'suministro__fabricante',
            'centro_costo',
            'dispositivo_destino',
        )

    @staticmethod
    @transaction.atomic
    def anular(acta_pk, usuario, motivo=None):
        """
        Anula o elimina un acta según su estado.

        - Borradores (firmada=False): eliminación física (DELETE).
          Carecen de valor legal, no necesitan preservarse.
        - Firmadas (firmada=True): anulación lógica (soft delete).
          Se mantiene el registro con estado 'anulada' para auditoría legal.

        Args:
            acta_pk: PK del acta.
            usuario: Instancia de Colaborador que ejecuta la acción.
            motivo: Motivo de anulación (obligatorio para firmadas).

        Returns:
            tuple: (acta, accion) donde accion es 'eliminada' o 'anulada'.

        Raises:
            ValidationError: Si el acta no existe, ya está anulada, o falta motivo.
        """
        try:
            acta = Acta.objects.select_for_update().get(pk=acta_pk)
        except Acta.DoesNotExist:
            raise ValidationError("El acta no existe.")

        if acta.anulada:
            raise ValidationError("Esta acta ya fue anulada.")

        if acta.firmada:
            # Anulación lógica — preservar para auditoría legal
            if not motivo or len(motivo.strip()) < 10:
                raise ValidationError(
                    "El motivo de anulación es obligatorio y debe tener al menos 10 caracteres."
                )
            acta.anulada = True
            acta.anulada_por = usuario
            acta.fecha_anulacion = timezone.now()
            acta.motivo_anulacion = motivo.strip()
            acta.save()
            logger.info(
                "Acta %s ANULADA por %s. Motivo: %s",
                acta.folio, usuario, motivo.strip()
            )
            return acta, 'anulada'
        else:
            # Eliminación física — es un borrador sin valor legal
            folio = acta.folio
            acta.delete()
            logger.info(
                "Acta %s ELIMINADA (borrador) por %s.",
                folio, usuario
            )
            return None, 'eliminada'


class ActaPDFService:
    """
    Servicio de generación de PDFs de actas usando Playwright/Chromium headless.

    Usa un pool de browsers (actas.playwright_browser) para reutilizar instancias
    y evitar el overhead de lanzar Chromium en cada request.
    """

    _logger = logging.getLogger('actas')
    _logo_base64_cache = None
    _logo_mtime = None

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
    def _encode_logo_to_base64(logo_path):
        """Convierte el logo a data URI base64 para embedding en HTML (con cache)."""
        if not logo_path:
            return None
        try:
            import base64
            import mimetypes
            import os
            mime, _ = mimetypes.guess_type(logo_path)
            current_mtime = os.path.getmtime(logo_path)
            if (ActaPDFService._logo_base64_cache is not None and
                    ActaPDFService._logo_mtime == current_mtime):
                return ActaPDFService._logo_base64_cache

            with open(logo_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode('ascii')
            result = f"data:{mime or 'image/png'};base64,{data}"
            ActaPDFService._logo_base64_cache = result
            ActaPDFService._logo_mtime = current_mtime
            return result
        except (OSError, ValueError) as e:
            ActaPDFService._logger.warning(f"No se pudo codificar logo a base64: {e}")
            return None

    @staticmethod
    def _playwright(acta, asignaciones=None, accesorios=None):
        """Genera PDF usando Playwright/Chromium en un thread separado.

        Usa el mismo HTML que la vista previa (acta_preview_content.html) para que
        el PDF sea pixel-perfect con lo que el usuario ve en el navegador.
        """
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
                    browser = pw.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox', '--disable-gpu',
                            '--disable-dev-shm-usage', '--disable-setuid-sandbox',
                            '--font-render-hinting=none',
                        ],
                    )
                    page = browser.new_page()
                    page.set_content(html_content, wait_until='networkidle')
                    pdf_bytes = page.pdf(
                        format='Letter',
                        margin={'top': '1.5cm', 'bottom': '1.5cm',
                                'left': '1.5cm', 'right': '1.5cm'},
                        print_background=True,
                    )
                    page.close()
                    browser.close()
                    ActaPDFService._logger.info(
                        f"Playwright: PDF generado ({len(pdf_bytes)} bytes)"
                    )
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

    @staticmethod
    def generar_pdf_suministros(acta, preview_html):
        """
        Genera PDF para acta de suministros a partir de HTML ya renderizado.
        
        Args:
            acta: Instancia de Acta (para el folio en logs).
            preview_html: HTML string renderizado del template de suministros.
            
        Returns:
            bytes: Contenido binario del PDF.
        """
        import concurrent.futures
        from django.conf import settings

        # Wrap en HTML completo para Playwright
        html = render_to_string('actas/playwright/pdf_wrapper.html', {
            'preview_html': preview_html,
        })

        ActaPDFService._logger.info(
            f"Iniciando generación Playwright para acta de suministros {acta.folio} "
            f"(HTML={len(html)} chars)"
        )

        def _render_in_thread(html_content):
            from playwright.sync_api import sync_playwright
            try:
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox', '--disable-gpu',
                            '--disable-dev-shm-usage', '--disable-setuid-sandbox',
                            '--font-render-hinting=none',
                        ],
                    )
                    page = browser.new_page()
                    page.set_content(html_content, wait_until='networkidle')
                    pdf_bytes = page.pdf(
                        format='Letter',
                        margin={'top': '1.5cm', 'bottom': '1.5cm',
                                'left': '1.5cm', 'right': '1.5cm'},
                        print_background=True,
                    )
                    page.close()
                    browser.close()
                    ActaPDFService._logger.info(
                        f"Playwright: PDF generado ({len(pdf_bytes)} bytes)"
                    )
                    return pdf_bytes
            except Exception as e:
                ActaPDFService._logger.error(f"Playwright error en thread: {e}")
                raise

        timeout = getattr(settings, 'PLAYWRIGHT_BROWSER_TIMEOUT', 15000) / 1000
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_render_in_thread, html)
            return future.result(timeout=timeout + 5)
