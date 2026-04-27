import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from dispositivos.tests.factories import DispositivoFactory, TipoDispositivoFactory
from core.tests.factories import ModeloFactory
from dispositivos.models import Dispositivo

@pytest.mark.django_db
class TestDispositivoModel:
    def test_valor_contable_negativo(self):
        """Verifica que el modelo rechace valores contables negativos."""
        # Se guarda el modelo por defecto porque factory() invoca save()
        # Pero podemos usar build() en memoria para testear el clean puro.
        d = DispositivoFactory.build(valor_contable=-100)
        with pytest.raises(ValidationError) as exc:
            d.clean()
        assert "El valor contable debe ser positivo." in str(exc.value)

    def test_fecha_compra_futura(self):
        """Verifica que no se admitan compras en el futuro."""
        futuro = timezone.now().date() + timedelta(days=1)
        d = DispositivoFactory.build(fecha_compra=futuro)
        with pytest.raises(ValidationError) as exc:
            d.clean()
        assert "La fecha de compra no puede ser futura." in str(exc.value)

    def test_generador_identificador_interno(self):
        """Verifica que al guardar un dispositivo se asigne un ID consecutivo."""
        tipo = TipoDispositivoFactory(nombre="Desktop", sigla="DSK")
        modelo = ModeloFactory(tipo_dispositivo=tipo)
        # .create() sí llama a save() directamente
        d1 = DispositivoFactory.create(modelo=modelo)
        assert d1.identificador_interno == "JMIE-DSK-0001"

        d2 = DispositivoFactory.create(modelo=modelo)
        assert d2.identificador_interno == "JMIE-DSK-0002"

        tipo2 = TipoDispositivoFactory(nombre="Tablet", sigla="TAB")
        modelo2 = ModeloFactory(tipo_dispositivo=tipo2)
        d3 = DispositivoFactory.create(modelo=modelo2)
        assert d3.identificador_interno == "JMIE-TAB-0001"
