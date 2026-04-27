"""
Capa de servicios para la app Actas.

Contiene toda la lógica de negocio separada de las vistas (HTTP) y los modelos (persistencia).
Siguiendo el patrón Service Layer recomendado por django-patterns skill.
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa

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
        Genera el contenido binario del PDF corporativo para un acta.

        Args:
            acta: Instancia de Acta (debe tener relaciones cargadas).

        Returns:
            bytes: El contenido del PDF generado.

        Raises:
            RuntimeError: Si xhtml2pdf falla en la generación.
        """
        asignaciones = ActaService.obtener_asignaciones_para_pdf(acta)
        logo_path = finders.find('img/LogoColor.png')
        accesorios = acta.accesorios.all()

        context = {
            'acta': acta,
            'asignaciones': asignaciones,
            'accesorios': accesorios,
            'logo_path': logo_path,
            'fecha_actual': timezone.now(),
        }

        html = render_to_string('actas/partials/acta_pdf.html', context)

        from io import BytesIO
        buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=buffer)

        if pisa_status.err:
            raise RuntimeError(f"Error al generar PDF para acta {acta.folio}")

        return buffer.getvalue()

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
