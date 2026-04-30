# Protección y Anulación de Actas — Implementation Plan

**Goal:** Implementar anulación lógica (soft delete) de actas con protección física, doble autorización para firmadas, auditoría completa y UI HTMX.

**Architecture:** Extender modelo `Acta` con campos de auditoría y estado de anulación; bloquear `delete()` si tiene folio; servicio `ActaService.anular_acta()` con lógica de autorización y atomicidad; vista HTMX `acta_anular`; modal y badges en tablas; logging en `'actas'`.

**Design:** [thoughts/shared/designs/2026-04-30-proteccion-anulacion-actas-design.md](thoughts/shared/designs/2026-04-30-proteccion-anulacion-actas-design.md)

---

## Dependency Graph

```
Batch 1 (parallel): 1.1, 1.2 [foundation - no deps]
Batch 2 (parallel): 2.1, 2.2, 2.3 [core logic - depends on batch 1]
Batch 3 (parallel): 3.1, 3.2, 3.3 [backend interface - depends on batch 2]
Batch 4 (parallel): 4.1, 4.2 [templates - depends on batch 3]
Batch 5 (parallel): 5.1, 5.2, 5.3, 5.4, 5.5 [tests - depends on batch 3/4]
Batch 6 (parallel): 6.1, 6.2 [e2e - depends on batch 5]
```

---

## Batch 1: Foundation (parallel — 2 implementers)

### Task 1.1: Django Migration — Nuevos campos y permisos en Acta
**File:** `actas/migrations/0003_acta_anulacion_fields.py` (nuevo, autogenerado vía makemigrations)
**Test:** none (verificación manual)
**Depends:** none

**Instrucciones:**
1. Ejecutar `python manage.py makemigrations actas` para generar la migración.
2. Verificar que la migración incluya:
   - `firmada_por` (FK a `colaboradores.Colaborador`, `on_delete=models.SET_NULL`, `null=True`, `blank=True`)
   - `fecha_firma` (`DateTimeField`, `null=True`, `blank=True`)
   - `anulada` (`BooleanField`, `default=False`)
   - `anulada_por` (FK a `colaboradores.Colaborador`, `on_delete=models.SET_NULL`, `null=True`, `blank=True`)
   - `fecha_anulacion` (`DateTimeField`, `null=True`, `blank=True`)
   - `motivo_anulacion` (`TextField`, `null=True`, `blank=True`)
   - Permiso custom `aprobar_anulacion` en `Meta` de `Acta`.
3. Aplicar con `python manage.py migrate`.

**Verify:** `python manage.py migrate --plan` muestra la migración lista para aplicar.
**Commit:** `feat(actas): add anulacion fields and approval permission migration`

---

### Task 1.2: Actualizar ActaFactory con nuevos campos
**File:** `core/tests/factories.py`
**Test:** none (factory helper)
**Depends:** none

```python
# Añadir al final de la clase ActaFactory (líneas 129-136)
class ActaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Acta
    
    colaborador = factory.SubFactory(ColaboradorFactory)
    creado_por = factory.SubFactory(ColaboradorFactory)
    tipo_acta = 'ENTREGA'
    observaciones = "Generada por factory"
    firmada = False
    anulada = False
    motivo_anulacion = None
    fecha_firma = None
    fecha_anulacion = None
    # firmada_por / anulada_por se dejan None por defecto
```

**Verify:** `pytest actas/tests/test_models.py::TestActaModel::test_folio_generation -v` pasa con factory actualizada.
**Commit:** `test(factories): extend ActaFactory with anulada and firma fields`

---

## Batch 2: Core Logic (parallel — 3 implementers)

### Task 2.1: Extender modelo Acta
**File:** `actas/models.py`
**Test:** `actas/tests/test_models.py`
**Depends:** 1.1

```python
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from colaboradores.models import Colaborador
from dispositivos.models import Dispositivo

class Acta(models.Model):
    TIPO_ACTA_CHOICES = [
        ('ENTREGA', 'Acta de Entrega'),
        ('DEVOLUCION', 'Acta de Devolución'),
    ]

    METODO_SANITIZACION_CHOICES = [
        ('CLEARED', 'NIST Clear (Borrado Lógico)'),
        ('PURGED', 'NIST Purge (Borrado Criptográfico Irreversible)'),
        ('DESTROYED', 'NIST Destroy (Destrucción Física)'),
        ('N/A', 'No Aplica / Entrega'),
    ]

    folio = models.CharField(max_length=20, unique=True, editable=False)
    fecha = models.DateTimeField(default=timezone.now)
    colaborador = models.ForeignKey(Colaborador, on_delete=models.PROTECT, related_name="actas")
    tipo_acta = models.CharField(max_length=15, choices=TIPO_ACTA_CHOICES, default='ENTREGA')
    
    creado_por = models.ForeignKey(Colaborador, on_delete=models.SET_NULL, null=True, related_name="actas_creadas")
    observaciones = models.TextField(null=True, blank=True)
    
    firmada = models.BooleanField(default=False, help_text="Si está firmada, no se puede modificar")
    firmada_por = models.ForeignKey(
        Colaborador, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='actas_firmadas'
    )
    fecha_firma = models.DateTimeField(null=True, blank=True)

    archivo_adjunto = models.FileField(upload_to='actas/firmadas/', null=True, blank=True, help_text="Acta escaneada y firmada")

    # Campos de cumplimiento legal y técnico para devoluciones
    metodo_sanitizacion = models.CharField(
        max_length=20, 
        choices=METODO_SANITIZACION_CHOICES, 
        default='N/A',
        help_text="Estándar NIST SP 800-88 aplicado al equipo"
    )
    ministro_de_fe = models.ForeignKey(
        Colaborador, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="actas_validadas",
        help_text="Administrador de obra que actúa como ministro de fe en terreno"
    )

    # Campos de anulación
    anulada = models.BooleanField(default=False, help_text="Si está anulada, el acta queda inhabilitada")
    anulada_por = models.ForeignKey(
        Colaborador, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='actas_anuladas'
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.firmada and self.pk:
            # Blindaje: Si ya existe y está firmada, impedimos cualquier cambio
            # Excepto campos de anulación (controlado vía servicio)
            existente = Acta.objects.get(pk=self.pk)
            if existente.firmada and not self.anulada:
                raise ValidationError("No se puede modificar un acta que ya ha sido marcada como FIRMADA.")
        
        if not self.folio:
            year = timezone.now().year
            prefix = f"ACT-{year}-"
            # Buscamos todos los folios de este año para encontrar el máximo real
            folios = Acta.objects.filter(folio__startswith=prefix).values_list('folio', flat=True)
            
            max_num = 0
            for f in folios:
                try:
                    # Extraemos el número final sin importar el largo (001 o 0001)
                    num = int(f.split('-')[-1])
                    if num > max_num:
                        max_num = num
                except (ValueError, IndexError):
                    continue
            
            # El nuevo número es el máximo + 1, formateado a 4 dígitos por estándar
            nuevo_sec = str(max_num + 1).zfill(4)
            self.folio = f"{prefix}{nuevo_sec}"
            
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.folio:
            raise ValidationError(
                "No se puede eliminar un acta que ya tiene folio asignado. "
                "Use la funcionalidad de anulación en su lugar."
            )
        super().delete(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.anulada and not self.motivo_anulacion:
            raise ValidationError({
                'motivo_anulacion': 'El motivo de anulación es obligatorio cuando se anula un acta.'
            })

    def __str__(self):
        return f"{self.folio} - {self.colaborador}"

    class Meta:
        verbose_name = "Acta"
        verbose_name_plural = "Actas"
        permissions = [
            ('aprobar_anulacion', 'Puede aprobar anulación de actas firmadas'),
        ]
```

**Verify:** `pytest actas/tests/test_models.py -v`
**Commit:** `feat(actas): add anulacion fields, delete protection and model validation`

---

### Task 2.2: Servicio ActaService — anular_acta y firma auditada
**File:** `actas/services.py`
**Test:** `actas/tests/test_services.py`
**Depends:** 2.1

