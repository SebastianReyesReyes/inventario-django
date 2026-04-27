import pytest
from django.urls import reverse
from suministros.tests.factories import SuministroFactory, CategoriaSuministroFactory
from core.tests.factories import ColaboradorFactory
from suministros.models import MovimientoStock


@pytest.mark.django_db
class TestSuministrosIntegration:
    @pytest.fixture
    def admin(self):
        u = ColaboradorFactory(username='int_admin', is_superuser=True)
        u.set_password('pass')
        u.save()
        return u

    def test_full_stock_flow(self, client, admin):
        """Crear suministro → entrada → salida → verificar stock → oversale → error"""
        client.login(username='int_admin', password='pass')
        cat = CategoriaSuministroFactory()

        # 1. Crear
        response = client.post(reverse('suministros:suministro_create'), {
            'nombre': 'Tóner X',
            'categoria': cat.pk,
            'codigo_interno': 'TN-X',
            'unidad_medida': 'Unidades',
            'stock_minimo': 2,
        })
        assert response.status_code in (302, 204)
        from suministros.models import Suministro
        s = Suministro.objects.get(nombre='Tóner X')
        assert s.stock_actual == 0

        # 2. Entrada 10
        response = client.post(reverse('suministros:movimiento_create'), {
            'suministro': s.pk,
            'tipo_movimiento': MovimientoStock.TipoMovimiento.ENTRADA,
            'cantidad': 10,
            'notas': 'Compra',
        })
        assert response.status_code == 204
        s.refresh_from_db()
        assert s.stock_actual == 10

        # 3. Salida 3
        response = client.post(reverse('suministros:movimiento_create'), {
            'suministro': s.pk,
            'tipo_movimiento': MovimientoStock.TipoMovimiento.SALIDA,
            'cantidad': 3,
            'notas': 'Entrega',
        })
        assert response.status_code == 204
        s.refresh_from_db()
        assert s.stock_actual == 7

        # 4. Oversale
        response = client.post(reverse('suministros:movimiento_create'), {
            'suministro': s.pk,
            'tipo_movimiento': MovimientoStock.TipoMovimiento.SALIDA,
            'cantidad': 99,
            'notas': 'Fail',
        })
        assert response.status_code == 200
        s.refresh_from_db()
        assert s.stock_actual == 7  # sin cambio

        # 5. Soft delete
        response = client.post(reverse('suministros:suministro_delete', args=[s.pk]))
        assert response.status_code == 204
        s.refresh_from_db()
        assert s.esta_activo is False

    def test_list_excludes_inactive(self, client, admin):
        client.login(username='int_admin', password='pass')
        cat = CategoriaSuministroFactory()
        active = SuministroFactory(nombre="Activo", categoria=cat, esta_activo=True)
        inactive = SuministroFactory(nombre="Inactivo", categoria=cat, esta_activo=False)

        response = client.get(reverse('suministros:suministro_list'))
        content = response.content.decode()
        assert 'Activo' in content
        assert 'Inactivo' not in content

    def test_htmx_partial_vs_full_page(self, client, admin):
        client.login(username='int_admin', password='pass')
        SuministroFactory()

        # Full page
        response = client.get(reverse('suministros:suministro_list'))
        assert '<html' in response.content.decode()

        # HTMX partial
        response = client.get(reverse('suministros:suministro_list'), HTTP_HX_REQUEST='true')
        assert '<html' not in response.content.decode()
        assert '<table' in response.content.decode()
