import pytest
from django.urls import reverse
from core.tests.factories import ColaboradorFactory, ActaFactory, HistorialAsignacionFactory

@pytest.mark.django_db
class TestActaViews:
    def test_acta_list_view(self, client):
        """Verificar carga de lista de actas"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        
        acta = ActaFactory(folio="ACT-TEST-001")
        
        url = reverse('actas:acta_list')
        response = client.get(url)
        assert response.status_code == 200
        assert "ACT-TEST-001" in response.content.decode('utf-8')

    def test_acta_list_htmx_partial(self, client):
        """Verificar que HTMX devuelve solo las filas de la tabla"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        
        url = reverse('actas:acta_list')
        response = client.get(url, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert '<html' not in html
        assert '<tr' in html

    def test_asignaciones_pendientes_view(self, client):
        """Verificar que muestra asignaciones pendientes del colaborador seleccionado"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        
        colaborador = ColaboradorFactory()
        h_pendiente = HistorialAsignacionFactory(colaborador=colaborador, acta=None)
        
        url = reverse('actas:acta_asignaciones_pendientes', kwargs={'colaborador_pk': colaborador.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert str(h_pendiente.dispositivo.numero_serie) in response.content.decode('utf-8')

    def test_acta_detail_view(self, client):
        """Verificar carga del detalle del acta"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        
        acta = ActaFactory()
        url = reverse('actas:acta_detail', kwargs={'pk': acta.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert acta.folio in response.content.decode('utf-8')