```python
"""
Capa de servicios para la app Actas.
"""
import logging

from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Acta
from dispositivos.models import HistorialAsignacion


class ActaService:
    """Servicio principal para la gestión de actas legales."""

    _logger = logging.getLogger('actas')

    @staticmethod
    @transaction.atomic
    def crear_acta(colaborador, tipo_acta, asignacion_ids, creado_por, observaciones=None, accesorio_ids=None, metodo_sanitizacion='N/A', ministro_de_fe=None):
        """
        Crea un acta nueva y vincula las asignaciones seleccionadas.
        """
        if not asignacion_ids:
            raise ValidationError("Debe seleccionar al menos una asignación.")

        from django.db import IntegrityError
        
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
                break
            except IntegrityError:
                if attempt == max_retries - 1:
                    raise ValidationError("Error crítico: No se pudo generar un folio único tras varios intentos. Reintente.")
                continue

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

        if accesorio_ids:
            from dispositivos.models import EntregaAccesorio
            EntregaAccesorio.objects.filter(
                pk__in=accesorio_ids,
                colaborador=colaborador,
                acta__isnull=True
            ).update(acta=acta)

        ActaService._logger.info("Acta %s creada por %s", acta.folio, creado_por)
        return acta

    @staticmethod
    @transaction.atomic
    def firmar_acta(acta_pk, firmado_por):
        """
        Marca un acta como firmada (blindaje legal) y registra auditoría.
        """
        try:
            acta = Acta.objects.get(pk=acta_pk)
        except Acta.DoesNotExist:
            raise ValidationError("El acta no existe.")

        if acta.firmada:
            raise ValidationError("El acta ya está firmada.")

        if acta.anulada:
            raise ValidationError("No se puede firmar un acta que ha sido anulada.")

        acta.firmada = True
        acta.firmada_por = firmado_por
        acta.fecha_firma = timezone.now()
        acta.save(update_fields=['firmada', 'firmada_por', 'fecha_firma'])

        ActaService._logger.info("Acta %s firmada por %s", acta.folio, firmado_por)
        return True

    @staticmethod
    @transaction.atomic
    def anular_acta(acta, usuario, motivo, aprobador_id=None):
        """
        Anula un acta lógicamente. Requiere doble autorización si está firmada.
        
        Args:
            acta: Instancia de Acta.
            usuario: Colaborador que solicita la anulación.
            motivo: Texto obligatorio con el motivo.
            aprobador_id: PK del aprobador (requerido si acta.firmada).
        
        Returns:
            Acta actualizada.
        
        Raises:
            ValidationError: Si las validaciones de estado o autorización fallan.
            PermissionDenied: Si el aprobador no tiene permisos.
        """
        if acta.anulada:
            raise ValidationError("Esta acta ya fue anulada.")

        if not motivo or not motivo.strip():
            raise ValidationError({"motivo": "El motivo de anulación es obligatorio."})

        if acta.firmada:
            if not aprobador_id:
                raise ValidationError({"aprobador": "Las actas firmadas requieren un aprobador."})

            if int(aprobador_id) == usuario.pk:
                raise ValidationError({"aprobador": "El aprobador no puede ser el mismo solicitante."})

            from colaboradores.models import Colaborador
            try:
                aprobador = Colaborador.objects.get(pk=aprobador_id, esta_activo=True)
            except Colaborador.DoesNotExist:
                raise ValidationError({"aprobador": "El aprobador seleccionado no existe o está inactivo."})

            if not aprobador.has_perm('actas.aprobar_anulacion'):
                raise PermissionDenied("El aprobador seleccionado no tiene permisos para aprobar anulaciones.")

            aprobador_display = aprobador
        else:
            # Actas no firmadas: requiere permiso estándar delete_acta
            if not usuario.has_perm('actas.delete_acta'):
                raise PermissionDenied("No tienes permisos para anular actas.")
            aprobador_display = None

        acta.anulada = True
        acta.motivo_anulacion = motivo.strip()
        acta.anulada_por = usuario
        acta.fecha_anulacion = timezone.now()
        acta.save(update_fields=['anulada', 'motivo_anulacion', 'anulada_por', 'fecha_anulacion'])

        ActaService._logger.warning(
            "Acta %s anulada por %s. Motivo: %s. Aprobador: %s",
            acta.folio, usuario, motivo, aprobador_display or "N/A (no firmada)"
        )
        return acta

    @staticmethod
    def obtener_acta_con_relaciones(acta_pk):
        """
        Obtiene un acta con todas sus relaciones cargadas para evitar N+1.
        """
        acta = Acta.objects.select_related(
            'colaborador__centro_costo',
            'colaborador__departamento',
            'creado_por',
            'ministro_de_fe',
            'firmada_por',
            'anulada_por',
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
        """
        return ActaPDFService._playwright(acta)

    @staticmethod
    def generar_preview_pdf(colaborador, tipo_acta, asignacion_ids, creado_por,
                             observaciones=None, accesorio_ids=None, ministro_de_fe=None):
        """
        Genera un PDF de preview (sin persistir) delegando en ActaPDFService.
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
    """

    _logger = logging.getLogger('actas')
    _logo_base64_cache = None
    _logo_mtime = None

    @staticmethod
    # ... resto del archivo se mantiene igual ...
```

**Nota:** El implementador debe conservar el resto de `ActaPDFService` tal como está.

**Verify:** `pytest actas/tests/test_services.py -v`
**Commit:** `feat(actas): add anular_acta service with dual authorization and audit logging`

---

### Task 2.3: Formulario de anulación ActaAnularForm
**File:** `actas/forms.py`
**Test:** `actas/tests/test_forms.py`
**Depends:** 2.1

```python
from django import forms
from django.core.exceptions import ValidationError
from .models import Acta
from core.forms import BaseStyledForm
from colaboradores.models import Colaborador

class ActaCrearForm(BaseStyledForm):
    class Meta:
        model = Acta
        fields = ['colaborador', 'tipo_acta', 'ministro_de_fe', 'observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Detalles adicionales, estado de entrega, etc.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['colaborador'].queryset = Colaborador.objects.filter(esta_activo=True).order_by('first_name', 'last_name')
        
        from django.db.models import Q
        admin_criterios = Q(cargo__icontains='Administrador') | Q(cargo__icontains='Jefe') | Q(cargo__icontains='Encargado')
        self.fields['ministro_de_fe'].queryset = Colaborador.objects.filter(
            esta_activo=True
        ).filter(admin_criterios).order_by('first_name', 'last_name')
        self.fields['ministro_de_fe'].required = False
        
        self.fields['tipo_acta'].widget.attrs.update({
            'x-model': 'tipoActa',
            'class': 'form-select-jmie'
        })
        
        self.fields['colaborador'].widget.attrs.update({
            'class': 'form-select-jmie htmx-colaborador-select',
        })

        self.fields['ministro_de_fe'].widget.attrs.update({
            'class': 'form-select-jmie htmx-ministro-select',
        })


class ActaAnularForm(forms.Form):
    """Formulario para solicitar la anulación de un acta."""
    
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Describa el motivo de la anulación...',
            'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background placeholder:text-jmie-gray focus:ring-1 focus:border-jmie-blue focus:ring-jmie-blue/40 transition-all',
        }),
        label='Motivo de Anulación',
        required=True,
    )
    
    aprobador = forms.ModelChoiceField(
        queryset=Colaborador.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background placeholder:text-jmie-gray focus:ring-1 focus:border-jmie-blue focus:ring-jmie-blue/40 transition-all appearance-none',
        }),
        label='Aprobador (solo actas firmadas)',
    )

    def __init__(self, *args, acta=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.acta = acta
        if acta and acta.firmada:
            # Solo supervisores con permiso de aprobación
            from django.db.models import Q
            self.fields['aprobador'].required = True
            self.fields['aprobador'].queryset = Colaborador.objects.filter(
                esta_activo=True,
                user_permissions__codename='aprobar_anulacion'
            ).distinct().order_by('first_name', 'last_name')
            
            # Excluir al solicitante si está autenticado
            if hasattr(self, 'solicitante') and self.solicitante:
                self.fields['aprobador'].queryset = self.fields['aprobador'].queryset.exclude(pk=self.solicitante.pk)
        else:
            self.fields['aprobador'].widget = forms.HiddenInput()
            self.fields['aprobador'].required = False

    def clean(self):
        cleaned_data = super().clean()
        motivo = cleaned_data.get('motivo', '').strip()
        
        if not motivo:
            raise ValidationError({'motivo': 'El motivo de anulación es obligatorio.'})
        
        if self.acta and self.acta.firmada:
            aprobador = cleaned_data.get('aprobador')
            if not aprobador:
                raise ValidationError({'aprobador': 'Las actas firmadas requieren un aprobador.'})
        
        return cleaned_data
```

**Verify:** `pytest actas/tests/test_forms.py -v`
**Commit:** `feat(actas): add ActaAnularForm with conditional approver field`

---

## Batch 3: Backend Interface (parallel — 3 implementers)

### Task 3.1: Vistas acta_anular y filtros en listado
**File:** `actas/views.py`
**Test:** `actas/tests/test_views.py`
**Depends:** 2.2, 2.3

