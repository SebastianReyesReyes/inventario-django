import pytest
from actas.forms import ActaCrearForm
from core.tests.factories import ColaboradorFactory

@pytest.mark.django_db
class TestActaForms:
    def test_ministro_de_fe_filtering(self):
        """Verifica que el dropdown de ministro de fe solo incluya administradores, jefes o encargados activos."""
        admin = ColaboradorFactory(cargo="Administrador de Red", esta_activo=True)
        jefe = ColaboradorFactory(cargo="Jefe de Soporte", esta_activo=True)
        normal = ColaboradorFactory(cargo="Operador", esta_activo=True)
        inactivo = ColaboradorFactory(cargo="Jefe Anterior", esta_activo=False)

        form = ActaCrearForm()
        ministros = list(form.fields['ministro_de_fe'].queryset)

        # Los permitidos deben estar
        assert admin in ministros
        assert jefe in ministros
        
        # Excluidos
        assert normal not in ministros
        assert inactivo not in ministros

    def test_colaborador_activo_filtering(self):
        """Verifica que solo los colaboradores activos estén en el listado base."""
        activo = ColaboradorFactory(esta_activo=True)
        inactivo = ColaboradorFactory(esta_activo=False)
        
        form = ActaCrearForm()
        colaboradores = list(form.fields['colaborador'].queryset)
        
        assert activo in colaboradores
        assert inactivo not in colaboradores
