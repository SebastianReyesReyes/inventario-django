from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# =============================================================================
# SOFT DELETE MIXIN
# =============================================================================

class SoftDeleteManager(models.Manager):
    """Manager que filtra automáticamente los registros eliminados."""
    def get_queryset(self):
        return super().get_queryset().filter(eliminado=False)


class SoftDeleteAllManager(models.Manager):
    """Manager que incluye TODOS los registros (incluyendo eliminados)."""
    pass


class SoftDeleteMixin(models.Model):
    """Mixin para soft delete. Agrega campos eliminado + fecha_eliminacion."""
    eliminado = models.BooleanField(default=False, db_index=True)
    fecha_eliminacion = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = SoftDeleteAllManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Override: marca como eliminado en vez de borrar de la DB."""
        self.eliminado = True
        self.fecha_eliminacion = timezone.now()
        self.save(update_fields=['eliminado', 'fecha_eliminacion'])

    def hard_delete(self, using=None, keep_parents=False):
        """Borrado real de la DB. Usar con precaución."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restaurar un registro eliminado."""
        self.eliminado = False
        self.fecha_eliminacion = None
        self.save(update_fields=['eliminado', 'fecha_eliminacion'])


# =============================================================================
# ENUMS (TextChoices — conjuntos fijos que rara vez cambian)
# =============================================================================

class Criticidad(models.TextChoices):
    BAJA = 'Baja', 'Baja'
    MEDIA = 'Media', 'Media'
    ALTA = 'Alta', 'Alta'
    CRITICA = 'Critica', 'Crítica'


class TipoActa(models.TextChoices):
    ENTREGA = 'Entrega', 'Entrega'
    DEVOLUCION = 'Devolucion', 'Devolución'
    RECAMBIO = 'Recambio', 'Recambio'


# =============================================================================
# CATÁLOGOS (tablas de DB — editables desde admin sin migración)
# =============================================================================

class TipoDispositivo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Tipo de dispositivo'
        verbose_name_plural = 'Tipos de dispositivo'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Estado(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Estado'
        verbose_name_plural = 'Estados'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Fabricante(models.Model):
    nombre = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name = 'Fabricante'
        verbose_name_plural = 'Fabricantes'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Modelo(models.Model):
    nombre = models.CharField(max_length=150)
    fabricante = models.ForeignKey(
        Fabricante, on_delete=models.PROTECT, related_name='modelos'
    )

    class Meta:
        verbose_name = 'Modelo'
        verbose_name_plural = 'Modelos'
        ordering = ['fabricante__nombre', 'nombre']
        unique_together = ['nombre', 'fabricante']

    def __str__(self):
        return self.nombre


class Departamento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Ubicacion(models.Model):
    nombre = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name = 'Ubicación'
        verbose_name_plural = 'Ubicaciones'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# =============================================================================
# PERSONAS
# =============================================================================

class Colaborador(SoftDeleteMixin):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='colaborador',
        null=True, blank=True,
        help_text='Cuenta de usuario Django (opcional hasta que se active login)'
    )
    rut = models.CharField(
        max_length=12, unique=True, db_index=True,
        help_text='Formato: 12.345.678-9'
    )
    nombre_completo = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True, unique=True)
    cargo = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    departamento = models.ForeignKey(
        Departamento, on_delete=models.PROTECT, related_name='colaboradores'
    )
    ubicacion = models.ForeignKey(
        Ubicacion, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='colaboradores',
        help_text='Ubicación principal del colaborador'
    )
    esta_activo = models.BooleanField(
        default=True, db_index=True,
        help_text='False = ex-empleado (baja lógica sin borrar historial)'
    )
    azure_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True,
        help_text='Object ID de Azure EntraID para sync futuro'
    )

    class Meta:
        verbose_name = 'Colaborador'
        verbose_name_plural = 'Colaboradores'
        ordering = ['nombre_completo']

    def __str__(self):
        return f'{self.nombre_completo} ({self.rut})'


# =============================================================================
# DISPOSITIVO (tabla principal)
# =============================================================================

