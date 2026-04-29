import pytest
from suministros.models import CategoriaSuministro, Suministro, MovimientoStock


@pytest.mark.django_db
class TestSuministroModel:
    @pytest.fixture
    def categoria(self):
        return CategoriaSuministro.objects.create(nombre="Papel", descripcion="Papel bond")

    @pytest.fixture
    def suministro(self, categoria):
        return Suministro.objects.create(nombre="Papel A4", categoria=categoria, stock_minimo=5)

    def test_esta_activo_default_true(self, suministro):
        assert suministro.esta_activo is True

    def test_queryset_activos_excludes_inactivos(self, categoria):
        s1 = Suministro.objects.create(nombre="Activo", categoria=categoria)
        s2 = Suministro.objects.create(nombre="Inactivo", categoria=categoria, esta_activo=False)
        activos = Suministro.objects.activos()
        assert s1 in activos
        assert s2 not in activos

    def test_bajo_stock_filter(self, categoria):
        normal = Suministro.objects.create(nombre="Normal", categoria=categoria, stock_actual=10, stock_minimo=5)
        critico = Suministro.objects.create(nombre="Critico", categoria=categoria, stock_actual=3, stock_minimo=5)
        bajo = Suministro.objects.bajo_stock()
        assert normal not in bajo
        assert critico in bajo

    def test_stock_critico_property(self, categoria):
        s = Suministro.objects.create(nombre="Test", categoria=categoria, stock_actual=2, stock_minimo=5)
        assert s.stock_critico is True
        s.stock_actual = 10
        assert s.stock_critico is False
