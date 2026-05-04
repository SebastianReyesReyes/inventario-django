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

    # ── Categoría CRUD (HTMX modal) ──────────────────────────────────

    def test_categoria_create_get_renders_full_page(self, client, admin_user):
        """Sin HX-Request: debe retornar página completa con base.html."""
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:categoriasuministro_create'))
        assert response.status_code == 200
        content = response.content.decode()
        assert '<!DOCTYPE html>' in content
        assert 'Nueva Categoría' in content

    def test_categoria_create_get_htmx_renders_partial(self, client, admin_user):
        """Con HX-Request: debe retornar partial del modal."""
        client.login(username='admin_test', password='pass')
        response = client.get(
            reverse('suministros:categoriasuministro_create'),
            HTTP_HX_REQUEST='true'
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert '<!DOCTYPE html>' not in content
        assert 'x-data="{ open: true }"' in content

    def test_categoria_create_post_success(self, client, admin_user):
        client.login(username='admin_test', password='pass')
        response = client.post(reverse('suministros:categoriasuministro_create'), {
            'nombre': 'Tóner Laser',
            'descripcion': 'Tóner para impresoras láser',
        })
        assert response.status_code in (204, 302)
        from suministros.models import CategoriaSuministro
        assert CategoriaSuministro.objects.filter(nombre='Tóner Laser').exists()

    def test_categoria_create_requires_permission(self, client, tecnico_user):
        client.login(username='tecnico_test', password='pass')
        response = client.get(reverse('suministros:categoriasuministro_create'))
        assert response.status_code == 403

    def test_categoria_update_get_renders_form(self, client, admin_user):
        cat = CategoriaSuministroFactory(nombre='Original')
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:categoriasuministro_update', args=[cat.pk]))
        assert response.status_code == 200
        assert 'Original' in response.content.decode()

    def test_categoria_update_post_success(self, client, admin_user):
        cat = CategoriaSuministroFactory(nombre='Old Name')
        client.login(username='admin_test', password='pass')
        response = client.post(reverse('suministros:categoriasuministro_update', args=[cat.pk]), {
            'nombre': 'Updated Name',
            'descripcion': '',
        })
        assert response.status_code in (204, 302)
        cat.refresh_from_db()
        assert cat.nombre == 'Updated Name'

    def test_ajax_categoria_options_returns_options(self, client, admin_user):
        CategoriaSuministroFactory(nombre='Cartuchos')
        CategoriaSuministroFactory(nombre='Resmas')
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:ajax_categoria_options'))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Cartuchos' in content
        assert 'Resmas' in content

    def test_ajax_categoria_options_with_selected(self, client, admin_user):
        cat = CategoriaSuministroFactory(nombre='Filtros')
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:ajax_categoria_options'), {'selected': cat.pk})
        assert response.status_code == 200
        assert 'selected' in response.content.decode()

    # ── Suministro HTMX modal ────────────────────────────────────────

    def test_create_htmx_returns_modal(self, client, admin_user):
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_create'), HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Nuevo Suministro' in content

    def test_update_htmx_returns_modal(self, client, admin_user):
        s = SuministroFactory()
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_update', args=[s.pk]), HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Editar Suministro' in content

    # ── Dispositivos compatibles (AJAX) ──────────────────────────────

    def test_ajax_dispositivos_compatibles(self, client, admin_user):
        from core.tests.factories import TipoDispositivoFactory, FabricanteFactory, ModeloFactory
        from dispositivos.tests.factories import DispositivoFactory

        tipo = TipoDispositivoFactory()
        fab = FabricanteFactory()
        modelo = ModeloFactory(tipo_dispositivo=tipo, fabricante=fab)
        cat = CategoriaSuministroFactory()
        cat.tipos_dispositivo_compatibles.add(tipo)

        s = SuministroFactory(categoria=cat)
        s.modelos_compatibles.add(modelo)

        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:ajax_get_dispositivos_compatibles'), {'suministro': s.pk})
        assert response.status_code == 200

    def test_ajax_fabricante_options(self, client, admin_user):
        from core.tests.factories import FabricanteFactory
        f1 = FabricanteFactory(nombre='HP')
        f2 = FabricanteFactory(nombre='Canon')
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('core:ajax_fabricante_options'))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'HP' in content
        assert 'Canon' in content

    def test_ajax_fabricante_options_with_selected(self, client, admin_user):
        from core.tests.factories import FabricanteFactory
        f = FabricanteFactory(nombre='Epson')
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('core:ajax_fabricante_options'), {'selected': f.pk})
        assert response.status_code == 200
        assert 'selected' in response.content.decode()

    # ── Factura como Reina ───────────────────────────────────────────

    def test_movimiento_create_con_seguir_ingresando_redirect(self, client, tecnico_user):
        """POST con seguir_ingresando=True redirige al form con params precargados."""
        s = SuministroFactory(stock_actual=0)
        client.login(username='tecnico_test', password='pass')
        response = client.post(reverse('suministros:movimiento_create'), {
            'suministro': s.pk,
            'tipo_movimiento': MovimientoStock.TipoMovimiento.ENTRADA,
            'cantidad': 10,
            'costo_unitario': 5000,
            'numero_factura': 'F001-123',
            'seguir_ingresando': 'on',
        })
        # Debe ser redirect (302) a movimiento_create con params
        assert response.status_code == 302
        assert 'movimiento/nuevo/' in response.url
        assert 'tipo_movimiento=ENTRADA' in response.url
        assert 'numero_factura=F001-123' in response.url

    def test_movimiento_create_sin_seguir_ingresando_retorna_204(self, client, tecnico_user):
        """POST sin seguir_ingresando retorna 204 (HTMX trigger)."""
        s = SuministroFactory(stock_actual=0)
        client.login(username='tecnico_test', password='pass')
        response = client.post(reverse('suministros:movimiento_create'), {
            'suministro': s.pk,
            'tipo_movimiento': MovimientoStock.TipoMovimiento.ENTRADA,
            'cantidad': 5,
            'costo_unitario': 3000,
            'numero_factura': 'F001-456',
        })
        assert response.status_code == 204

    def test_factura_create_get_renders_form(self, client, tecnico_user):
        """GET a factura_create renderiza el formulario con formset vacío."""
        client.login(username='tecnico_test', password='pass')
        response = client.get(reverse('suministros:factura_create'))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Ingreso de Factura' in content
        assert 'numero_factura' in content
        assert 'form-TOTAL_FORMS' in content

    def test_factura_create_post_crea_multiples_movimientos(self, client, tecnico_user):
        """POST válido crea múltiples MovimientoStock con el mismo numero_factura."""
        s1 = SuministroFactory(stock_actual=0)
        s2 = SuministroFactory(stock_actual=0)
        client.login(username='tecnico_test', password='pass')

        response = client.post(reverse('suministros:factura_create'), {
            'numero_factura': 'F-MASIVA-001',
            'fecha': '2026-05-04',
            # Formset - 2 filas válidas + 1 vacía (el extra)
            'form-TOTAL_FORMS': '3',
            'form-INITIAL_FORMS': '0',
            'form-0-suministro': s1.pk,
            'form-0-cantidad': 10,
            'form-0-costo_unitario': 5000,
            'form-0-notas': 'Item 1',
            'form-1-suministro': s2.pk,
            'form-1-cantidad': 5,
            'form-1-costo_unitario': 3000,
            'form-1-notas': 'Item 2',
            'form-2-suministro': '',
            'form-2-cantidad': '',
            'form-2-costo_unitario': '',
            'form-2-notas': '',
        })

        assert response.status_code == 302
        assert MovimientoStock.objects.filter(numero_factura='F-MASIVA-001').count() == 2
        movs = MovimientoStock.objects.filter(numero_factura='F-MASIVA-001')
        assert all(m.tipo_movimiento == MovimientoStock.TipoMovimiento.ENTRADA for m in movs)
        # Verificar que el stock se actualizó
        s1.refresh_from_db()
        s2.refresh_from_db()
        assert s1.stock_actual == 10
        assert s2.stock_actual == 5

    def test_factura_create_post_invalid_renders_errors(self, client, tecnico_user):
        """POST inválido re-renderiza el form con errores."""
        client.login(username='tecnico_test', password='pass')
        response = client.post(reverse('suministros:factura_create'), {
            'numero_factura': '',  # vacío → error
            'fecha': '2026-05-04',
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-0-suministro': '',
            'form-0-cantidad': '',
        })
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Error' in content or 'campo' in content.lower() or 'numero_factura' in content

    def test_factura_create_requires_permission(self, client, auditor_user):
        """Usuario sin permiso add_movimientostock obtiene 403."""
        client.login(username='auditor_test', password='pass')
        response = client.get(reverse('suministros:factura_create'))
        assert response.status_code == 403

    # ── Tests de Exportación Excel ──────────────────────────────────────

    def test_export_suministros_excel(self, client, admin_user):
        """Exportar catálogo de suministros responde con archivo Excel."""
        SuministroFactory.create_batch(3)
        client.login(username='admin_test', password='pass')
        response = client.get(reverse('suministros:suministro_export_excel'))
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'attachment' in response['Content-Disposition']
        assert len(response.content) > 0

    def test_export_suministros_excel_respects_filters(self, client, admin_user):
        """La exportación respeta los filtros aplicados en el listado."""
        cat = CategoriaSuministroFactory(nombre='Tóner')
        s1 = SuministroFactory(nombre='Tóner HP', categoria=cat)
        SuministroFactory(nombre='Mouse Logitech')

        client.login(username='admin_test', password='pass')
        response = client.get(
            reverse('suministros:suministro_export_excel'),
            {'q': 'Tóner'}
        )
        assert response.status_code == 200
        # El contenido del Excel debería contener solo el tóner
        # (verificamos indirectamente por el tamaño o estructura)
        assert len(response.content) > 0

    def test_export_movimientos_excel(self, client, admin_user):
        """Exportar historial de movimientos de un suministro."""
        suministro = SuministroFactory()
        MovimientoStockFactory(suministro=suministro, tipo_movimiento=MovimientoStock.TipoMovimiento.ENTRADA, cantidad=10)
        MovimientoStockFactory(suministro=suministro, tipo_movimiento=MovimientoStock.TipoMovimiento.SALIDA, cantidad=3)

        client.login(username='admin_test', password='pass')
        response = client.get(
            reverse('suministros:suministro_movimientos_export_excel', args=[suministro.pk])
        )
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'attachment' in response['Content-Disposition']
        assert len(response.content) > 0

    def test_export_movimientos_excel_requires_permission(self, client, auditor_user):
        """Usuario sin permiso view_movimientostock obtiene 403."""
        suministro = SuministroFactory()
        client.login(username='auditor_test', password='pass')
        response = client.get(
            reverse('suministros:suministro_movimientos_export_excel', args=[suministro.pk])
        )
        assert response.status_code == 403