class Dispositivo(SoftDeleteMixin):
    serial_number = models.CharField(
        'Número de serie', max_length=100, unique=True, db_index=True
    )
    tipo = models.ForeignKey(
        TipoDispositivo, on_delete=models.PROTECT,
        related_name='dispositivos', verbose_name='Tipo'
    )
    fabricante = models.ForeignKey(
        Fabricante, on_delete=models.PROTECT,
        related_name='dispositivos', verbose_name='Fabricante'
    )
    modelo = models.ForeignKey(
        Modelo, on_delete=models.PROTECT,
        related_name='dispositivos', verbose_name='Modelo'
    )
    estado = models.ForeignKey(
        Estado, on_delete=models.PROTECT,
        related_name='dispositivos', verbose_name='Estado'
    )
    ubicacion = models.ForeignKey(
        Ubicacion, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='dispositivos', verbose_name='Ubicación'
    )
    propietario_actual = models.ForeignKey(
        Colaborador, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dispositivos_asignados',
        verbose_name='Propietario actual'
    )

    # Datos financieros y soporte
    fecha_compra = models.DateField('Fecha de compra', null=True, blank=True)
    precio_compra = models.DecimalField(
        'Precio de compra', max_digits=12, decimal_places=2,
        null=True, blank=True, help_text='CLP'
    )
    n_pedido = models.CharField(
        'N° de pedido', max_length=100, blank=True,
        help_text='Número de orden de compra'
    )
    rust_desk_id = models.CharField(
        'RustDesk ID', max_length=50, blank=True,
        help_text='ID para soporte remoto'
    )
    criticidad = models.CharField(
        max_length=20, choices=Criticidad.choices,
        blank=True, help_text='Nivel de criticidad del equipo'
    )
    notas_condicion = models.TextField(
        'Notas de condición', blank=True,
        help_text='Estado físico, daños cosméticos, observaciones'
    )
    foto_equipo = models.ImageField(
        'Foto del equipo', upload_to='dispositivos/', blank=True, null=True
    )

    class Meta:
        verbose_name = 'Dispositivo'
        verbose_name_plural = 'Dispositivos'
        ordering = ['-id']

    def __str__(self):
        return f'{self.tipo} - {self.fabricante} {self.modelo} (SN: {self.serial_number})'


# =============================================================================
# DETALLES 1:1 (tablas hijas — PK = FK al dispositivo)
# =============================================================================

class Notebook(models.Model):
    dispositivo = models.OneToOneField(
        Dispositivo, on_delete=models.CASCADE,
        primary_key=True, related_name='notebook'
    )
    ram_gb = models.PositiveIntegerField('RAM (GB)', null=True, blank=True)
    procesador = models.CharField('Procesador', max_length=100, blank=True)
    sistema_operativo = models.CharField('Sistema operativo', max_length=100, blank=True)
    mac_address = models.CharField('Dirección MAC', max_length=20, blank=True)

    class Meta:
        verbose_name = 'Detalle Notebook'
        verbose_name_plural = 'Detalles Notebook'

    def __str__(self):
        return f'Notebook: {self.dispositivo.serial_number}'


class Smartphone(models.Model):
    dispositivo = models.OneToOneField(
        Dispositivo, on_delete=models.CASCADE,
        primary_key=True, related_name='smartphone'
    )
    imei_1 = models.CharField('IMEI 1', max_length=20, blank=True)
    imei_2 = models.CharField('IMEI 2', max_length=20, blank=True)
    numero_telefono = models.CharField('Número de teléfono', max_length=20, blank=True)

    class Meta:
        verbose_name = 'Detalle Smartphone'
        verbose_name_plural = 'Detalles Smartphone'

    def __str__(self):
        return f'Smartphone: {self.dispositivo.serial_number}'


class Impresora(models.Model):
    dispositivo = models.OneToOneField(
        Dispositivo, on_delete=models.CASCADE,
        primary_key=True, related_name='impresora'
    )
    direccion_ip = models.CharField('Dirección IP', max_length=20, blank=True)
    es_multifuncional = models.BooleanField(
        'Es multifuncional', default=False,
        help_text='Marcar si tiene scanner integrado'
    )
    tipo_tinta = models.CharField(
        'Tipo de tinta', max_length=50, blank=True,
        help_text='Ej: Láser, Inyección'
    )

    class Meta:
        verbose_name = 'Detalle Impresora'
        verbose_name_plural = 'Detalles Impresora'

    def __str__(self):
        return f'Impresora: {self.dispositivo.serial_number}'


class RouterMovil(models.Model):
    dispositivo = models.OneToOneField(
        Dispositivo, on_delete=models.CASCADE,
        primary_key=True, related_name='router_movil'
    )
    imei = models.CharField('IMEI', max_length=20, blank=True)
    compania = models.CharField(
        'Compañía', max_length=50, blank=True,
        help_text='Ej: Entel, Claro, Movistar'
    )
    es_5g = models.BooleanField('Es 5G', default=False)

    class Meta:
        verbose_name = 'Detalle Router Móvil'
        verbose_name_plural = 'Detalles Router Móvil'

    def __str__(self):
        return f'Router Móvil: {self.dispositivo.serial_number}'