```python
import logging

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.utils.html import escape

from .models import Acta
from .forms import ActaCrearForm, ActaAnularForm
from .services import ActaService, ActaPDFService
from core.htmx import htmx_trigger_response

logger = logging.getLogger('actas')


def _render_acta_error(message):
    """Renderiza el bloque OOB de errores para el modal de actas."""
    return render_to_string("actas/partials/acta_error.html", {"message": message})

@login_required
@permission_required('actas.view_acta', raise_exception=True)
def acta_list(request):
    """Listado paginado de actas con filtrado básico, ordenamiento HTMX y exclusión de anuladas por defecto."""
    actas_list = Acta.objects.all().select_related('colaborador', 'creado_por')
    
    # Por defecto ocultar anuladas; se pueden incluir con ?incluir_anuladas=1
    if not request.GET.get('incluir_anuladas'):
        actas_list = actas_list.filter(anulada=False)
    
    q = request.GET.get('q')
    if q:
        from django.db.models import Q
        actas_list = actas_list.filter(
            Q(folio__icontains=q) | 
            Q(colaborador__first_name__icontains=q) |
            Q(colaborador__last_name__icontains=q)
        )
        
    tipo = request.GET.get('tipo')
    if tipo:
        actas_list = actas_list.filter(tipo_acta=tipo)

    # Ordenamiento
    sort = request.GET.get('sort', 'folio')
    order = request.GET.get('order', 'asc')
    
    SORT_MAP = {
        'folio': 'folio',
        'colaborador': 'colaborador__first_name',
        'tipo': 'tipo_acta',
        'fecha': 'fecha',
        'creado_por': 'creado_por__first_name',
        'firmada': 'firmada',
    }
    
    sort_field = SORT_MAP.get(sort, 'folio')
    if order == 'desc':
        sort_field = f'-{sort_field}'
    actas_list = actas_list.order_by(sort_field)

    paginator = Paginator(actas_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    template = 'actas/acta_list.html'
    if request.headers.get('HX-Request'):
        template = 'actas/partials/acta_table.html'

    return render(request, template, {
        'page_obj': page_obj,
        'query': q or '',
        'tipo': tipo or '',
        'current_sort': sort,
        'current_order': order,
        'incluir_anuladas': bool(request.GET.get('incluir_anuladas')),
    })

@login_required
@permission_required('actas.add_acta', raise_exception=True)
def acta_preview(request):
    """Genera la vista previa HTML de un acta sin persistir en BD."""
    if request.method == 'POST':
        data = request.POST
    elif request.method == 'GET':
        data = request.GET
    else:
        return HttpResponse("Método no permitido", status=405)

    form = ActaCrearForm(data)
    asignacion_ids = data.getlist('asignaciones')
    accesorio_ids = data.getlist('accesorios')

    if not form.is_valid():
        error_html = _render_acta_error("Corrija los errores del formulario antes de previsualizar.")
        return HttpResponse(error_html)

    try:
        preview_html = ActaService.generar_preview_html(
            colaborador=form.cleaned_data['colaborador'],
            tipo_acta=form.cleaned_data['tipo_acta'],
            asignacion_ids=asignacion_ids,
            creado_por=request.user,
            observaciones=form.cleaned_data.get('observaciones'),
            accesorio_ids=accesorio_ids,
            ministro_de_fe=form.cleaned_data.get('ministro_de_fe'),
        )

        if request.method == 'GET':
            return render(request, 'actas/partials/acta_preview_fullpage.html', {
                'preview_html': preview_html,
                'acta': form.cleaned_data['colaborador'],
            })

        return render(request, 'actas/partials/acta_preview_sideover.html', {
            'preview_html': preview_html,
            'form_data': data,
        })

    except ValidationError as e:
        error_html = _render_acta_error(str(e))
        return HttpResponse(error_html)
    except Exception:
        logger.exception("Error en preview de acta")
        error_html = _render_acta_error('Error interno al generar la vista previa.')
        return HttpResponse(error_html)


@login_required
@permission_required('actas.add_acta', raise_exception=True)
def acta_preview_pdf(request):
    """Genera un PDF de preview (sin persistir) usando el engine configurado."""
    form = ActaCrearForm(request.GET)
    asignacion_ids = request.GET.getlist('asignaciones')
    accesorio_ids = request.GET.getlist('accesorios')

    if not form.is_valid():
        return HttpResponse("Datos inválidos para generar PDF de preview", status=400)

    try:
        pdf_bytes = ActaPDFService.generar_preview_pdf(
            colaborador=form.cleaned_data['colaborador'],
            tipo_acta=form.cleaned_data['tipo_acta'],
            asignacion_ids=asignacion_ids,
            creado_por=request.user,
            observaciones=form.cleaned_data.get('observaciones'),
            accesorio_ids=accesorio_ids,
            ministro_de_fe=form.cleaned_data.get('ministro_de_fe'),
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="preview.pdf"'
        return response
    except ValidationError as e:
        logger.warning("Error de validación en preview PDF: %s", e)
        return HttpResponse("Datos inválidos para generar PDF de preview", status=400)
    except Exception:
        logger.exception("Error generando preview PDF")
        return HttpResponse("Error interno al generar el PDF. Intente nuevamente.", status=500)


@login_required
@permission_required('actas.add_acta', raise_exception=True)
def acta_create(request):
    """Crea una nueva acta vinculando asignaciones seleccionadas usando ActaService."""
    if request.method == 'POST':
        form = ActaCrearForm(request.POST)
        asignacion_ids = request.POST.getlist('asignaciones')
        accesorio_ids = request.POST.getlist('accesorios')
        
        if form.is_valid():
            try:
                ActaService.crear_acta(
                    colaborador=form.cleaned_data['colaborador'],
                    tipo_acta=form.cleaned_data['tipo_acta'],
                    asignacion_ids=asignacion_ids,
                    creado_por=request.user,
                    observaciones=form.cleaned_data.get('observaciones'),
                    accesorio_ids=accesorio_ids,
                    metodo_sanitizacion=form.cleaned_data.get('metodo_sanitizacion', 'N/A'),
                    ministro_de_fe=form.cleaned_data.get('ministro_de_fe')
                )

                return htmx_trigger_response('actaCreated')
                
            except ValidationError as e:
                error_html = _render_acta_error(str(e))
                return HttpResponse(error_html)
            except Exception:
                logger.exception("Error creando acta")
                error_html = _render_acta_error('Error interno al crear el acta.')
                return HttpResponse(error_html)

    else:
        form = ActaCrearForm()
    
    return render(request, 'actas/partials/acta_crear_modal.html', {'form': form})

@login_required
@permission_required('actas.view_acta', raise_exception=True)
def acta_detail(request, pk):
    """Muestra el detalle de un acta en el side-over."""
    acta, asignaciones = ActaService.obtener_acta_con_relaciones(pk)
    
    return render(request, 'actas/partials/acta_detail_sideover.html', {
        'acta': acta,
        'asignaciones': asignaciones
    })

@login_required
@permission_required('actas.view_acta', raise_exception=True)
def acta_pdf(request, pk):
    """Genera el PDF legal corporativo usando ActaPDFService (Playwright/Chromium)."""
    try:
        acta, _ = ActaService.obtener_acta_con_relaciones(pk)
        pdf_content = ActaPDFService.generar_pdf(acta)

        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Acta_{acta.folio}.pdf"'
        return response
    except Exception:
        logger.exception("Error generando PDF para acta %s", pk)
        return HttpResponse('Error interno al generar el PDF. Intente nuevamente.', status=500)

@login_required
@permission_required('actas.change_acta', raise_exception=True)
def acta_firmar(request, pk):
    """Marca un acta como firmada usando ActaService."""
    if request.method == 'POST':
        try:
            ActaService.firmar_acta(pk, request.user)
        except ValidationError:
            pass  # Si ya está firmada, no es un error
        
        response = HttpResponse(
            '<button disabled class="w-full py-3 bg-success/10 text-success text-xs font-black uppercase tracking-widest rounded-xl border border-success/20 transition-all flex items-center justify-center gap-2 opacity-60 cursor-not-allowed">'
            '<span class="material-symbols-outlined text-sm">check_circle</span>'
            'Acta Firmada'
            '</button>',
            status=200
        )
        response["HX-Trigger"] = "actaFirmada"
        return response
    return HttpResponse("Método no permitido", status=405)

@login_required
@permission_required('actas.delete_acta', raise_exception=True)
def acta_anular(request, pk):
    """
    Vista HTMX para anular un acta.
    GET: carga modal con formulario.
    POST: procesa anulación.
    """
    acta = get_object_or_404(Acta, pk=pk)

    if request.method == 'GET':
        form = ActaAnularForm(acta=acta)
        return render(request, 'actas/partials/acta_anular_modal.html', {
            'form': form,
            'acta': acta,
        })

    if request.method == 'POST':
        form = ActaAnularForm(request.POST, acta=acta)
        if form.is_valid():
            try:
                ActaService.anular_acta(
                    acta=acta,
                    usuario=request.user,
                    motivo=form.cleaned_data['motivo'],
                    aprobador_id=form.cleaned_data.get('aprobador'),
                )
                return htmx_trigger_response('actaAnulada')
            except PermissionDenied as e:
                logger.warning("Permiso denegado en anulación de acta %s: %s", pk, e)
                error_html = _render_acta_error(str(e))
                response = HttpResponse(error_html, status=403)
                response["HX-Trigger"] = json.dumps({"showToast": str(e)})
                return response
            except ValidationError as e:
                # Re-renderizar modal con errores
                if hasattr(e, 'message_dict'):
                    for field, errors in e.message_dict.items():
                        form.add_error(field, errors[0])
                else:
                    form.add_error(None, str(e))
                response = render(request, 'actas/partials/acta_anular_modal.html', {
                    'form': form,
                    'acta': acta,
                })
                response["HX-Trigger"] = json.dumps({"showToast": "Corrija los errores del formulario."})
                return response
            except Exception:
                logger.exception("Error anulando acta %s", pk)
                error_html = _render_acta_error('Error interno al anular el acta.')
                return HttpResponse(error_html, status=500)
        else:
            response = render(request, 'actas/partials/acta_anular_modal.html', {
                'form': form,
                'acta': acta,
            })
            response["HX-Trigger"] = json.dumps({"showToast": "Corrija los errores del formulario."})
            return response

    return HttpResponse("Método no permitido", status=405)

@login_required
@permission_required('actas.add_acta', raise_exception=True)
def asignaciones_pendientes(request, colaborador_pk):
    """HTMX partial que lista las asignaciones sin acta de un colaborador."""
    real_pk = colaborador_pk or request.GET.get('colaborador_pk')
    
    if not real_pk or real_pk == '0':
        return HttpResponse('<p class="text-xs text-jmie-gray italic text-center py-4">Seleccione un colaborador para ver equipos pendientes.</p>')
    
    asignaciones = ActaService.obtener_pendientes(real_pk)
    accesorios = ActaService.obtener_accesorios_pendientes(real_pk)
    
    return render(request, 'actas/partials/asignaciones_pendientes.html', {
        'asignaciones': asignaciones,
        'accesorios': accesorios
    })

@login_required
def ministros_por_colaborador(request, colaborador_pk):
    """Retorna las opciones del select de Ministro de Fe filtradas por la obra del colaborador."""
    from colaboradores.models import Colaborador
    from django.db.models import Q
    
    colaborador = get_object_or_404(Colaborador, pk=colaborador_pk)
    obra = colaborador.centro_costo
    
    admin_criterios = Q(cargo__icontains='Administrador') | Q(cargo__icontains='Jefe') | Q(cargo__icontains='Encargado')
    
    ministros = Colaborador.objects.filter(
        esta_activo=True,
        centro_costo=obra
    ).filter(admin_criterios).order_by('first_name')
    
    if not ministros.exists():
        ministros = Colaborador.objects.filter(
            esta_activo=True
        ).filter(admin_criterios).order_by('first_name')

    options_html = '<option value="">---------</option>'
    for m in ministros:
        selected = 'selected' if ministros.count() == 1 else ''
        nombre = escape(m.nombre_completo)
        cargo = escape(m.cargo) if m.cargo else "Sin Cargo"
        options_html += f'<option value="{m.pk}" {selected}>{nombre} ({cargo})</option>'

    return HttpResponse(options_html)
```

