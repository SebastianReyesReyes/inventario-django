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

    def save(self, *args, **kwargs):
        if self.firmada and self.pk:
            # Blindaje: Si ya existe y está firmada, impedimos cualquier cambio
            existente = Acta.objects.get(pk=self.pk)
            if existente.firmada:
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

    def __str__(self):
        return f"{self.folio} - {self.colaborador}"

    class Meta:
        verbose_name = "Acta"
        verbose_name_plural = "Actas"


# Modelos HistorialAsignacion y EntregaAccesorio movidos a dispositivos/models.py 
# según la nueva arquitectura de mini-apps para trazabilidad.