class EquipoRed(models.Model):
    dispositivo = models.OneToOneField(
        Dispositivo, on_delete=models.CASCADE,
        primary_key=True, related_name='equipo_red'
    )
    ip_gestion = models.CharField(
        'IP de gestión', max_length=20, blank=True
    )
    firmware_version = models.CharField(
        'Versión de firmware', max_length=100, blank=True
    )
    puertos_totales = models.PositiveIntegerField(
        'Puertos totales', null=True, blank=True
    )
    capa_red = models.PositiveIntegerField(
        'Capa de red', null=True, blank=True,
        help_text='Capa 2 o Capa 3'
    )

    class Meta:
        verbose_name = 'Detalle Equipo de Red'
        verbose_name_plural = 'Detalles Equipo de Red'

    def __str__(self):
        return f'Equipo Red: {self.dispositivo.serial_number}'


class Servidor(models.Model):
    dispositivo = models.OneToOneField(
        Dispositivo, on_delete=models.CASCADE,
        primary_key=True, related_name='servidor'
    )
    ram_gb = models.PositiveIntegerField('RAM (GB)', null=True, blank=True)
    procesador = models.CharField('Procesador', max_length=100, blank=True)
    almacenamiento_total = models.CharField(
        'Almacenamiento total', max_length=100, blank=True,
        help_text='Ej: 2TB RAID 5'
    )
    raid_config = models.CharField(
        'Configuración RAID', max_length=50, blank=True,
        help_text='Ej: RAID 0, 1, 5, 10'
    )
    id_rack = models.CharField('ID del rack', max_length=50, blank=True)
    posicion_u = models.PositiveIntegerField(
        'Posición U', null=True, blank=True,
        help_text='Posición en unidades de rack'
    )

    class Meta:
        verbose_name = 'Detalle Servidor'
        verbose_name_plural = 'Detalles Servidor'

    def __str__(self):
        return f'Servidor: {self.dispositivo.serial_number}'


class TelefonoIP(models.Model):
    dispositivo = models.OneToOneField(
        Dispositivo, on_delete=models.CASCADE,
        primary_key=True, related_name='telefono_ip'
    )
    anexo = models.CharField('Anexo', max_length=10, blank=True)
    mac_address = models.CharField('Dirección MAC', max_length=20, blank=True)
    modelo_expansion = models.BooleanField(
        'Módulo de expansión', default=False,
        help_text='Tiene módulo de expansión de teclas'
    )

    class Meta:
        verbose_name = 'Detalle Teléfono IP'
        verbose_name_plural = 'Detalles Teléfono IP'

    def __str__(self):
        return f'Teléfono IP: {self.dispositivo.serial_number}'


class Periferico(models.Model):
    dispositivo = models.OneToOneField(
        Dispositivo, on_delete=models.CASCADE,
        primary_key=True, related_name='periferico'
    )
    tipo_periferico = models.CharField(
        'Tipo de periférico', max_length=100, blank=True,
        help_text='Ej: Monitor, Docking Station, UPS'
    )
    conector = models.CharField(
        'Conector', max_length=50, blank=True,
        help_text='Ej: USB-C, HDMI, Inalámbrico'
    )

    class Meta:
        verbose_name = 'Detalle Periférico'
        verbose_name_plural = 'Detalles Periférico'

    def __str__(self):
        return f'Periférico: {self.dispositivo.serial_number}'


# =============================================================================
# INVENTARIO & STOCK
# =============================================================================

class Accesorio(models.Model):
    nombre = models.CharField(max_length=150)
    categoria = models.CharField(
        max_length=100, blank=True,
        help_text='Ej: Periférico, Energía, Adaptador'
    )
    stock_disponible = models.PositiveIntegerField(
        'Stock disponible', default=0
    )

    class Meta:
        verbose_name = 'Accesorio'
        verbose_name_plural = 'Accesorios'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} (stock: {self.stock_disponible})'


class Consumible(models.Model):
    nombre = models.CharField(max_length=150)
    stock_actual = models.PositiveIntegerField('Stock actual', default=0)
    alerta_minima = models.PositiveIntegerField(
        'Alerta mínima', default=0,
        help_text='Umbral para notificación de stock bajo'
    )

    class Meta:
        verbose_name = 'Consumible'
        verbose_name_plural = 'Consumibles'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} (stock: {self.stock_actual})'

    @property
    def stock_bajo(self):
        return self.stock_actual <= self.alerta_minima


class ConsumibleCompatibilidad(models.Model):
    consumible = models.ForeignKey(
        Consumible, on_delete=models.CASCADE, related_name='compatibilidades'
    )
    modelo = models.ForeignKey(
        Modelo, on_delete=models.CASCADE, related_name='consumibles_compatibles'
    )

    class Meta:
        verbose_name = 'Compatibilidad de consumible'
        verbose_name_plural = 'Compatibilidades de consumible'
        unique_together = ['consumible', 'modelo']

    def __str__(self):
        return f'{self.consumible.nombre} → {self.modelo}'


