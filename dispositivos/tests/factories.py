"""Factories para la app dispositivos.

Importa las factories canónicas desde core.tests.factories para evitar duplicación.
Solo define factories específicas de dispositivos que no existen en core.
"""
import factory
from django.utils import timezone

from dispositivos.models import (
    Dispositivo, Notebook, Smartphone, Monitor, Impresora,
    Servidor, EquipoRed, BitacoraMantenimiento,
)
from core.tests.factories import (
    TipoDispositivoFactory,
    EstadoDispositivoFactory,
    FabricanteFactory,
    ModeloFactory,
    CentroCostoFactory,
    ColaboradorFactory,
    DispositivoFactory,
)


class NotebookFactory(factory.django.DjangoModelFactory):
    """Crea un Notebook con todos los campos requeridos del modelo especializado."""

    class Meta:
        model = Notebook

    numero_serie = factory.Sequence(lambda n: f"NB-SN-{n:06d}")
    estado = factory.SubFactory(EstadoDispositivoFactory, nombre="Disponible")
    modelo = factory.SubFactory(ModeloFactory)
    centro_costo = factory.SubFactory(CentroCostoFactory)
    valor_contable = 800000
    fecha_compra = factory.LazyFunction(lambda: timezone.now().date())
    notas_condicion = "Nuevo en caja"

    procesador = "Intel Core i7"
    ram_gb = 16
    almacenamiento = "512GB SSD"
    sistema_operativo = "Windows 11 Pro"


class SmartphoneFactory(factory.django.DjangoModelFactory):
    """Crea un Smartphone con IMEI único."""

    class Meta:
        model = Smartphone

    numero_serie = factory.Sequence(lambda n: f"SP-SN-{n:06d}")
    estado = factory.SubFactory(EstadoDispositivoFactory, nombre="Disponible")
    modelo = factory.SubFactory(ModeloFactory)
    centro_costo = factory.SubFactory(CentroCostoFactory)
    valor_contable = 400000
    fecha_compra = factory.LazyFunction(lambda: timezone.now().date())
    notas_condicion = "Nuevo"

    imei_1 = factory.Sequence(lambda n: f"35{100000000000 + n}")


class MonitorFactory(factory.django.DjangoModelFactory):
    """Crea un Monitor."""

    class Meta:
        model = Monitor

    numero_serie = factory.Sequence(lambda n: f"MON-SN-{n:06d}")
    estado = factory.SubFactory(EstadoDispositivoFactory, nombre="Disponible")
    modelo = factory.SubFactory(ModeloFactory)
    centro_costo = factory.SubFactory(CentroCostoFactory)
    valor_contable = 200000
    fecha_compra = factory.LazyFunction(lambda: timezone.now().date())
    notas_condicion = "Nuevo"

    pulgadas = 24.0
    resolucion = "1920x1080"


class BitacoraMantenimientoFactory(factory.django.DjangoModelFactory):
    """Crea un registro de mantenimiento."""

    class Meta:
        model = BitacoraMantenimiento

    dispositivo = factory.SubFactory(DispositivoFactory)
    falla_reportada = "No enciende"
    reparacion_realizada = "Se reemplazó fuente de poder"
    costo_reparacion = 50000
    tecnico_responsable = factory.SubFactory(ColaboradorFactory)
