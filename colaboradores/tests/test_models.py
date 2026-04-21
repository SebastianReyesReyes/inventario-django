import pytest
from colaboradores.models import Colaborador
from colaboradores.tests.factories import ColaboradorFactory, DepartamentoFactory, CentroCostoFactory

@pytest.mark.django_db
class TestColaboradorModel:
    
    def test_creacion_colaborador(self):
        """El factory inicializa correctamente"""
        colaborador = ColaboradorFactory()
        assert colaborador.pk is not None
        assert colaborador.esta_activo is True

    def test_nombre_completo_con_nombres(self):
        """Retorna el nombre si existe first_name y last_name"""
        colaborador = ColaboradorFactory(first_name="Juan", last_name="Perez")
        assert colaborador.nombre_completo == "Juan Perez"

    def test_nombre_completo_sin_nombres(self):
        """Retorna el username si no tiene nombres ni apellidos"""
        colaborador = ColaboradorFactory(first_name="", last_name="", username="jdoe")
        assert colaborador.nombre_completo == "jdoe"

    def test_borrado_logico(self):
        """El método delete(). debe ser lógico, no destruir el registro."""
        colaborador = ColaboradorFactory(username="test_del")
        assert colaborador.esta_activo is True
        assert colaborador.is_active is True
        
        # Ejecutamos borrado
        colaborador.delete()
        
        # Refrescamos instancia para asegurar que sigue en la BD
        colaborador.refresh_from_db()
        assert colaborador.esta_activo is False
        assert colaborador.is_active is False
        assert Colaborador.objects.filter(username="test_del").exists()

    def test_relaciones_foraneas(self):
        """Puede guardar correctamente foráneas a Departamento y CC."""
        depto = DepartamentoFactory()
        cc = CentroCostoFactory()
        colaborador = ColaboradorFactory(departamento=depto, centro_costo=cc)
        
        assert colaborador.departamento.pk == depto.pk
        assert colaborador.centro_costo.pk == cc.pk
