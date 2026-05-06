from django.db import models

class TipoDispositivo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    sigla = models.CharField(max_length=10, unique=True, null=True, blank=True, help_text="Ej: NTBK, SMPH")
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    umbral_disponibilidad = models.PositiveIntegerField(
        default=3,
        help_text="Stock mínimo de equipos disponibles para semáforo verde en el Dashboard"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Tipo de Dispositivo"
        verbose_name_plural = "Tipos de Dispositivo"

class EstadoDispositivo(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#6B7280', help_text="Hex color para el badge")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Estado de Dispositivo"
        verbose_name_plural = "Estados de Dispositivo"

class Fabricante(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Modelo(models.Model):
    nombre = models.CharField(max_length=100)
    fabricante = models.ForeignKey(Fabricante, on_delete=models.PROTECT, related_name="modelos")
    tipo_dispositivo = models.ForeignKey(TipoDispositivo, on_delete=models.PROTECT, related_name="modelos")

    def __str__(self):
        return self.nombre

    class Meta:
        unique_together = ('nombre', 'fabricante')

class Departamento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class CentroCosto(models.Model):
    nombre = models.CharField(max_length=100)
    codigo_contable = models.CharField(max_length=50, unique=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.codigo_contable} - {self.nombre}"

    class Meta:
        verbose_name = "Centro de Costo"
        verbose_name_plural = "Centros de Costo"