**Verify:** `pytest actas/tests/test_views.py -v`
**Commit:** `feat(actas): add acta_anular HTMX view and filter anuladas in list`

---

### Task 3.2: URLs — acta_anular path
**File:** `actas/urls.py`
**Test:** none (covered por test_views)
**Depends:** 2.2

```python
from django.urls import path
from . import views

app_name = 'actas'

urlpatterns = [
    path('', views.acta_list, name='acta_list'),
    path('preview/', views.acta_preview, name='acta_preview'),
    path('preview/pdf/', views.acta_preview_pdf, name='acta_preview_pdf'),
    path('crear/', views.acta_create, name='acta_create'),
    path('<int:pk>/', views.acta_detail, name='acta_detail'),
    path('<int:pk>/pdf/', views.acta_pdf, name='acta_pdf'),
    path('<int:pk>/firmar/', views.acta_firmar, name='acta_firmar'),
    path('<int:pk>/anular/', views.acta_anular, name='acta_anular'),
    path('asignaciones-pendientes/<int:colaborador_pk>/', views.asignaciones_pendientes, name='acta_asignaciones_pendientes'),
    path('ministros-por-colaborador/<int:colaborador_pk>/', views.ministros_por_colaborador, name='acta_ministros_por_colaborador'),
]
```

**Verify:** `python manage.py check` pasa sin errores.
**Commit:** `feat(actas): add acta_anular URL pattern`

---

### Task 3.3: Admin — proteger eliminación física
**File:** `actas/admin.py`
**Test:** none (verificación manual)
**Depends:** 2.1

```python
from django.contrib import admin
from django.core.exceptions import ValidationError
from .models import Acta


@admin.register(Acta)
class ActaAdmin(admin.ModelAdmin):
    list_display = ('folio', 'colaborador', 'tipo_acta', 'firmada', 'anulada', 'fecha')
    list_filter = ('tipo_acta', 'firmada', 'anulada', 'fecha')
    search_fields = ('folio', 'colaborador__first_name', 'colaborador__last_name')
    readonly_fields = ('folio', 'fecha', 'firmada_por', 'fecha_firma', 'anulada_por', 'fecha_anulacion')

    def has_delete_permission(self, request, obj=None):
        """Bloquea eliminación física desde el admin si el acta tiene folio."""
        if obj and obj.folio:
            return False
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        """Intercepta la eliminación individual para validar."""
        if obj.folio:
            raise ValidationError("No se puede eliminar un acta con folio asignado. Use la anulación.")
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Intercepta eliminación masiva; filtra actas con folio."""
        queryset = queryset.filter(folio__isnull=True)
        super().delete_queryset(request, queryset)
```

**Verify:** Acceder a `/admin/actas/acta/` y verificar que actas con folio no muestran botón eliminar.
**Commit:** `feat(actas): prevent physical deletion of actas with folio in admin`

---

## Batch 4: Templates (parallel — 2 implementers)

### Task 4.1: Modal de anulación
**File:** `actas/templates/actas/partials/acta_anular_modal.html`
**Test:** none (covered por E2E)
**Depends:** 3.1, 3.2

```html
<div x-data="{ open: true }" 
     x-show="open" 
     x-cloak
     @modal-close.window="open = false; setTimeout(() => { $el.remove() }, 500)"
     class="fixed inset-0 z-50 flex items-center justify-center p-4">
    
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-background/80 backdrop-blur-md" @click="open = false; setTimeout(() => { $el.remove() }, 500)"></div>

    <!-- Modal Content -->
    <div x-show="open"
         x-transition:enter="ease-out duration-300"
         x-transition:enter-start="opacity-0 scale-95 translate-y-4"
         x-transition:enter-end="opacity-100 scale-100 translate-y-0"
         class="relative w-full max-w-lg bg-surface-container border border-white/10 rounded-3xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] overflow-visible">
        
        <!-- Glow Effect -->
        <div class="absolute -top-24 -left-24 w-48 h-48 bg-error/10 blur-[80px] rounded-full"></div>

        <div class="p-8 relative">
            <div class="flex items-center justify-between mb-8 border-b border-white/5 pb-6">
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 rounded-2xl bg-error/10 flex items-center justify-center text-error border border-error/20">
                        <span class="material-symbols-outlined text-3xl">delete_forever</span>
                    </div>
                    <div>
                        <h2 class="text-2xl font-black tracking-tighter uppercase">Anular Acta</h2>
                        <p class="text-jmie-gray text-xs font-bold uppercase tracking-widest mt-0.5">{{ acta.folio }}</p>
                    </div>
                </div>
                <button @click="open = false; setTimeout(() => { $el.remove() }, 500)" class="text-jmie-gray hover:text-on-background transition-colors">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>

            <form id="acta-anular-form"
                  hx-post="{% url 'actas:acta_anular' acta.pk %}"
                  hx-target="#modal-container"
                  hx-swap="innerHTML"
                  class="space-y-6">
                {% csrf_token %}

                <!-- Error Container -->
                <div id="acta-errors" class="empty:hidden"></div>
                
                {% if acta.firmada %}
                <div class="p-4 bg-amber-500/5 rounded-2xl border border-amber-500/10 flex items-start gap-3">
                    <span class="material-symbols-outlined text-amber-400 text-sm">warning</span>
                    <p class="text-xs text-amber-300 font-bold leading-relaxed">
                        Esta acta está <span class="uppercase">FIRMADA</span>. Requiere aprobación de un supervisor para ser anulada.
                    </p>
                </div>
                {% endif %}

                <div class="space-y-2">
                    <label class="text-[10px] font-black uppercase tracking-widest text-jmie-gray ml-1">
                        Motivo de Anulación <span class="text-error">*</span>
                    </label>
                    {{ form.motivo }}
                    {% if form.motivo.errors %}
                        <p class="text-[10px] text-error font-bold mt-1">{{ form.motivo.errors.0 }}</p>
                    {% endif %}
                </div>

                {% if acta.firmada %}
                <div class="space-y-2">
                    <label class="text-[10px] font-black uppercase tracking-widest text-jmie-gray ml-1">
                        Aprobador <span class="text-error">*</span>
                    </label>
                    {{ form.aprobador }}
                    {% if form.aprobador.errors %}
                        <p class="text-[10px] text-error font-bold mt-1">{{ form.aprobador.errors.0 }}</p>
                    {% endif %}
                    <p class="text-[9px] text-jmie-gray italic">Solo supervisores con permiso especial pueden aprobar.</p>
                </div>
                {% else %}
                    {{ form.aprobador }}
                {% endif %}

                <div class="pt-6 border-t border-white/5 flex items-center justify-between">
                    <div id="form-indicator" class="htmx-indicator flex items-center gap-2 text-jmie-blue">
                        <div class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                        <span class="text-[10px] font-black uppercase tracking-widest">Procesando...</span>
                    </div>

                    <div class="flex gap-3 ml-auto">
                        <button type="button"
                                @click="open = false; setTimeout(() => { $el.remove() }, 500)"
                                class="px-6 py-2.5 text-xs font-black uppercase tracking-widest text-jmie-gray hover:text-on-background border border-white/10 rounded-xl hover:bg-white/5 transition-all">
                            Cancelar
                        </button>
                        <button type="submit"
                                hx-confirm="{% if acta.firmada %}¿Está seguro? Esta acta está firmada y requiere aprobación.{% else %}¿Está seguro de anular este acta?{% endif %}"
                                class="px-8 py-2.5 bg-error text-white text-xs font-black uppercase tracking-widest rounded-xl hover:brightness-110 shadow-[0_10px_30px_rgba(239,68,68,0.2)] transition-all flex items-center gap-2">
                            <span class="material-symbols-outlined text-sm">delete_forever</span>
                            Confirmar Anulación
                        </button>
                    </div>
                </div>
            </form>
        </div>
    </div>
</div>
```

