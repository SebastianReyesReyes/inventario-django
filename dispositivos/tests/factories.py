import factory
from django.utils import timezone
from dispositivos.models import Dispositivo, TipoDispositivo, EstadoDispositivo, Modelo
from core.models import Fabricante
from colaboradores.tests.factories import CentroCostoFactory, ColaboradorFactory

class FabricanteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Fabricante
    nombre = factory.Sequence(lambda n: f"Fabricante {n}")

class ModeloFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Modelo
    nombre = factory.Sequence(lambda n: f"Modelo {n}")
    fabricante = factory.SubFactory(FabricanteFactory)

class TipoDispositivoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TipoDispositivo
    nombre = factory.Sequence(lambda n: f"Tipo {n}")
    sigla = factory.Sequence(lambda n: f"T{n}")

class EstadoDispositivoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EstadoDispositivo
    nombre = factory.Sequence(lambda n: f"Estado {n}")
    color = "#000000"

class DispositivoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Dispositivo
    
    numero_serie = factory.Sequence(lambda n: f"SN-{n}")
    tipo = factory.SubFactory(TipoDispositivoFactory)
    estado = factory.SubFactory(EstadoDispositivoFactory)
    modelo = factory.SubFactory(ModeloFactory)
    centro_costo = factory.SubFactory(CentroCostoFactory)
    valor_contable = 500000
    fecha_compra = timezone.now().date()
