from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum, F
from core.models import Modelo, CentroCosto, Fabricante
from colaboradores.models import Colaborador

class CategoriaSuministro(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, help_text="Descripción de la categoría de suministros")
    tipos_dispositivo_compatibles = models.ManyToManyField('core.TipoDispositivo', blank=True, help_text="Tipos de dispositivos que usan esta categoría de suministros")

    class Meta:
        verbose_name = "Categoría de Suministro"
        verbose_name_plural = "Categorías de Suministros"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class SuministroQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(esta_activo=True)

    def bajo_stock(self):
        return self.filter(stock_actual__lte=F('stock_minimo'))


class Suministro(models.Model):
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaSuministro, on_delete=models.PROTECT, related_name='suministros')
    codigo_interno = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="SKU o código de barras")
    
    fabricante = models.ForeignKey(Fabricante, on_delete=models.SET_NULL, null=True, blank=True, related_name='suministros', help_text="Fabricante del insumo (Ej: Brother, HP, Dataline)")
    es_alternativo = models.BooleanField(default=False, help_text="Marcar si es un insumo alternativo/genérico")
    
    unidad_medida = models.CharField(max_length=50, default="Unidades", help_text="Ej: Unidades, Cajas, Litros")
    stock_minimo = models.PositiveIntegerField(default=2, help_text="Nivel de alerta para reposición")
    
    modelos_compatibles = models.ManyToManyField(Modelo, blank=True, related_name='suministros_compatibles', help_text="Modelos de impresoras o dispositivos compatibles")
    
    # Campo de solo lectura, actualizado vía señales o services
    stock_actual = models.IntegerField(default=0, editable=False, help_text="Stock calculado en base a movimientos")
    esta_activo = models.BooleanField(default=True, help_text="Indica si el suministro está activo en el catálogo")
    duracion_estimada_dias = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Días estimados que debería durar este insumo. Usado para alertas de consumo inusual."
    )

    class Meta:
        verbose_name = "Suministro"
        verbose_name_plural = "Suministros"
        ordering = ['categoria__nombre', 'nombre']

    def __str__(self):
        fabricante_str = ""
        if self.fabricante and self.fabricante.nombre.lower() not in self.nombre.lower():
            fabricante_str = f" ({self.fabricante.nombre})"
            
        tipo_str = " [Alternativo]" if self.es_alternativo else ""
        return f"{self.nombre}{fabricante_str}{tipo_str}"
        
    def recalcular_stock(self):
        """
        Recalcula el stock_actual sumando las ENTRADAS/AJUSTES_POSITIVOS
        y restando las SALIDAS/AJUSTES_NEGATIVOS.
        """
        entradas = self.movimientos.filter(
            tipo_movimiento__in=[MovimientoStock.TipoMovimiento.ENTRADA, MovimientoStock.TipoMovimiento.AJUSTE_POSITIVO]
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        salidas = self.movimientos.filter(
            tipo_movimiento__in=[MovimientoStock.TipoMovimiento.SALIDA, MovimientoStock.TipoMovimiento.AJUSTE_NEGATIVO]
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        nuevo_stock = entradas - salidas
        if self.stock_actual != nuevo_stock:
            self.stock_actual = nuevo_stock
            self.save(update_fields=['stock_actual'])
            
    @property
    def stock_critico(self):
        return self.stock_actual <= self.stock_minimo

    objects = SuministroQuerySet.as_manager()


class MovimientoStock(models.Model):
    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada (Compra)'
        SALIDA = 'SALIDA', 'Salida (Entrega/Asignación)'
        AJUSTE_POSITIVO = 'AJUSTE_POS', 'Ajuste Positivo'
        AJUSTE_NEGATIVO = 'AJUSTE_NEG', 'Ajuste Negativo (Merma/Pérdida)'

    suministro = models.ForeignKey(Suministro, on_delete=models.PROTECT, related_name='movimientos')
    fecha = models.DateTimeField(default=timezone.now)
    tipo_movimiento = models.CharField(max_length=20, choices=TipoMovimiento.choices)
    cantidad = models.PositiveIntegerField(help_text="Cantidad del movimiento (siempre positiva)")
    
    # Datos de la Factura (Solo para ENTRADAS)
    costo_unitario = models.PositiveIntegerField(null=True, blank=True, help_text="Costo unitario en la factura (solo entradas)")
    numero_factura = models.CharField(max_length=100, null=True, blank=True)
    
    # Datos de Salida (Solo para SALIDAS)
    colaborador_destino = models.ForeignKey(Colaborador, on_delete=models.SET_NULL, null=True, blank=True, related_name='suministros_recibidos')
    centro_costo = models.ForeignKey(CentroCosto, on_delete=models.SET_NULL, null=True, blank=True, related_name='suministros_cargados')
    dispositivo_destino = models.ForeignKey('dispositivos.Dispositivo', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_stock', help_text="Dispositivo al que se destinó el insumo (ej: impresora)")
    
    registrado_por = models.ForeignKey(Colaborador, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_stock_registrados')
    notas = models.TextField(blank=True, help_text="Razón de la merma, detalle de la entrega, etc.")

    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.tipo_movimiento} de {self.cantidad} {self.suministro.unidad_medida} - {self.suministro.nombre}"

    def clean(self):
        tipos_salida = [self.TipoMovimiento.SALIDA, self.TipoMovimiento.AJUSTE_NEGATIVO]
        if self.tipo_movimiento in tipos_salida and self.cantidad > self.suministro.stock_actual:
            # Validamos que no se saque más de lo que hay, si es un nuevo movimiento
            if self.pk is None: 
                raise ValidationError({"cantidad": f"No hay suficiente stock. Stock actual: {self.suministro.stock_actual}."})