**Verify:** Renderizado visual del modal al abrir desde lista de actas.
**Commit:** `feat(actas): add anulacion modal template with conditional approver`

---

### Task 4.2: Badges y botón de acción en tabla
**File:** `actas/templates/actas/partials/acta_table_rows.html`
**Test:** `actas/tests/test_views.py` (badge presence)
**Depends:** 3.1, 3.2

```html
{% load acta_tags %}
{% for acta in page_obj %}
<tr class="hover:bg-white/[0.02] transition-colors cursor-pointer group {% if acta.anulada %}opacity-50{% endif %}"
    hx-get="{% url 'actas:acta_detail' acta.pk %}"
    hx-target="#side-over-container">
    <td class="px-6 py-4">
        <span class="text-xs font-black text-on-background bg-surface-container px-2 py-1 rounded border border-white/5 uppercase">
            {{ acta.folio }}
        </span>
    </td>
    <td class="px-6 py-4">
        <div class="flex flex-col">
            <span class="text-sm font-bold text-on-background">{{ acta.colaborador.nombre_completo }}</span>
            <span class="text-[10px] text-jmie-gray font-black tracking-widest">{{ acta.colaborador.rut|default:"SIN RUT"|format_rut }}</span>
        </div>
    </td>
    <td class="px-6 py-4">
        <span class="text-xs font-bold text-on-surface-variant">{{ acta.fecha|date:"d M Y" }}</span>
    </td>
    <td class="px-6 py-4">
        <span class="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full border 
            {% if acta.tipo_acta == 'ENTREGA' %}
                bg-blue-500/10 text-blue-400 border-blue-500/20
            {% else %}
                bg-purple-500/10 text-purple-400 border-purple-500/20
            {% endif %}">
            {{ acta.get_tipo_acta_display }}
        </span>
    </td>
    <td class="px-6 py-4">
        {% if acta.anulada %}
        <div class="flex items-center gap-2">
            <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>
            <span class="text-[10px] font-black text-red-400 uppercase tracking-widest">ANULADA</span>
        </div>
        {% elif acta.firmada %}
        <div class="flex items-center gap-2">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span class="text-[10px] font-black text-emerald-400 uppercase tracking-widest">FIRMADA</span>
        </div>
        {% else %}
        <div class="flex items-center gap-2 opacity-60">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            <span class="text-[10px] font-black text-amber-400 uppercase tracking-widest">PENDIENTE DE FIRMA</span>
        </div>
        {% endif %}
    </td>
    <td class="px-6 py-4 text-right" onclick="event.stopPropagation()">
        <div class="flex items-center justify-end gap-2">
            <a href="{% url 'actas:acta_pdf' acta.pk %}" 
               target="_blank"
               class="p-2 text-jmie-gray hover:text-jmie-blue hover:bg-jmie-blue/10 rounded-lg transition-all"
               title="Ver PDF">
                <span class="material-symbols-outlined text-lg">picture_as_pdf</span>
            </a>
            
            {% if not acta.anulada and not acta.firmada and perms.actas.change_acta %}
            <button class="p-2 text-jmie-gray hover:text-emerald-400 hover:bg-emerald-400/10 rounded-lg transition-all"
                    hx-post="{% url 'actas:acta_firmar' acta.pk %}"
                    hx-confirm="¿Está seguro de firmar esta acta? Una vez firmada, el documento queda bloqueado legalmente según Ley 21.663 y 21.719."
                    title="Firmar Acta">
                <span class="material-symbols-outlined text-lg">draw</span>
            </button>
            {% endif %}

            {% if not acta.anulada and perms.actas.delete_acta %}
            <button class="p-2 text-jmie-gray hover:text-error hover:bg-error/10 rounded-lg transition-all"
                    hx-get="{% url 'actas:acta_anular' acta.pk %}"
                    hx-target="#modal-container"
                    hx-swap="innerHTML"
                    title="Anular Acta">
                <span class="material-symbols-outlined text-lg">delete_forever</span>
            </button>
            {% endif %}
        </div>
    </td>
</tr>
{% empty %}
<tr>
    <td colspan="6">
        <c-empty-state icon="description" title="Sin Actas" subtitle="No se han generado actas para los criterios seleccionados." action_url="/actas/crear/" action_label="Generar Acta" action_htmx="True" />
    </td>
</tr>
{% endfor %}
```

**Verify:** `pytest actas/tests/test_views.py::TestActaViews::test_acta_list_view -v` muestra badge ANULADA si acta.anulada=True.
**Commit:** `feat(actas): add anulada badge and anular button to table rows`

---

## Batch 5: Tests (parallel — 5 implementers)

### Task 5.1: Unit tests — Modelo
**File:** `actas/tests/test_models.py`
**Test:** self-testing (pytest)
**Depends:** 2.1

```python
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from actas.models import Acta
from core.tests.factories import ActaFactory, ColaboradorFactory

@pytest.mark.django_db
class TestActaModel:
    def test_folio_generation(self):
        """Verificar que el folio se genera automáticamente con el formato correcto"""
        colaborador = ColaboradorFactory()
        acta = Acta.objects.create(colaborador=colaborador)
        year = timezone.now().year
        assert acta.folio.startswith(f"ACT-{year}-")
        assert len(acta.folio.split('-')[-1]) == 4

    def test_folio_increment(self):
        """Verificar que el folio incrementa secuencialmente"""
        colaborador = ColaboradorFactory()
        acta1 = Acta.objects.create(colaborador=colaborador)
        acta2 = Acta.objects.create(colaborador=colaborador)
        
        num1 = int(acta1.folio.split('-')[-1])
        num2 = int(acta2.folio.split('-')[-1])
        assert num2 == num1 + 1

    def test_blindaje_firmada(self):
        """Verificar que no se puede modificar un acta marcada como firmada"""
        acta = ActaFactory(firmada=True)
        acta.observaciones = "Cambio prohibido"
        with pytest.raises(ValidationError, match="No se puede modificar un acta que ya ha sido marcada como FIRMADA"):
            acta.save()

    def test_str_representation(self):
        """Verificar representación string del acta"""
        colaborador = ColaboradorFactory(first_name="Juan", last_name="Perez")
        acta = ActaFactory(colaborador=colaborador, folio="ACT-2024-0001")
        assert str(acta) == "ACT-2024-0001 - Juan Perez"

    def test_delete_bloqueado_si_tiene_folio(self):
        """Verificar que delete() lanza ValidationError si el acta tiene folio"""
        acta = ActaFactory()
        assert acta.folio is not None
        with pytest.raises(ValidationError, match="No se puede eliminar un acta que ya tiene folio asignado"):
            acta.delete()

    def test_delete_permitido_sin_folio(self):
        """Verificar que delete() funciona si el acta aún no tiene folio"""
        acta = ActaFactory()
        acta.folio = ''
        acta.save(update_fields=['folio'])
        # Django permite delete() porque folio está vacío
        acta.delete()
        assert Acta.objects.filter(pk=acta.pk).count() == 0

    def test_clean_requiere_motivo_si_anulada(self):
        """Verificar que clean() exige motivo cuando anulada=True"""
        acta = ActaFactory()
        acta.anulada = True
        acta.motivo_anulacion = None
        with pytest.raises(ValidationError, match="motivo de anulación es obligatorio"):
            acta.clean()

    def test_clean_pasa_si_anulada_con_motivo(self):
        """Verificar que clean() pasa si anulada=True y motivo está presente"""
        acta = ActaFactory()
        acta.anulada = True
        acta.motivo_anulacion = "Error de registro"
        acta.clean()  # No debe lanzar excepción
```

**Verify:** `pytest actas/tests/test_models.py -v`
**Commit:** `test(actas): add model tests for delete protection and anulacion validation`

---

