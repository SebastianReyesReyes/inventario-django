from django.db import models
from django.urls import reverse
from core.models import TipoDispositivo, EstadoDispositivo, Modelo, CentroCosto
from colaboradores.models import Colaborador
from django.core.exceptions import ValidationError
from django.utils import timezone

class DispositivoQuerySet(models.QuerySet):
    def activos(self):
        return self.exclude(estado__nombre='Fuera de Inventario')
    
    def con_detalles(self):
        return self.select_related(
            'tipo', 'estado', 'modelo', 'modelo__fabricante', 
            'propietario_actual', 'centro_costo'
        )

class Dispositivo(models.Model):
    identificador_interno = models.CharField(max_length=50, unique=True, blank=True, verbose_name="ID Interno (Auto)")
    numero_serie = models.CharField(max_length=100, unique=True, verbose_name="Número de Serie")
    
    tipo = models.ForeignKey(TipoDispositivo, on_delete=models.PROTECT)
    estado = models.ForeignKey(EstadoDispositivo, on_delete=models.PROTECT)
    modelo = models.ForeignKey(Modelo, on_delete=models.PROTECT)
    
    propietario_actual = models.ForeignKey(Colaborador, on_delete=models.SET_NULL, null=True, blank=True, related_name="equipos_asignados")
    centro_costo = models.ForeignKey(CentroCosto, on_delete=models.PROTECT)
    
    fecha_compra = models.DateField(null=True, blank=True)
    valor_contable = models.PositiveIntegerField(default=0, help_text="Valor en pesos chilenos")
    
    notas_condicion = models.TextField(verbose_name="Condición Física", help_text="Detallar rayas, golpes o desgaste")
    foto_equipo = models.ImageField(upload_to='dispositivos/fotos/', null=True, blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    objects = DispositivoQuerySet.as_manager()

    def clean(self):
        if self.fecha_compra and self.fecha_compra > timezone.now().date():
            raise ValidationError({'fecha_compra': "La fecha de compra no puede ser futura."})
        if self.valor_contable and self.valor_contable < 0:
            raise ValidationError({'valor_contable': "El valor contable debe ser positivo."})

    def save(self, *args, **kwargs):
        if not self.identificador_interno:
            prefix = "JMIE"
            # Obtenemos la sigla del tipo de dispositivo
            sigla = self.tipo.sigla if self.tipo and self.tipo.sigla else "EQUIP"
            
            # Buscamos el último dispositivo con la misma sigla para seguir la secuencia
            last_device = Dispositivo.objects.filter(
                identificador_interno__startswith=f"{prefix}-{sigla}-"
            ).order_by('identificador_interno').last()
            
            if last_device:
                try:
                    # JMIE-SIGLA-00001 -> '00001'
                    last_num_str = last_device.identificador_interno.split('-')[-1]
                    new_num = int(last_num_str) + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1
            
            self.identificador_interno = f"{prefix}-{sigla}-{new_num:05d}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.identificador_interno} - {self.modelo}"

    def get_absolute_url(self):
        return reverse('dispositivos:dispositivo_detail', kwargs={'pk': self.pk})

    class Meta:
        verbose_name = "Dispositivo"
        verbose_name_plural = "Dispositivos"
        constraints = [
            models.CheckConstraint(condition=models.Q(valor_contable__gte=0), name='valor_contable_positivo')
        ]

# --- Modelos Especializados (Herencia) ---

class Notebook(Dispositivo):
    procesador = models.CharField(max_length=100)
    ram_gb = models.PositiveIntegerField(verbose_name="RAM (GB)")
    almacenamiento = models.CharField(max_length=100, help_text="Ej: 512GB SSD")
    sistema_operativo = models.CharField(max_length=100)
    mac_address = models.CharField(max_length=17, null=True, blank=True)
    ip_asignada = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Notebook"

class Smartphone(Dispositivo):
    imei_1 = models.CharField(max_length=15, unique=True)
    imei_2 = models.CharField(max_length=15, null=True, blank=True)
    numero_telefono = models.CharField(max_length=20, null=True, blank=True)
    
    class Meta:
        verbose_name = "Smartphone"

class Impresora(Dispositivo):
    es_multifuncional = models.BooleanField(default=False)
    tipo_tinta = models.CharField(max_length=100, help_text="Ej: Toner TN-660")
    mac_address = models.CharField(max_length=17, null=True, blank=True)
    ip_asignada = models.GenericIPAddressField(null=True, blank=True)

class Servidor(Dispositivo):
    rack_u = models.CharField(max_length=50, verbose_name="Ubicación en Rack")
    configuracion_raid = models.CharField(max_length=100, null=True, blank=True)
    procesadores_fisicos = models.PositiveIntegerField(default=1)
    criticidad = models.CharField(max_length=50, choices=[('Baja', 'Baja'), ('Media', 'Media'), ('Alta', 'Alta')], default='Media')

class EquipoRed(Dispositivo):
    # Switch, Access Point, Firewall, etc.
    subtipo = models.CharField(max_length=50, help_text="Ej: Switch 24 puertos PoE")
    firmware_version = models.CharField(max_length=100, null=True, blank=True)
    mac_address = models.CharField(max_length=17, null=True, blank=True)
    ip_gestion = models.GenericIPAddressField(null=True, blank=True)

class Monitor(Dispositivo):
    pulgadas = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    resolucion = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Monitor"
        verbose_name_plural = "Monitores"

class BitacoraMantenimiento(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name="mantenimientos")
    fecha = models.DateTimeField(default=timezone.now)
    falla_reportada = models.TextField()
    reparacion_realizada = models.TextField(null=True, blank=True)
    costo_reparacion = models.PositiveIntegerField(default=0)
    tecnico_responsable = models.ForeignKey(Colaborador, on_delete=models.SET_NULL, null=True, blank=True)
    cambio_estado_automatico = models.BooleanField(default=False)

    def __str__(self):
        return f"Manto. {self.dispositivo.identificador_interno} - {self.fecha.date()}"

    class Meta:
        ordering = ['-fecha']
        verbose_name = "Bitácora de Mantenimiento"
        verbose_name_plural = "Bitácoras de Mantenimiento"

class HistorialAsignacion(models.Model):
    dispositivo      = models.ForeignKey('Dispositivo', on_delete=models.PROTECT, related_name='historial')
    colaborador      = models.ForeignKey('colaboradores.Colaborador', on_delete=models.PROTECT, related_name='asignaciones')
    fecha_inicio     = models.DateField(auto_now_add=True)
    fecha_fin        = models.DateField(null=True, blank=True)
    condicion_fisica = models.TextField()
    registrado_por   = models.ForeignKey(
        'colaboradores.Colaborador', on_delete=models.SET_NULL,
        null=True, related_name='asignaciones_registradas'
    )
    acta = models.ForeignKey(
        'actas.Acta', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='asignaciones'
    )
    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = 'Historial de Asignación'

    def __str__(self):
        return f"{self.dispositivo} → {self.colaborador} ({self.fecha_inicio})"

class EntregaAccesorio(models.Model):
    colaborador    = models.ForeignKey('colaboradores.Colaborador', on_delete=models.PROTECT, related_name='accesorios')
    tipo           = models.CharField(max_length=100)
    cantidad       = models.PositiveIntegerField(default=1)
    descripcion    = models.TextField(blank=True)
    fecha          = models.DateField(auto_now_add=True)
    registrado_por = models.ForeignKey(
        'colaboradores.Colaborador', on_delete=models.SET_NULL,
        null=True, related_name='entregas_registradas'
    )
    acta = models.ForeignKey(
        'actas.Acta', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='accesorios'
    )

    class Meta:
        ordering = ['-fecha']

    TIPOS_COMUNES = [
        'Mouse', 'Teclado', 'Mochila', 'Audífonos', 'Cable HDMI',
        'Cargador', 'Mouse Pad', 'Hub USB', 'Parlantes',
    ]

    def __str__(self):
        return f"{self.tipo} ({self.cantidad}) → {self.colaborador}"
