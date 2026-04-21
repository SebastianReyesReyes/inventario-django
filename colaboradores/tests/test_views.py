import pytest
from django.urls import reverse
from colaboradores.models import Colaborador
from colaboradores.tests.factories import ColaboradorFactory

@pytest.mark.django_db
class TestColaboradorViews:
    def setup_method(self):
        # El usuario staff con permiso
        self.admin = ColaboradorFactory(is_staff=True, is_superuser=True)
        self.url_list = reverse('colaboradores:colaborador_list')
        self.url_create = reverse('colaboradores:colaborador_create')

    def test_colaborador_list_view_get(self, client):
        client.force_login(self.admin)
        ColaboradorFactory.create_batch(3)
        
        # Usuario Inactivo no debe aparecer en la lista
        ColaboradorFactory(esta_activo=False, username="inactivo")
        
        response = client.get(self.url_list)
        assert response.status_code == 200
        # Incluye el creador(admin) + 3 = 4. 
        # Pero podemos limitarnos a comprobar que se renderiza bien.
        assert 'colaboradores' in response.context
        assert 'colaboradores/colaborador_list.html' in [t.name for t in response.templates]

        # Comprobar que el inactivo no está en el listado
        usernames = [c.username for c in response.context['colaboradores']]
        assert "inactivo" not in usernames

    def test_colaborador_list_htmx_search(self, client):
        client.force_login(self.admin)
        ColaboradorFactory(first_name="Uniko", last_name="Search", username="uniko123")
        
        # Petición con HTMX simulada
        response = client.get(self.url_list, {'q': 'Uniko'}, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert 'colaboradores' in response.context
        # En HTMX, retorna renderizado parcial
        assert 'colaboradores/partials/colaborador_list_results.html' in [t.name for t in response.templates]

        # Debería filtrar
        resultados = response.context['colaboradores']
        assert len(resultados) == 1
        assert resultados[0].first_name == "Uniko"

    def test_colaborador_create_post(self, client):
        client.force_login(self.admin)
        
        data = {
            'username': 'nuevo_colab',
            'first_name': 'Nuevo',
            'last_name': 'Colaborador',
            'rut': '12345678-5', # Formato válido real
        }
        response = client.post(self.url_create, data)
        assert response.status_code == 302 # Se redirige al éxito
        assert response.url == self.url_list
        assert Colaborador.objects.filter(username='nuevo_colab').exists()

    def test_colaborador_delete_logical_view(self, client):
        client.force_login(self.admin)
        colaborador = ColaboradorFactory()
        url_delete = reverse('colaboradores:colaborador_delete', kwargs={'pk': colaborador.pk})
        
        response = client.post(url_delete)
        # Redirección
        assert response.status_code == 302
        
        colaborador.refresh_from_db()
        assert colaborador.esta_activo is False