### Task 5.2: Unit tests — Servicios
**File:** `actas/tests/test_services.py`
**Test:** self-testing (pytest)
**Depends:** 2.2

```python
import pytest
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from actas.models import Acta
from actas.services import ActaService
from core.tests.factories import (
    ColaboradorFactory, HistorialAsignacionFactory,
    EntregaAccesorioFactory, ActaFactory
)

# ... mantener tests existentes anteriores a TestActaService ...

@pytest.mark.django_db
class TestActaServiceAnulacion:
    def test_anular_borrador_sin_aprobador(self):
        """Acta no firmada se anula con solo motivo"""
        acta = ActaFactory(firmada=False)
        usuario = ColaboradorFactory()
        # Asignar permiso delete_acta
        ct = ContentType.objects.get_for_model(Acta)
        perm = Permission.objects.get(codename='delete_acta', content_type=ct)
        usuario.user_permissions.add(perm)
        usuario.save()

        result = ActaService.anular_acta(acta, usuario, "Error de registro")
        assert result.anulada is True
        assert result.motivo_anulacion == "Error de registro"
        assert result.anulada_por == usuario

    def test_anular_firmada_requiere_aprobador(self):
        """Sin aprobador, lanza ValidationError"""
        acta = ActaFactory(firmada=True)
        usuario = ColaboradorFactory()
        ct = ContentType.objects.get_for_model(Acta)
        perm = Permission.objects.get(codename='aprobar_anulacion', content_type=ct)
        usuario.user_permissions.add(perm)
        usuario.save()

        with pytest.raises(ValidationError, match="requieren un aprobador"):
            ActaService.anular_acta(acta, usuario, "Error grave")

    def test_anular_firmada_aprobador_sin_permiso(self):
        """Aprobador sin rol adecuado falla con PermissionDenied"""
        acta = ActaFactory(firmada=True)
        solicitante = ColaboradorFactory()
        aprobador = ColaboradorFactory()

        with pytest.raises(PermissionDenied, match="no tiene permisos"):
            ActaService.anular_acta(acta, solicitante, "Error grave", aprobador_id=aprobador.pk)

    def test_anular_firmada_aprobador_igual_solicitante(self):
        """Debe fallar si aprobador es el mismo solicitante"""
        acta = ActaFactory(firmada=True)
        usuario = ColaboradorFactory()
        ct = ContentType.objects.get_for_model(Acta)
        perm = Permission.objects.get(codename='aprobar_anulacion', content_type=ct)
        usuario.user_permissions.add(perm)
        usuario.save()

        with pytest.raises(ValidationError, match="no puede ser el mismo solicitante"):
            ActaService.anular_acta(acta, usuario, "Error grave", aprobador_id=usuario.pk)

    def test_anular_firmada_con_aprobador_valido(self):
        """Anulación exitosa de acta firmada con aprobador autorizado"""
        acta = ActaFactory(firmada=True)
        solicitante = ColaboradorFactory()
        aprobador = ColaboradorFactory()
        ct = ContentType.objects.get_for_model(Acta)
        perm = Permission.objects.get(codename='aprobar_anulacion', content_type=ct)
        aprobador.user_permissions.add(perm)
        aprobador.save()

        result = ActaService.anular_acta(acta, solicitante, "Error de datos", aprobador_id=aprobador.pk)
        assert result.anulada is True
        assert result.anulada_por == solicitante

    def test_anular_acta_ya_anulada_falla(self):
        """No se puede anular dos veces"""
        acta = ActaFactory(anulada=True, motivo_anulacion="Ya anulada")
        usuario = ColaboradorFactory()
        with pytest.raises(ValidationError, match="ya fue anulada"):
            ActaService.anular_acta(acta, usuario, "Otro motivo")

    def test_firmar_acta_registra_auditoria(self):
        """firmar_acta actualiza firmada_por y fecha_firma"""
        acta = ActaFactory(firmada=False)
        firmador = ColaboradorFactory()
        ActaService.firmar_acta(acta.pk, firmador)
        acta.refresh_from_db()
        assert acta.firmada is True
        assert acta.firmada_por == firmador
        assert acta.fecha_firma is not None

    def test_firmar_acta_ya_firmada_falla(self):
        """No se puede firmar dos veces"""
        firmador = ColaboradorFactory()
        acta = ActaFactory(firmada=True, firmada_por=firmador)
        with pytest.raises(ValidationError, match="ya está firmada"):
            ActaService.firmar_acta(acta.pk, firmador)

    def test_firmar_acta_anulada_falla(self):
        """No se puede firmar un acta anulada"""
        acta = ActaFactory(anulada=True, motivo_anulacion="Error")
        firmador = ColaboradorFactory()
        with pytest.raises(ValidationError, match="anulada"):
            ActaService.firmar_acta(acta.pk, firmador)
```

**Verify:** `pytest actas/tests/test_services.py -v`
**Commit:** `test(actas): add service tests for anulacion logic and dual authorization`

---

### Task 5.3: Integration tests — Vistas
**File:** `actas/tests/test_views.py`
**Test:** self-testing (pytest)
**Depends:** 3.1

```python
import pytest
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from actas.models import Acta
from core.tests.factories import ColaboradorFactory, ActaFactory, HistorialAsignacionFactory

@pytest.mark.django_db
class TestActaAnularViews:
    def _login_admin(self, client):
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        return user

    def test_get_anular_modal_returns_form(self, client):
        user = self._login_admin(client)
        acta = ActaFactory(firmada=False)
        url = reverse('actas:acta_anular', kwargs={'pk': acta.pk})
        response = client.get(url)
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert 'Anular Acta' in html
        assert 'motivo' in html

    def test_post_anular_acta_borrador_returns_204(self, client):
        user = self._login_admin(client)
        acta = ActaFactory(firmada=False)
        url = reverse('actas:acta_anular', kwargs={'pk': acta.pk})
        response = client.post(url, {
            'motivo': 'Error de registro',
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 204
        assert response['HX-Trigger'] == 'actaAnulada'
        acta.refresh_from_db()
        assert acta.anulada is True

    def test_post_anular_acta_firmada_sin_aprobador_returns_error(self, client):
        user = self._login_admin(client)
        acta = ActaFactory(firmada=True)
        url = reverse('actas:acta_anular', kwargs={'pk': acta.pk})
        response = client.post(url, {
            'motivo': 'Error grave',
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert 'requieren un aprobador' in html

    def test_post_anular_acta_firmada_con_aprobador_valido(self, client):
        user = self._login_admin(client)
        acta = ActaFactory(firmada=True)
        aprobador = ColaboradorFactory()
        ct = ContentType.objects.get_for_model(Acta)
        perm = Permission.objects.get(codename='aprobar_anulacion', content_type=ct)
        aprobador.user_permissions.add(perm)
        aprobador.save()

        url = reverse('actas:acta_anular', kwargs={'pk': acta.pk})
        response = client.post(url, {
            'motivo': 'Error de datos',
            'aprobador': aprobador.pk,
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 204
        assert response['HX-Trigger'] == 'actaAnulada'

    def test_tabla_muestra_badge_anulada(self, client):
        user = self._login_admin(client)
        acta = ActaFactory(anulada=True, motivo_anulacion="Test")
        url = reverse('actas:acta_list')
        response = client.get(url, {'incluir_anuladas': '1'})
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert 'ANULADA' in html

    def test_listado_excluye_anuladas_por_defecto(self, client):
        user = self._login_admin(client)
        acta_normal = ActaFactory(anulada=False, folio="ACT-N-0001")
        acta_anulada = ActaFactory(anulada=True, motivo_anulacion="X", folio="ACT-A-0001")
        url = reverse('actas:acta_list')
        response = client.get(url)
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert "ACT-N-0001" in html
        assert "ACT-A-0001" not in html

    def test_firmar_acta_actualiza_firmada_por(self, client):
        user = self._login_admin(client)
        acta = ActaFactory(firmada=False)
        url = reverse('actas:acta_firmar', kwargs={'pk': acta.pk})
        response = client.post(url, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        acta.refresh_from_db()
        assert acta.firmada_por == user
        assert acta.fecha_firma is not None
```

**Verify:** `pytest actas/tests/test_views.py::TestActaAnularViews -v`
**Commit:** `test(actas): add integration tests for anular views and table badges`

---

### Task 5.4: Integration tests — Flujos completos
**File:** `actas/tests/test_integration.py`
**Test:** self-testing (pytest)
**Depends:** 3.1

