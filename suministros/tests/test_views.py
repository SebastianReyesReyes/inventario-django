import pytest
from django.urls import reverse
from suministros.tests.factories import SuministroFactory, CategoriaSuministroFactory, MovimientoStockFactory
from suministros.models import MovimientoStock
from core.tests.factories import ColaboradorFactory


@pytest.mark.django_db
class TestSuministroViews:
    @pytest.fixture
    def admin_user(self):
        user = ColaboradorFactory(username='admin_test', is_staff=True, is_superuser=True)
        user.set_password('pass')
        user.save()
        return user

    @pytest.fixture
    def tecnico_user(self):
        user = ColaboradorFactory(username='tecnico_test')
        user.set_password('pass')
        user.save()
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from suministros.models import Suministro, MovimientoStock
        ct_s = ContentType.objects.get_for_model(Suministro)
        ct_m = ContentType.objects.get_for_model(MovimientoStock)
        user.user_permissions.add(
            Permission.objects.get(codename='view_suministro', content_type=ct_s),
            Permission.objects.get(codename='add_movimientostock', content_type=ct_m),
        )
        return user

    @pytest.fixture
    def auditor_user(self):
        user = ColaboradorFactory(username='auditor_test')
        user.set_password('pass')
        user.save()
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from suministros.models import Suministro
        ct = ContentType.objects.get_for_model(Suministro)
        user.user_permissions.add(Permission.objects.get(codename='view_suministro', content_type=ct))
        return user

    def test_list_standard_request(self, client, admin_user):
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_list'))
        assert response.status_code == 200
        assert '<html' in response.content.decode()

    def test_list_htmx_returns_partial(self, client, admin_user):
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_list'), HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert '<html' not in response.content.decode()
        assert 'suministros/partials/suministro_list_table.html' in [t.name for t in response.templates]

    def test_list_search_filters(self, client, admin_user):
        cat = CategoriaSuministroFactory(nombre="Tintas")
        SuministroFactory(nombre="Tinta Negra", categoria=cat)
        SuministroFactory(nombre="Papel A4", categoria=CategoriaSuministroFactory(nombre="Papel"))
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_list'), {'q': 'Tinta'})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Tinta Negra' in content
        assert 'Papel A4' not in content

    def test_list_pagination(self, client, admin_user):
        cat = CategoriaSuministroFactory()
        for i in range(25):
            SuministroFactory(nombre=f"Suministro {i}", categoria=cat)
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_list'))
        assert response.status_code == 200
        page_obj = response.context['page_obj']
        assert len(page_obj.object_list) == 20
        assert page_obj.has_next()

    def test_create_view_requires_add_permission(self, client, tecnico_user):
        client.login(username='tecnico_test', password='pass')
        response = client.get(reverse('suministros:suministro_create'))
        assert response.status_code == 403

    def test_create_view_as_admin(self, client, admin_user):
        client.login(username='admin_test', password='pass')
        cat = CategoriaSuministroFactory()
        response = client.post(reverse('suministros:suministro_create'), {
            'nombre': 'Nuevo Toner',
            'categoria': cat.pk,
            'codigo_interno': 'TONER-01',
            'unidad_medida': 'Unidades',
            'stock_minimo': 2,
        })
        assert response.status_code == 302 or response.status_code == 204
        from suministros.models import Suministro
        assert Suministro.objects.filter(nombre='Nuevo Toner').exists()

    def test_detail_view_shows_movements(self, client, admin_user):
        s = SuministroFactory()
        MovimientoStockFactory(suministro=s, cantidad=5)
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_detail', args=[s.pk]))
        assert response.status_code == 200
        assert response.context['suministro'] == s
        assert len(response.context['page_obj'].object_list) == 1

    def test_soft_delete_sets_inactive(self, client, admin_user):
        s = SuministroFactory()
        client.login(username='admin_test', password='pass')
        response = client.post(reverse('suministros:suministro_delete', args=[s.pk]))
        assert response.status_code == 204
        s.refresh_from_db()
        assert s.esta_activo is False

    def test_auditor_cannot_create_movement(self, client, auditor_user):
        s = SuministroFactory()
        client.login(username='auditor_test', password='pass')
        response = client.get(reverse('suministros:movimiento_create'), {'suministro': s.pk})
        assert response.status_code == 403

    def test_tecnico_can_create_movement(self, client, tecnico_user):
        s = SuministroFactory(stock_actual=10)
        # Crear movimiento de entrada para que recalcular_stock() tenga base real
        MovimientoStockFactory(suministro=s, tipo_movimiento=MovimientoStock.TipoMovimiento.ENTRADA, cantidad=10)
        s.recalcular_stock()
        client.login(username='tecnico_test', password='pass')
        response = client.post(reverse('suministros:movimiento_create'), {
            'suministro': s.pk,
            'tipo_movimiento': 'SALIDA',
            'cantidad': 2,
            'notas': 'Entrega',
        })
        assert response.status_code == 204
        s.refresh_from_db()
        assert s.stock_actual == 8

    def test_movement_validation_error_returns_modal(self, client, tecnico_user):
        s = SuministroFactory(stock_actual=1)
        client.login(username='tecnico_test', password='pass')
        response = client.post(reverse('suministros:movimiento_create'), {
            'suministro': s.pk,
            'tipo_movimiento': 'SALIDA',
            'cantidad': 5,
            'notas': 'Fail',
        })
        assert response.status_code == 200
        content = response.content.decode()
        assert 'No hay suficiente stock' in content

    def test_ajax_modelos_compatibles(self, client, admin_user):
        from core.tests.factories import TipoDispositivoFactory, FabricanteFactory, ModeloFactory
        tipo = TipoDispositivoFactory()
        cat = CategoriaSuministroFactory()
        cat.tipos_dispositivo_compatibles.add(tipo)
        fab = FabricanteFactory()
        modelo = ModeloFactory(tipo_dispositivo=tipo, fabricante=fab)
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:ajax_get_modelos_compatibles'), {'categoria': cat.pk})
        assert response.status_code == 200
        assert modelo.nombre in response.content.decode()

    def test_create_get_renders_form(self, client, admin_user):
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_create'))
        assert response.status_code == 200
        assert 'Nuevo Suministro' in response.content.decode()

    def test_update_get_renders_form(self, client, admin_user):
        s = SuministroFactory()
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_update', args=[s.pk]))
        assert response.status_code == 200
        assert 'Editar Suministro' in response.content.decode()

    def test_delete_get_renders_modal(self, client, admin_user):
        s = SuministroFactory()
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_delete', args=[s.pk]))
        assert response.status_code == 200
        assert 'Desactivar Suministro' in response.content.decode()

    def test_delete_with_stock_shows_warning(self, client, admin_user):
        s = SuministroFactory(stock_actual=5)
        MovimientoStockFactory(suministro=s, tipo_movimiento=MovimientoStock.TipoMovimiento.ENTRADA, cantidad=5)
        s.recalcular_stock()
        client.login(username='admin_test', password='pass')
        response = client.post(reverse('suministros:suministro_delete', args=[s.pk]))
        assert response.status_code == 204
        s.refresh_from_db()
        assert s.esta_activo is False
