import pytest
from django.db.models.deletion import ProtectedError
from .factories import (
    FabricanteFactory, ModeloFactory, TipoDispositivoFactory, 
    EstadoDispositivoFactory, CentroCostoFactory
)

@pytest.mark.django_db
class TestCatalogModels:
    def test_modelo_fabricante_protect(self):
        """Validar que no se puede eliminar un fabricante si tiene modelos asociados (PROTECT)"""
        fabricante = FabricanteFactory()
        ModeloFactory(nombre="Latitude 5420", fabricante=fabricante)
        
        with pytest.raises(ProtectedError):
            fabricante.delete()

    def test_centro_costo_default_active(self):
        """Validar que el centro de costo se crea activo por defecto"""
        cc = CentroCostoFactory()
        assert cc.activa is True
        cc.activa = False
        cc.save()
        assert cc.activa is False

    def test_estado_dispositivo_color(self):
        """Validar almacenamiento de color en estado"""
        estado = EstadoDispositivoFactory(color="#FF0000")
        assert estado.color == "#FF0000"

    def test_tipo_dispositivo_str(self):
        """Validar representación string del tipo"""
        tipo = TipoDispositivoFactory(nombre="Notebook")
        assert str(tipo) == "Notebook"

    def test_fabricante_str(self):
        """Validar representación string del fabricante"""
        fabricante = FabricanteFactory(nombre="Dell")
        assert str(fabricante) == "Dell"

    def test_modelo_str(self):
        """Validar representación string del modelo"""
        fabricante = FabricanteFactory(nombre="Dell")
        modelo = ModeloFactory(nombre="Latitude", fabricante=fabricante)
        assert str(modelo) == "Dell Latitude"

    def test_centro_costo_str(self):
        """Validar representación string del centro de costo"""
        cc = CentroCostoFactory(codigo_contable="CC001", nombre="Ventas")
        assert str(cc) == "CC001 - Ventas"