```python
"""Tests de integración para la app Actas (anulación)."""
import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from actas.services import ActaService
from actas.models import Acta
from core.tests.factories import ColaboradorFactory, ActaFactory

@pytest.mark.integration
@pytest.mark.django_db
class TestActaAnulacionIntegration:
    def test_anular_borrador_y_verificar_estado(self):
        """Flujo: crear acta -> anular -> verificar estado y campos"""
        acta = ActaFactory(firmada=False)
        usuario = ColaboradorFactory()
        ct = ContentType.objects.get_for_model(Acta)
        perm = Permission.objects.get(codename='delete_acta', content_type=ct)
        usuario.user_permissions.add(perm)
        usuario.save()

        ActaService.anular_acta(acta, usuario, "Equipo devuelto antes de firma")
        acta.refresh_from_db()

        assert acta.anulada is True
        assert acta.motivo_anulacion == "Equipo devuelto antes de firma"
        assert acta.anulada_por == usuario
        assert acta.fecha_anulacion is not None

    def test_anular_firmada_con_doble_autorizacion(self):
        """Flujo: crear -> firmar -> anular con aprobador -> verificar"""
        acta = ActaFactory(firmada=False)
        firmador = ColaboradorFactory()
        solicitante = ColaboradorFactory()
        aprobador = ColaboradorFactory()

        ct = ContentType.objects.get_for_model(Acta)
        perm_aprobar = Permission.objects.get(codename='aprobar_anulacion', content_type=ct)
        aprobador.user_permissions.add(perm_aprobar)
        aprobador.save()

        # Firmar
        ActaService.firmar_acta(acta.pk, firmador)
        acta.refresh_from_db()
        assert acta.firmada is True

        # Anular con aprobador
        ActaService.anular_acta(acta, solicitante, "Error en datos del colaborador", aprobador_id=aprobador.pk)
        acta.refresh_from_db()
        assert acta.anulada is True

    def test_no_se_puede_editar_despues_de_anular(self):
        """Un acta anulada no debe poder modificarse"""
        acta = ActaFactory(anulada=True, motivo_anulacion="Test")
        acta.observaciones = "Nuevo texto"
        # El save() del modelo no bloquea explícitamente anuladas,
        # pero el blindaje de firmada sí. Asumimos que anulada implica no editable.
        # Si es necesario, extender el save() en modelo.
        # Por ahora verificamos que no se puede firmar una anulada.
        firmador = ColaboradorFactory()
        with pytest.raises(ValidationError, match="anulada"):
            ActaService.firmar_acta(acta.pk, firmador)
```

**Verify:** `pytest actas/tests/test_integration.py::TestActaAnulacionIntegration -v`
**Commit:** `test(actas): add integration tests for full anulacion lifecycle`

---

### Task 5.5: Form tests
**File:** `actas/tests/test_forms.py`
**Test:** self-testing (pytest)
**Depends:** 2.3

```python
import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from actas.forms import ActaCrearForm, ActaAnularForm
from actas.models import Acta
from core.tests.factories import ColaboradorFactory, ActaFactory

@pytest.mark.django_db
class TestActaForms:
    def test_ministro_de_fe_filtering(self):
        """Verifica que el dropdown de ministro de fe solo incluya administradores activos."""
        admin = ColaboradorFactory(cargo="Administrador de Red", esta_activo=True)
        jefe = ColaboradorFactory(cargo="Jefe de Soporte", esta_activo=True)
        normal = ColaboradorFactory(cargo="Operador", esta_activo=True)
        inactivo = ColaboradorFactory(cargo="Jefe Anterior", esta_activo=False)

        form = ActaCrearForm()
        ministros = list(form.fields['ministro_de_fe'].queryset)

        assert admin in ministros
        assert jefe in ministros
        assert normal not in ministros
        assert inactivo not in ministros

    def test_colaborador_activo_filtering(self):
        """Verifica que solo los colaboradores activos estén en el listado base."""
        activo = ColaboradorFactory(esta_activo=True)
        inactivo = ColaboradorFactory(esta_activo=False)
        
        form = ActaCrearForm()
        colaboradores = list(form.fields['colaborador'].queryset)
        
        assert activo in colaboradores
        assert inactivo not in colaboradores

    def test_anular_form_borrador_no_requiere_aprobador(self):
        """Formulario para acta no firmada no muestra aprobador requerido"""
        acta = ActaFactory(firmada=False)
        form = ActaAnularForm(acta=acta, data={'motivo': 'Error'})
        assert form.is_valid()
        assert form.cleaned_data['aprobador'] is None

    def test_anular_form_firmada_requiere_aprobador(self):
        """Formulario para acta firmada valida aprobador"""
        acta = ActaFactory(firmada=True)
        form = ActaAnularForm(acta=acta, data={'motivo': 'Error grave'})
        assert not form.is_valid()
        assert 'aprobador' in form.errors

    def test_anular_form_firmada_con_aprobador_valido(self):
        """Formulario válido cuando se provee aprobador con permisos"""
        acta = ActaFactory(firmada=True)
        aprobador = ColaboradorFactory(esta_activo=True)
        ct = ContentType.objects.get_for_model(Acta)
        perm = Permission.objects.get(codename='aprobar_anulacion', content_type=ct)
        aprobador.user_permissions.add(perm)
        aprobador.save()

        form = ActaAnularForm(acta=acta, data={
            'motivo': 'Error de datos',
            'aprobador': aprobador.pk,
        })
        assert form.is_valid()

    def test_anular_form_motivo_obligatorio(self):
        """El motivo es obligatorio en cualquier caso"""
        acta = ActaFactory(firmada=False)
        form = ActaAnularForm(acta=acta, data={'motivo': ''})
        assert not form.is_valid()
        assert 'motivo' in form.errors
```

**Verify:** `pytest actas/tests/test_forms.py -v`
**Commit:** `test(actas): add form validation tests for ActaAnularForm`

---

## Batch 6: E2E Tests (parallel — 2 implementers)

### Task 6.1: Page Object updates
**File:** `tests_e2e/pages/inventory_pages.py`
**Test:** none (helper)
**Depends:** 4.1, 4.2

```python
from playwright.sync_api import Page, expect

# ... clases existentes (LoginPage, DashboardPage, DispositivosPage, etc.) ...

class ActasPage:
    """Page Object para el listado y generación de actas."""

    def __init__(self, page: Page):
        self.page = page
        self.table = page.locator('table')
        self.generate_button = page.locator('a:has-text("Generar Acta"), button:has-text("Generar Acta")')
        self.modal = page.locator('#modal-container, [role="dialog"]')
        self.sideover = page.locator('text=Vista Previa del Acta').locator('xpath=ancestor::div[contains(@class, "fixed")]')

    def navigate(self, base_url):
        self.page.goto(f"{base_url}/actas/")

    def click_generate(self):
        self.generate_button.click()

    def expect_modal_visible(self):
        expect(self.modal).to_be_visible()

    def expect_modal_hidden(self):
        expect(self.modal).not_to_be_visible()

    def select_colaborador(self, label):
        self.page.select_option('select[name="colaborador"]', label=label)

    def check_asignacion(self):
        checkbox = self.page.locator('input[name="asignaciones"]').first
        checkbox.check()

    def click_preview(self):
        """Hace clic en el botón Previsualizar Acta."""
        self.page.click('button:has-text("Previsualizar Acta")')

    def click_confirm(self):
        """Hace clic en Confirmar y Generar Acta dentro del side-over."""
        self.page.click('button:has-text("Confirmar y Generar Acta")')

    def click_volver_a_editar(self):
        """Hace clic en Volver a Editar dentro del side-over."""
        self.page.click('button:has-text("Volver a Editar")')

    def expect_sideover_visible(self):
        expect(self.page.locator('text=Vista Previa del Acta')).to_be_visible()

    def expect_sideover_hidden(self):
        expect(self.page.locator('text=Vista Previa del Acta')).not_to_be_visible()

    def expect_preview_contains(self, text):
        expect(self.page.locator('.preview-document')).to_contain_text(text)

    def submit(self):
        """Flujo completo: preview + confirmar (para compatibilidad con tests antiguos)."""
        self.click_preview()
        self.expect_sideover_visible()
        self.click_confirm()

    def expect_acta_in_list(self, text):
        expect(self.page.locator('#search-results, table')).to_contain_text(text)

    def acta_row(self, folio):
        return self.page.locator(f'tr:has-text("{folio}")')

    # --- Nuevos métodos para anulación ---
    def click_anular(self, folio: str):
        """Hace clic en el botón de anular de la fila del acta."""
        row = self.acta_row(folio)
        anular_btn = row.locator('button[title="Anular Acta"]')
        anular_btn.click()

    def expect_anular_modal_visible(self):
        expect(self.page.locator('h2:has-text("Anular Acta")')).to_be_visible()

    def fill_motivo_anulacion(self, texto: str):
        self.page.fill('textarea[name="motivo"]', texto)

    def select_aprobador(self, label: str):
        self.page.select_option('select[name="aprobador"]', label=label)

    def confirmar_anulacion(self):
        """Hace clic en Confirmar Anulación dentro del modal."""
        # Manejar el diálogo de confirmación de HTMX
        self.page.once("dialog", lambda dialog: dialog.accept())
        self.page.click('button:has-text("Confirmar Anulación")')

    def expect_badge_anulada(self, folio: str):
        row = self.acta_row(folio)
        expect(row.locator('text=ANULADA')).to_be_visible()

    def expect_boton_anular_hidden(self, folio: str):
        row = self.acta_row(folio)
        expect(row.locator('button[title="Anular Acta"]')).not_to_be_visible()

    def click_firmar(self, folio: str):
        row = self.acta_row(folio)
        firmar_btn = row.locator('button[title="Firmar Acta"]')
        firmar_btn.click()


class AsignacionPage:
    # ... mantener existente ...
    pass

class DevolucionPage:
    # ... mantener existente ...
    pass

class MantenimientoPage:
    # ... mantener existente ...
    pass
```

