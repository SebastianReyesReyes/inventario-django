import factory
from django.contrib.auth import get_user_model
from core.models import TipoDispositivo, EstadoDispositivo, Fabricante, Modelo, Departamento, CentroCosto
from colaboradores.models import Colaborador
from dispositivos.models import Dispositivo, HistorialAsignacion, EntregaAccesorio
from actas.models import Acta

class TipoDispositivoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TipoDispositivo
        django_get_or_create = ('nombre',)
    
    nombre = factory.Sequence(lambda n: f"Tipo {n}")
    sigla = factory.Sequence(lambda n: f"T{n:03d}")

class EstadoDispositivoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EstadoDispositivo
        django_get_or_create = ('nombre',)
    
    nombre = factory.Sequence(lambda n: f"Estado {n}")
    color = "#6B7280"


class EstadoDisponibleFactory(EstadoDispositivoFactory):
    nombre = "Disponible"
    color = "#10B981"


class EstadoAsignadoFactory(EstadoDispositivoFactory):
    nombre = "Asignado"
    color = "#3B82F6"


class EstadoReparacionFactory(EstadoDispositivoFactory):
    nombre = "En Reparación"
    color = "#F59E0B"


class EstadoFueraInventarioFactory(EstadoDispositivoFactory):
    nombre = "Fuera de Inventario"
    color = "#EF4444"

class FabricanteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Fabricante
        django_get_or_create = ('nombre',)
    
    nombre = factory.Sequence(lambda n: f"Fabricante {n}")

class ModeloFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Modelo
        django_get_or_create = ('nombre', 'fabricante', 'tipo_dispositivo')
    
    nombre = factory.Sequence(lambda n: f"Modelo {n}")
    fabricante = factory.SubFactory(FabricanteFactory)
    tipo_dispositivo = factory.SubFactory(TipoDispositivoFactory)

class DepartamentoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Departamento
        django_get_or_create = ('nombre',)
    
    nombre = factory.Sequence(lambda n: f"Departamento {n}")

class CentroCostoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CentroCosto
        django_get_or_create = ('codigo_contable',)
    
    nombre = factory.Sequence(lambda n: f"Centro Costo {n}")
    codigo_contable = factory.Sequence(lambda n: f"CC-{n:04d}")

class ColaboradorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Colaborador
    
    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    rut = factory.Sequence(lambda n: f"{10000000+n}-{n%10}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    departamento = factory.SubFactory(DepartamentoFactory)
    centro_costo = factory.SubFactory(CentroCostoFactory)
    is_active = True
    esta_activo = True

class DispositivoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Dispositivo
    
    numero_serie = factory.Sequence(lambda n: f"SN-{n:08d}")
    estado = factory.SubFactory(EstadoDispositivoFactory)
    modelo = factory.SubFactory(ModeloFactory)
    centro_costo = factory.SubFactory(CentroCostoFactory)
    valor_contable = 500000
    notas_condicion = "Nuevo en caja"

class HistorialAsignacionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HistorialAsignacion
    
    dispositivo = factory.SubFactory(DispositivoFactory)
    colaborador = factory.SubFactory(ColaboradorFactory)
    condicion_fisica = "Buen estado"
    registrado_por = factory.SubFactory(ColaboradorFactory)

class EntregaAccesorioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EntregaAccesorio
    
    colaborador = factory.SubFactory(ColaboradorFactory)
    tipo = "Mouse"
    cantidad = 1
    descripcion = "Mouse óptico"
    registrado_por = factory.SubFactory(ColaboradorFactory)

class ActaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Acta
    
    colaborador = factory.SubFactory(ColaboradorFactory)
    creado_por = factory.SubFactory(ColaboradorFactory)
    tipo_acta = 'ENTREGA'
    observaciones = "Generada por factory"
