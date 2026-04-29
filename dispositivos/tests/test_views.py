import pytest
from django.urls import reverse
from core.tests.factories import (
    ColaboradorFactory, DispositivoFactory, EstadoDispositivoFactory,
    HistorialAsignacionFactory, TipoDispositivoFactory, FabricanteFactory,
    CentroCostoFactory, ModeloFactory
)


@pytest.mark.django_db
class TestDispositivoViews:
    def test_dispositivo_list_standard_request(self, client):
        """Test full page load contains layout template headers"""
        user = ColaboradorFactory(username='testuser')
        user.set_password('password')
        user.save()

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

    def test_dispositivo_list_htmx_sort_returns_table_partial(self, client):
        """HTMX request con sorting debe retornar el partial de tabla completa (headers + filas)"""
        user = ColaboradorFactory(username='testhtmxsort')
        user.set_password('password')
        user.save()

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from dispositivos.models import Dispositivo
        content_type = ContentType.objects.get_for_model(Dispositivo)
        permission = Permission.objects.get(codename='view_dispositivo', content_type=content_type)
        user.user_permissions.add(permission)

        client.login(username='testhtmxsort', password='password')
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'sort': 'id', 'order': 'asc'}, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert 'dispositivos/partials/dispositivo_list_table.html' in [t.name for t in response.templates]
        html_content = response.content.decode('utf-8')
        assert '<thead>' in html_content
        assert '<tbody' in html_content

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

    def test_dispositivo_list_returns_page_obj(self, client):
        user = ColaboradorFactory(username='adminpage', is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username='adminpage', password='password')
        for i in range(25):
            DispositivoFactory(identificador_interno=f"JMIE-NOT-{i:05d}")
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url)
        assert response.status_code == 200
        assert 'page_obj' in response.context
        assert response.context['page_obj'].paginator.per_page == 20

    def test_dispositivo_list_invalid_page_fallback(self, client):
        user = ColaboradorFactory(username='adminfallback', is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username='adminfallback', password='password')
        DispositivoFactory()
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'page': 'xyz'})
        assert response.status_code == 200
        assert response.context['page_obj'].number == 1

    def test_dispositivo_list_htmx_pagination(self, client):
        user = ColaboradorFactory(username='adminhtmx', is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username='adminhtmx', password='password')
        for i in range(25):
            DispositivoFactory(identificador_interno=f"JMIE-NOT-{i:05d}")
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'page': '2'}, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert 'dispositivos/partials/dispositivo_list_table.html' in [t.name for t in response.templates]
        assert response.context['page_obj'].number == 2
        html = response.content.decode('utf-8')
        assert 'JMIE-NOT-00020' in html


