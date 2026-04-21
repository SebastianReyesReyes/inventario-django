import factory
from colaboradores.models import Colaborador
from core.models import Departamento, CentroCosto

class DepartamentoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Departamento
        
    nombre = factory.Sequence(lambda n: f"Departamento {n}")

class CentroCostoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CentroCosto
        
    codigo_contable = factory.Sequence(lambda n: f"CC-{n}")
    nombre = factory.Sequence(lambda n: f"Centro Costo {n}")
    activa = True

class ColaboradorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Colaborador
    
    username = factory.Sequence(lambda n: f"user{n}")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    esta_activo = True
    is_active = True
    
    # We leave rut, cargo, etc. as defaults or can be passed dynamically.
