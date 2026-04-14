from django.test import TestCase
from django.db.models.deletion import ProtectedError
from .models import Fabricante, Modelo, TipoDispositivo, CentroCosto, EstadoDispositivo

class CatalogModelsTest(TestCase):
    def setUp(self):
        self.fabricante = Fabricante.objects.create(nombre="Test Manufacturer")
        self.tipo = TipoDispositivo.objects.create(nombre="Test Type", sigla="TST")
        self.estado = EstadoDispositivo.objects.create(nombre="Test Status", color="#FF0000")
        self.cc = CentroCosto.objects.create(nombre="Test CC", codigo_contable="TST-001")

    def test_modelo_fabricante_protect(self):
        """Validar que no se puede eliminar un fabricante si tiene modelos asociados (PROTECT)"""
        Modelo.objects.create(nombre="Latitude 5420", fabricante=self.fabricante)
        
        with self.assertRaises(ProtectedError):
            self.fabricante.delete()

    def test_centro_costo_toggle(self):
        """Validar que el centro de costo se crea activo por defecto"""
        self.assertTrue(self.cc.activa)
        self.cc.activa = False
        self.cc.save()
        self.assertFalse(self.cc.activa)

    def test_estado_dispositivo_color(self):
        """Validar almacenamiento de color en estado"""
        self.assertEqual(self.estado.color, "#FF0000")

class CatalogCRUDTest(TestCase):
    def test_tipo_dispositivo_sigla_optional(self):
        """La sigla es opcional pero recomendada"""
        tipo = TipoDispositivo.objects.create(nombre="Periférico")
        self.assertIsNone(tipo.sigla)

    def test_fabricante_unique_name(self):
        """El nombre del fabricante debería ser único si así se definió (no está explícito en models.py pero es buena práctica)"""
        # Según models.py: nombre = models.CharField(max_length=100)
        # No tiene unique=True. Si no lo tiene, permitira duplicados.
        pass
