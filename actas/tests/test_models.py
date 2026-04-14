import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from actas.models import Acta
from core.tests.factories import ActaFactory, ColaboradorFactory

@pytest.mark.django_db
class TestActaModel:
    def test_folio_generation(self):
        """Verificar que el folio se genera automáticamente con el formato correcto"""
        colaborador = ColaboradorFactory()
        acta = Acta.objects.create(colaborador=colaborador)
        year = timezone.now().year
        assert acta.folio.startswith(f"ACT-{year}-")
        assert len(acta.folio.split('-')[-1]) == 4

    def test_folio_increment(self):
        """Verificar que el folio incrementa secuencialmente"""
        colaborador = ColaboradorFactory()
        acta1 = Acta.objects.create(colaborador=colaborador)
        acta2 = Acta.objects.create(colaborador=colaborador)
        
        num1 = int(acta1.folio.split('-')[-1])
        num2 = int(acta2.folio.split('-')[-1])
        assert num2 == num1 + 1

    def test_blindaje_firmada(self):
        """Verificar que no se puede modificar un acta marcada como firmada"""
        acta = ActaFactory(firmada=True)
        acta.observaciones = "Cambio prohibido"
        with pytest.raises(ValidationError, match="No se puede modificar un acta que ya ha sido marcada como FIRMADA"):
            acta.save()

    def test_str_representation(self):
        """Verificar representación string del acta"""
        colaborador = ColaboradorFactory(first_name="Juan", last_name="Perez")
        acta = ActaFactory(colaborador=colaborador, folio="ACT-2024-0001")
        assert str(acta) == "ACT-2024-0001 - Juan Perez"