@pytest.mark.django_db
class TestTrazabilidadViews:
    """Pruebas de regresión para contratos HTMX y flujos transaccionales."""

    def _login_superuser(self, client):
        user = ColaboradorFactory(username='admintraz', is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username='admintraz', password='password')
        return user

    # ------------------------------------------------------------------
    # Asignar
    # ------------------------------------------------------------------
    def test_asignar_get_modal(self, client):
        user = self._login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Disponible'))
        url = reverse('dispositivos:dispositivo_asignar', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert 'dispositivos/partials/asignacion_form_modal.html' in [t.name for t in response.templates]

    def test_asignar_post_htmx_crea_acta(self, client):
        user = self._login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Disponible'), propietario_actual=None)
        colaborador = ColaboradorFactory()
        url = reverse('dispositivos:dispositivo_asignar', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'colaborador': colaborador.pk,
            'condicion_fisica': 'Buen estado general',
            'generar_acta': 'on'
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert response['HX-Trigger'] == 'asignacion-saved'
        assert 'dispositivos/partials/trazabilidad_success.html' in [t.name for t in response.templates]
        dispositivo.refresh_from_db()
        assert dispositivo.propietario_actual == colaborador
        assert dispositivo.estado.nombre == 'Asignado'
        assert dispositivo.historial.filter(colaborador=colaborador).exists()

    def test_asignar_post_sin_htmx_redirect(self, client):
        user = self._login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Disponible'), propietario_actual=None)
        colaborador = ColaboradorFactory()
        url = reverse('dispositivos:dispositivo_asignar', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'colaborador': colaborador.pk,
            'condicion_fisica': 'Buen estado',
            'generar_acta': ''
        })
        assert response.status_code == 302
        assert response.url == reverse('dispositivos:dispositivo_detail', kwargs={'pk': dispositivo.pk})

    # ------------------------------------------------------------------
    # Reasignar
    # ------------------------------------------------------------------
    def test_reasignar_get_modal(self, client):
        user = self._login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Asignado'))
        HistorialAsignacionFactory(dispositivo=dispositivo, fecha_fin=None)
        url = reverse('dispositivos:dispositivo_reasignar', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert 'dispositivos/partials/reasignacion_form_modal.html' in [t.name for t in response.templates]

    def test_reasignar_post_htmx_cierra_anterior(self, client):
        user = self._login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Asignado'))
        anterior = ColaboradorFactory()
        nuevo = ColaboradorFactory()
        hist = HistorialAsignacionFactory(dispositivo=dispositivo, colaborador=anterior, fecha_fin=None)
        url = reverse('dispositivos:dispositivo_reasignar', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'colaborador': nuevo.pk,
            'condicion_fisica': 'Con rayones leves',
            'generar_acta': ''
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert response['HX-Trigger'] == 'asignacion-saved'
        hist.refresh_from_db()
        assert hist.fecha_fin is not None
        dispositivo.refresh_from_db()
        assert dispositivo.propietario_actual == nuevo

    # ------------------------------------------------------------------
    # Devolver
    # ------------------------------------------------------------------
    def test_devolver_get_modal(self, client):
        user = self._login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Asignado'))
        HistorialAsignacionFactory(dispositivo=dispositivo, fecha_fin=None)
        url = reverse('dispositivos:dispositivo_devolver', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert 'dispositivos/partials/devolucion_form_modal.html' in [t.name for t in response.templates]

    def test_devolver_post_htmx_danado(self, client):
        user = self._login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Asignado'))
        colaborador = ColaboradorFactory()
        HistorialAsignacionFactory(dispositivo=dispositivo, colaborador=colaborador, fecha_fin=None)
        url = reverse('dispositivos:dispositivo_devolver', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'condicion_fisica': 'Pantalla rota',
            'estado_llegada': 'danado',
            'generar_acta': ''
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert response['HX-Trigger'] == 'asignacion-saved'
        dispositivo.refresh_from_db()
        assert dispositivo.estado.nombre == 'En Reparación'
        assert dispositivo.propietario_actual is None

    def test_devolver_post_htmx_bueno(self, client):
        user = self._login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoDispositivoFactory(nombre='Asignado'))
        colaborador = ColaboradorFactory()
        HistorialAsignacionFactory(dispositivo=dispositivo, colaborador=colaborador, fecha_fin=None)
        url = reverse('dispositivos:dispositivo_devolver', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'condicion_fisica': 'Perfecto estado',
            'estado_llegada': 'bueno',
            'generar_acta': ''
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        dispositivo.refresh_from_db()
        assert dispositivo.estado.nombre == 'Disponible'
        assert dispositivo.propietario_actual is None

    # ------------------------------------------------------------------
    # Entrega Accesorio
    # ------------------------------------------------------------------
    def test_entrega_accesorio_get_modal(self, client):
        user = self._login_superuser(client)
        colaborador = ColaboradorFactory()
        url = reverse('dispositivos:colaborador_entrega_accesorio', kwargs={'pk': colaborador.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert 'dispositivos/partials/accesorio_form_modal.html' in [t.name for t in response.templates]

    def test_entrega_accesorio_post_htmx_trigger(self, client):
        user = self._login_superuser(client)
        colaborador = ColaboradorFactory()
        url = reverse('dispositivos:colaborador_entrega_accesorio', kwargs={'pk': colaborador.pk})
        response = client.post(url, {
            'tipo': 'Mouse',
            'cantidad': 2,
            'descripcion': 'Mouse inalámbrico'
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert response['HX-Trigger'] == 'accesorio-saved'
        assert 'dispositivos/partials/accesorio_success.html' in [t.name for t in response.templates]
        assert colaborador.accesorios.filter(tipo='Mouse').exists()

    # ------------------------------------------------------------------
    # Eliminar Dispositivo
    # ------------------------------------------------------------------
    def test_delete_post_htmx_hx_redirect(self, client):
        user = self._login_superuser(client)
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:dispositivo_delete', kwargs={'pk': dispositivo.pk})
        response = client.post(url, HTTP_HX_REQUEST='true')
        assert response.status_code == 204
        assert response['HX-Redirect'] == reverse('dispositivos:dispositivo_list')

    def test_delete_post_sin_htmx_redirect(self, client):
        user = self._login_superuser(client)
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:dispositivo_delete', kwargs={'pk': dispositivo.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert response.url == reverse('dispositivos:dispositivo_list')

    def test_dispositivo_list_sort_by_id_asc(self, client):
        """Verificar ordenamiento ascendente por ID"""
        user = self._login_superuser(client)
        d1 = DispositivoFactory(identificador_interno="JMIE-NOT-00001")
        d2 = DispositivoFactory(identificador_interno="JMIE-NOT-00002")
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'sort': 'id', 'order': 'asc'})
        assert response.status_code == 200
        ids = [d.identificador_interno for d in response.context['dispositivos']]
        assert ids.index("JMIE-NOT-00001") < ids.index("JMIE-NOT-00002")

    def test_dispositivo_list_sort_by_id_desc(self, client):
        """Verificar ordenamiento descendente por ID"""
        user = self._login_superuser(client)
        d1 = DispositivoFactory(identificador_interno="JMIE-NOT-00001")
        d2 = DispositivoFactory(identificador_interno="JMIE-NOT-00002")
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'sort': 'id', 'order': 'desc'})
        assert response.status_code == 200
        ids = [d.identificador_interno for d in response.context['dispositivos']]
        assert ids.index("JMIE-NOT-00002") < ids.index("JMIE-NOT-00001")

    def test_dispositivo_list_sort_by_estado(self, client):
        """Verificar ordenamiento por estado"""
        user = self._login_superuser(client)
        est1 = EstadoDispositivoFactory(nombre="Asignado")
        est2 = EstadoDispositivoFactory(nombre="Disponible")
        DispositivoFactory(estado=est1)
        DispositivoFactory(estado=est2)
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'sort': 'estado', 'order': 'asc'})
        assert response.status_code == 200
        estados = [d.estado.nombre for d in response.context['dispositivos']]
        assert estados.index("Asignado") < estados.index("Disponible")

    def test_dispositivo_list_sort_by_tipo(self, client):
        """Verificar ordenamiento por tipo"""
        user = self._login_superuser(client)
        tipo1 = TipoDispositivoFactory(nombre="Notebook")
        tipo2 = TipoDispositivoFactory(nombre="Smartphone")
        modelo1 = ModeloFactory(tipo_dispositivo=tipo1)
        modelo2 = ModeloFactory(tipo_dispositivo=tipo2)
        DispositivoFactory(modelo=modelo1)
        DispositivoFactory(modelo=modelo2)
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'sort': 'tipo', 'order': 'asc'})
        assert response.status_code == 200
        tipos = [d.modelo.tipo_dispositivo.nombre for d in response.context['dispositivos']]
        assert tipos.index("Notebook") < tipos.index("Smartphone")

    def test_create_dispositivo_genera_acta(self, client):
        """Al crear dispositivo con propietario y generar_acta=True, debe crear acta y redirigir al detalle"""
        user = self._login_superuser(client)
        colaborador = ColaboradorFactory()
        tipo = TipoDispositivoFactory(nombre="Impresora")  # Tipo genérico para evitar campos técnicos
        estado = EstadoDispositivoFactory(nombre="Disponible")
        fabricante = FabricanteFactory()
        modelo = ModeloFactory(fabricante=fabricante, tipo_dispositivo=tipo)
        cc = CentroCostoFactory()
        
        url = reverse('dispositivos:dispositivo_create')
        response = client.post(url, {
            'numero_serie': 'SN-TEST-001',
            'tipo': tipo.pk,
            'estado': estado.pk,
            'modelo': modelo.pk,
            'centro_costo': cc.pk,
            'fabricante': fabricante.pk,
            'propietario_actual': colaborador.pk,
            'notas_condicion': 'Nuevo',
            'valor_contable': 500000,
            'generar_acta': 'on',
        })
        
        assert response.status_code == 200
        from dispositivos.models import Dispositivo
        dispositivo = Dispositivo.objects.get(numero_serie='SN-TEST-001')
        
        from actas.models import Acta
        assert Acta.objects.filter(colaborador=colaborador).exists()
        acta = Acta.objects.filter(colaborador=colaborador).first()
        assert acta.tipo_acta == 'ENTREGA'
        
        assert response.context['show_acta_modal'] is True
        assert response.context['acta'] == acta
        assert response.context['d'] == dispositivo

    def test_create_dispositivo_sin_generar_acta(self, client):
        """Al crear dispositivo sin generar_acta, no debe crear acta"""
        user = self._login_superuser(client)
        colaborador = ColaboradorFactory()
        tipo = TipoDispositivoFactory(nombre="Impresora")
        estado = EstadoDispositivoFactory()
        fabricante = FabricanteFactory()
        modelo = ModeloFactory(fabricante=fabricante, tipo_dispositivo=tipo)
        cc = CentroCostoFactory()
        
        url = reverse('dispositivos:dispositivo_create')
        response = client.post(url, {
            'numero_serie': 'SN-TEST-002',
            'tipo': tipo.pk,
            'estado': estado.pk,
            'modelo': modelo.pk,
            'centro_costo': cc.pk,
            'fabricante': fabricante.pk,
            'propietario_actual': colaborador.pk,
            'notas_condicion': 'Nuevo',
            'valor_contable': 500000,
        })
        
        assert response.status_code == 302
        from actas.models import Acta
        assert not Acta.objects.filter(colaborador=colaborador).exists()

    def test_update_dispositivo_cambio_propietario_genera_acta(self, client):
        """Al editar y cambiar propietario con generar_acta=True, debe generar acta"""
        user = self._login_superuser(client)
        dispositivo = DispositivoFactory()
        nuevo_colaborador = ColaboradorFactory()
        estado = EstadoDispositivoFactory(nombre="Disponible")
        
        url = reverse('dispositivos:dispositivo_update', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'numero_serie': dispositivo.numero_serie,
            'tipo': dispositivo.modelo.tipo_dispositivo.pk,
            'estado': estado.pk,
            'modelo': dispositivo.modelo.pk,
            'centro_costo': dispositivo.centro_costo.pk,
            'fabricante': dispositivo.modelo.fabricante.pk,
            'propietario_actual': nuevo_colaborador.pk,
            'notas_condicion': dispositivo.notas_condicion,
            'valor_contable': dispositivo.valor_contable,
            'generar_acta': 'on',
        })
        
        assert response.status_code == 200
        from actas.models import Acta
        assert Acta.objects.filter(colaborador=nuevo_colaborador).exists()
        acta = Acta.objects.filter(colaborador=nuevo_colaborador).first()
        assert acta.tipo_acta == 'ENTREGA'
        
        assert response.context['show_acta_modal'] is True
        assert response.context['acta'] == acta
        assert response.context['d'].pk == dispositivo.pk

    def test_update_dispositivo_sin_cambio_propietario_no_genera_acta(self, client):
        """Al editar sin cambiar propietario, no debe generar acta"""
        user = self._login_superuser(client)
        dispositivo = DispositivoFactory()
        
        url = reverse('dispositivos:dispositivo_update', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'numero_serie': dispositivo.numero_serie,
            'tipo': dispositivo.modelo.tipo_dispositivo.pk,
            'estado': dispositivo.estado.pk,
            'modelo': dispositivo.modelo.pk,
            'centro_costo': dispositivo.centro_costo.pk,
            'fabricante': dispositivo.modelo.fabricante.pk,
            'propietario_actual': dispositivo.propietario_actual.pk if dispositivo.propietario_actual else '',
            'notas_condicion': dispositivo.notas_condicion,
            'valor_contable': dispositivo.valor_contable,
            'generar_acta': 'on',
        })
        
        assert response.status_code == 302
        from actas.models import Acta
        assert Acta.objects.count() == 0
