import pytest
from django.urls import reverse
from core.tests.factories import ColaboradorFactory, DispositivoFactory, EstadoDispositivoFactory

@pytest.mark.django_db
class TestDispositivoViews:
    def test_dispositivo_list_standard_request(self, client):
        """Test full page load contains layout template headers"""
        user = ColaboradorFactory(username='testuser')
        user.set_password('password')
        user.save()
        
        # Asignar permiso de ver dispositivos
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from dispositivos.models import Dispositivo
        content_type = ContentType.objects.get_for_model(Dispositivo)
        permission = Permission.objects.get(codename='view_dispositivo', content_type=content_type)
        user.user_permissions.add(permission)
        
        client.login(username='testuser', password='password')
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url)
        assert response.status_code == 200
        html_content = response.content.decode('utf-8')
        assert '<html' in html_content
        assert '<body' in html_content

    def test_dispositivo_list_htmx_request(self, client):
        """Test HTMX request only returns the un-layered partial HTML (No layout)"""
        user = ColaboradorFactory(username='testhtmx')
        user.set_password('password')
        user.save()
        
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from dispositivos.models import Dispositivo
        content_type = ContentType.objects.get_for_model(Dispositivo)
        permission = Permission.objects.get(codename='view_dispositivo', content_type=content_type)
        user.user_permissions.add(permission)
        
        client.login(username='testhtmx', password='password')
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        html_content = response.content.decode('utf-8')
        assert '<html' not in html_content
        assert '<body' not in html_content
        # Al menos debería haber un mensaje de no encontrado o la tabla
        assert 'No se encontraron dispositivos' in html_content or '<tr' in html_content

    def test_dispositivo_list_with_data(self, client):
        """Test list view shows created devices"""
        user = ColaboradorFactory(username='testdata', is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        
        estado = EstadoDispositivoFactory(nombre="Disponible")
        dispositivo = DispositivoFactory(estado=estado, numero_serie="UNIQUE-SN-123")
        
        client.login(username='testdata', password='password')
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url)
        assert response.status_code == 200
        assert "UNIQUE-SN-123" in response.content.decode('utf-8')