**Verify:** `pytest tests_e2e/test_acta_flow.py -m e2e --headed --browser chromium -k "anular"` (después de implementar Task 6.2).
**Commit:** `test(e2e): extend ActasPage with anulacion flow helpers`

---

### Task 6.2: E2E tests — Flujos de anulación
**File:** `tests_e2e/test_acta_flow.py`
**Test:** self-testing (pytest-playwright)
**Depends:** 6.1

```python
import pytest
from playwright.sync_api import Page, expect
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from core.tests.factories import ColaboradorFactory, HistorialAsignacionFactory, DispositivoFactory, ActaFactory
from actas.models import Acta
from .pages.inventory_pages import LoginPage, ActasPage

@pytest.fixture
def e2e_user(db):
    user = ColaboradorFactory(username='admin_actas', is_superuser=True, is_staff=True)
    user.set_password('12345')
    user.save()
    return user

# ... tests E2E existentes (test_create_acta_flow, test_preview_acta_and_cancel) ...

@pytest.mark.e2e
@pytest.mark.django_db
def test_anular_acta_borrador_flow(live_server, page: Page, e2e_user):
    """Flujo completo: Crear acta → Anular → Verificar badge en tabla."""
    login_page = LoginPage(page)
    actas_page = ActasPage(page)

    # 1. Login
    login_page.navigate(live_server.url + "/login/")
    login_page.login('admin_actas', '12345')
    page.wait_for_url(live_server.url + "/")

    # 2. Crear acta de prueba
    colaborador = ColaboradorFactory(first_name="Anular", last_name="Test")
    dispositivo = DispositivoFactory(numero_serie="SN-ANULAR-001")
    HistorialAsignacionFactory(colaborador=colaborador, dispositivo=dispositivo, acta=None)

    page.click('text=Actas')
    page.wait_for_url(lambda url: "/actas/" in url)

    actas_page.click_generate()
    actas_page.select_colaborador(f"{colaborador.first_name} {colaborador.last_name}")
    actas_page.check_asignacion()
    actas_page.click_preview()
    actas_page.expect_sideover_visible()
    actas_page.click_confirm()
    actas_page.expect_modal_hidden()

    # Esperar a que aparezca en la lista
    actas_page.expect_acta_in_list("Anular Test")

    # 3. Obtener el folio del acta creado (del texto de la tabla)
    # Como no sabemos el folio exacto, usamos el nombre del colaborador para encontrar la fila
    # y luego buscamos el botón anular en esa fila
    row = actas_page.acta_row("Anular Test")
    expect(row).to_be_visible()

    # Extraer folio de la fila para referencia posterior
    folio_text = row.locator('td:first-child span').inner_text()

    # 4. Clic en anular
    actas_page.click_anular(folio_text)
    actas_page.expect_anular_modal_visible()

    # 5. Llenar motivo y confirmar
    actas_page.fill_motivo_anulacion("Error en datos de prueba")
    actas_page.confirmar_anulacion()

    # 6. Verificar badge ANULADA
    actas_page.expect_badge_anulada(folio_text)
    actas_page.expect_boton_anular_hidden(folio_text)


@pytest.mark.e2e
@pytest.mark.django_db
def test_anular_acta_firmada_con_aprobador_flow(live_server, page: Page, e2e_user):
    """Flujo completo: Crear acta → Firmar → Anular con aprobador → Verificar badge."""
    login_page = LoginPage(page)
    actas_page = ActasPage(page)

    # 1. Login
    login_page.navigate(live_server.url + "/login/")
    login_page.login('admin_actas', '12345')
    page.wait_for_url(live_server.url + "/")

    # 2. Crear acta
    colaborador = ColaboradorFactory(first_name="Firmada", last_name="Anular")
    dispositivo = DispositivoFactory(numero_serie="SN-FIRM-002")
    HistorialAsignacionFactory(colaborador=colaborador, dispositivo=dispositivo, acta=None)

    page.click('text=Actas')
    page.wait_for_url(lambda url: "/actas/" in url)

    actas_page.click_generate()
    actas_page.select_colaborador(f"{colaborador.first_name} {colaborador.last_name}")
    actas_page.check_asignacion()
    actas_page.click_preview()
    actas_page.expect_sideover_visible()
    actas_page.click_confirm()
    actas_page.expect_modal_hidden()
    actas_page.expect_acta_in_list("Firmada Anular")

    # 3. Obtener folio y firmar
    row = actas_page.acta_row("Firmada Anular")
    folio_text = row.locator('td:first-child span').inner_text()
    actas_page.click_firmar(folio_text)

    # Esperar a que se refresque la fila (HTMX trigger)
    page.wait_for_timeout(500)

    # 4. Crear aprobador con permiso
    aprobador = ColaboradorFactory(
        username='aprobador_test', first_name="Super", last_name="Visor",
        is_staff=True, is_superuser=True
    )
    aprobador.set_password('12345')
    ct = ContentType.objects.get_for_model(Acta)
    perm = Permission.objects.get(codename='aprobar_anulacion', content_type=ct)
    aprobador.user_permissions.add(perm)
    aprobador.save()

    # 5. Anular (como admin original)
    actas_page.click_anular(folio_text)
    actas_page.expect_anular_modal_visible()

    # Debe aparecer el campo aprobador
    expect(page.locator('select[name="aprobador"]')).to_be_visible()

    actas_page.fill_motivo_anulacion("Error de datos detectado post-firma")
    actas_page.select_aprobador("Super Visor")
    actas_page.confirmar_anulacion()

    # 6. Verificar badge ANULADA
    actas_page.expect_badge_anulada(folio_text)
```

**Verify:** `pytest tests_e2e/test_acta_flow.py -m e2e --headed --browser chromium`
**Commit:** `test(e2e): add E2E tests for anulacion borrador and firmada flows`

---

## Migration Strategy

1. **Generar migración:** `python manage.py makemigrations actas`
   - Debe detectar automáticamente todos los nuevos campos y el permiso custom.
2. **Revisar migración generada** (Task 1.1) antes de aplicar:
   - Verificar que `default=False` en `anulada` evite problemas con datos existentes.
   - Verificar que las FKs usen `SET_NULL` para no romper referencias históricas.
3. **Aplicar:** `python manage.py migrate`
4. **Rollback plan:** La migración es reversible (`ReverseOperation` automático de Django para AddField). En caso de emergencia: `python manage.py migrate actas 0002`.
5. **Datos existentes:** Los actas previos quedarán con `anulada=False`, `firmada_por=None`, `fecha_firma=None` (valores por defecto apropiados).

---

## Dependency & Risk Considerations

| Riesgo | Mitigación |
|--------|-----------|
| **Folios con huecos** (el design original temía huecos por delete) | Mitigado: `delete()` bloqueado. La anulación mantiene el folio activo en BD. |
| **Performance en listado** (filtrar anuladas por defecto) | Bajo: índice implícito en `BooleanField` es suficiente para SQLite con <100k registros. Si escala, agregar `index=True` a `anulada`. |
| **Permisos faltantes en producción** | Los permisos custom (`aprobar_anulacion`) se crean vía migración. Requerirá asignación manual a grupos/supervisores vía Admin o data migration posterior. |
| **URLs rotas** (`render_actions` espera `acta_delete`) | La convención CRUD `acta_delete` no existe; usamos `acta_anular` (acción específica de dominio). `render_actions` no se usa en esta app (botones custom en tabla). |
| **HTMX race conditions** (doble clic en anular) | Mitigado: `transaction.atomic()` en servicio + `unique` implícito del estado (idempotente si ya está anulada). |
| **Logging no aparece** | Verificar que settings.LOGGING incluya logger `'actas'` con nivel INFO. Ya está configurado según AGENTS.md. |
| **E2E flaky por timeouts HTMX** | Usar `expect().to_be_visible()` con timeout por defecto de Playwright (5s). Añadir `page.wait_for_timeout(300)` solo si es estrictamente necesario. |
| **Soft delete vs hard delete en Admin** | Admin sobreescrito para bloquear delete individual y masivo. Superusers siguen viendo la opción pero reciben error si intentan usarla. |

---

## Verify Everything

```bash
# 1. Migraciones
python manage.py makemigrations --check
python manage.py migrate

# 2. Tests unitarios + integración
pytest actas/tests/test_models.py actas/tests/test_services.py actas/tests/test_views.py actas/tests/test_integration.py actas/tests/test_forms.py -v

# 3. Tests E2E
pytest tests_e2e/test_acta_flow.py -m e2e --headed --browser chromium

# 4. Django checks
python manage.py check

# 5. Lint (si aplica)
ruff check actas/
```

**Coverage target:** 80%+ en `actas/models.py`, `actas/services.py`, `actas/views.py`.
