import factory
from suministros.models import CategoriaSuministro, Suministro, MovimientoStock
from core.tests.factories import ColaboradorFactory, ModeloFactory, FabricanteFactory


class CategoriaSuministroFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CategoriaSuministro
        django_get_or_create = ('nombre',)

    nombre = factory.Sequence(lambda n: f"Categoría {n}")
    descripcion = factory.Sequence(lambda n: f"Descripción {n}")


class SuministroFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Suministro

    nombre = factory.Sequence(lambda n: f"Suministro {n}")
    categoria = factory.SubFactory(CategoriaSuministroFactory)
    codigo_interno = factory.Sequence(lambda n: f"SKU-{n:04d}")
    fabricante = factory.SubFactory(FabricanteFactory)
    es_alternativo = False
    unidad_medida = "Unidades"
    stock_minimo = 2
    stock_actual = 0
    esta_activo = True

    @factory.post_generation
    def modelos_compatibles(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for modelo in extracted:
                self.modelos_compatibles.add(modelo)


class MovimientoStockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MovimientoStock

    suministro = factory.SubFactory(SuministroFactory)
    tipo_movimiento = MovimientoStock.TipoMovimiento.ENTRADA
    cantidad = 10
    costo_unitario = 5000
    numero_factura = "FACT-001"
    registrado_por = factory.SubFactory(ColaboradorFactory)
    notas = "Movimiento de prueba"