# =============================================================================
# MOVIMIENTOS & DOCUMENTOS
# =============================================================================

class Acta(SoftDeleteMixin):
    tipo = models.CharField(
        'Tipo de acta', max_length=20, choices=TipoActa.choices
    )
    colaborador = models.ForeignKey(
        Colaborador, on_delete=models.PROTECT,
        related_name='actas_recibidas',
        verbose_name='Colaborador (destinatario)',
        help_text='El que recibe o devuelve los equipos'
    )
    creado_por = models.ForeignKey(
        Colaborador, on_delete=models.PROTECT,
        related_name='actas_creadas',
        verbose_name='Creado por',
        help_text='El técnico que genera el acta'
    )
    fecha = models.DateTimeField('Fecha', auto_now_add=True)
    observaciones = models.TextField('Observaciones', blank=True)
    pdf_generado = models.FileField(
        'PDF generado', upload_to='actas/pdf/',
        blank=True, null=True
    )
    acta_firmada = models.FileField(
        'Acta firmada', upload_to='actas/firmadas/',
        blank=True, null=True,
        help_text='PDF escaneado o foto del acta firmada'
    )
    foto_evidencia = models.ImageField(
        'Foto de evidencia', upload_to='actas/evidencia/',
        blank=True, null=True
    )

    class Meta:
        verbose_name = 'Acta'
        verbose_name_plural = 'Actas'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.colaborador.nombre_completo} ({self.fecha:%d/%m/%Y})'


class HistorialAsignacion(SoftDeleteMixin):
    dispositivo = models.ForeignKey(
        Dispositivo, on_delete=models.CASCADE,
        related_name='historial_asignaciones',
        verbose_name='Dispositivo'
    )
    colaborador = models.ForeignKey(
        Colaborador, on_delete=models.PROTECT,
        related_name='historial_asignaciones',
        verbose_name='Colaborador'
    )
    acta = models.ForeignKey(
        Acta, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='asignaciones',
        verbose_name='Acta',
        help_text='Acta que documenta esta asignación'
    )
    fecha_entrega = models.DateTimeField('Fecha de entrega')
    fecha_devolucion = models.DateTimeField(
        'Fecha de devolución', null=True, blank=True,
        help_text='Vacío = aún asignado'
    )

    class Meta:
        verbose_name = 'Historial de asignación'
        verbose_name_plural = 'Historial de asignaciones'
        ordering = ['-fecha_entrega']

    def __str__(self):
        estado = 'activo' if not self.fecha_devolucion else 'devuelto'
        return f'{self.dispositivo} → {self.colaborador.nombre_completo} ({estado})'


class EntregaAccesorios(SoftDeleteMixin):
    colaborador = models.ForeignKey(
        Colaborador, on_delete=models.PROTECT,
        related_name='entregas_accesorios',
        verbose_name='Colaborador'
    )
    accesorio = models.ForeignKey(
        Accesorio, on_delete=models.PROTECT,
        related_name='entregas',
        verbose_name='Accesorio'
    )
    acta = models.ForeignKey(
        Acta, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='entregas_accesorios',
        verbose_name='Acta'
    )
    cantidad = models.PositiveIntegerField('Cantidad', default=1)
    fecha_entrega = models.DateField('Fecha de entrega')

    class Meta:
        verbose_name = 'Entrega de accesorio'
        verbose_name_plural = 'Entregas de accesorios'
        ordering = ['-fecha_entrega']

    def __str__(self):
        return f'{self.accesorio.nombre} x{self.cantidad} → {self.colaborador.nombre_completo}'


class HistoriaMantenimiento(SoftDeleteMixin):
    dispositivo = models.ForeignKey(
        Dispositivo, on_delete=models.CASCADE,
        related_name='historial_mantenimiento',
        verbose_name='Dispositivo'
    )
    fecha_falla = models.DateField('Fecha de falla')
    descripcion = models.TextField('Descripción')
    costo_estimado_reparacion = models.DecimalField(
        'Costo estimado de reparación',
        max_digits=12, decimal_places=2,
        null=True, blank=True, help_text='CLP'
    )
    estado_resolucion = models.CharField(
        'Estado de resolución', max_length=100, blank=True,
        help_text='Ej: Reparado, Irreparable, En espera'
    )

    class Meta:
        verbose_name = 'Historia de mantenimiento'
        verbose_name_plural = 'Historias de mantenimiento'
        ordering = ['-fecha_falla']

    def __str__(self):
        return f'{self.dispositivo} - {self.fecha_falla} ({self.estado_resolucion or "Pendiente"})'
