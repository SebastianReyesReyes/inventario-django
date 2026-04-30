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

    def test_acta_crear_post_success_returns_sideover_preview(self, client):
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')

        colaborador = ColaboradorFactory()
        asignacion = HistorialAsignacionFactory(colaborador=colaborador, acta=None)

        url = reverse('actas:acta_create')
        response = client.post(
            url,
            {
                'colaborador': colaborador.pk,
                'tipo_acta': 'ENTREGA',
                'observaciones': 'Entrega inicial',
                'asignaciones': [asignacion.pk],
            },
            HTTP_HX_REQUEST='true'
        )

        assert response.status_code == 200
        assert response['HX-Retarget'] == '#side-over-container'
        assert 'actaCreated' in response['HX-Trigger']
        assert 'modal-close' in response['HX-Trigger']
        # Debe contener el side-over con el detalle del acta
        from actas.models import Acta
        acta = Acta.objects.first()
        assert acta.folio in response.content.decode('utf-8')
        assert 'Descargar PDF' in response.content.decode('utf-8')

    def test_acta_crear_post_validation_error_returns_oob_block(self, client):
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')

        colaborador = ColaboradorFactory()

        url = reverse('actas:acta_create')
        response = client.post(
            url,
            {
                'colaborador': colaborador.pk,
                'tipo_acta': 'ENTREGA',
                'observaciones': 'Sin asignaciones',
            },
            HTTP_HX_REQUEST='true'
        )

        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert 'id="acta-errors"' in html
        assert 'hx-swap-oob="true"' in html

    def test_acta_firmar_post_success_returns_trigger(self, client):
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')

        acta = ActaFactory(firmada=False)
        url = reverse('actas:acta_firmar', kwargs={'pk': acta.pk})
        response = client.post(url, HTTP_HX_REQUEST='true')

        assert response.status_code == 200
        assert response['HX-Trigger'] == 'actaFirmada'
        assert 'Acta Firmada' in response.content.decode('utf-8')

    def test_acta_firmar_post_already_firmada_returns_success(self, client):
        """Si ya está firmada, no es error, devuelve el botón firmado igual."""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')

        acta = ActaFactory(firmada=True)
        url = reverse('actas:acta_firmar', kwargs={'pk': acta.pk})
        response = client.post(url, HTTP_HX_REQUEST='true')

        assert response.status_code == 200
        assert 'Acta Firmada' in response.content.decode('utf-8')

    def test_acta_pdf_generates_pdf_content(self, client):
        """Verificar que la vista de PDF retorna contenido binario PDF."""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')

        acta = ActaFactory()
        HistorialAsignacionFactory(acta=acta)

        url = reverse('actas:acta_pdf', kwargs={'pk': acta.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert response.content.startswith(b'%PDF')

    def test_ministros_por_colaborador_returns_options_html(self, client):
        """Verificar que retorna opciones HTML para el select de ministro."""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')

        colaborador = ColaboradorFactory(cargo='Administrador de Obra')
        url = reverse('actas:acta_ministros_por_colaborador', kwargs={'colaborador_pk': colaborador.pk})
        response = client.get(url)

        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert '<option' in html
        assert colaborador.nombre_completo in html

    def test_acta_list_sort_by_folio_asc(self, client):
        """Verificar ordenamiento ascendente por folio"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        
        from actas.models import Acta
        Acta.objects.create(colaborador=ColaboradorFactory(), tipo_acta='ENTREGA', folio='ACT-002')
        Acta.objects.create(colaborador=ColaboradorFactory(), tipo_acta='ENTREGA', folio='ACT-001')
        
        url = reverse('actas:acta_list')
        response = client.get(url, {'sort': 'folio', 'order': 'asc'})
        assert response.status_code == 200
        folios = [a.folio for a in response.context['page_obj']]
        assert folios.index('ACT-001') < folios.index('ACT-002')

    def test_acta_list_sort_by_folio_desc(self, client):
        """Verificar ordenamiento descendente por folio"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        
        from actas.models import Acta
        Acta.objects.create(colaborador=ColaboradorFactory(), tipo_acta='ENTREGA', folio='ACT-001')
        Acta.objects.create(colaborador=ColaboradorFactory(), tipo_acta='ENTREGA', folio='ACT-002')
        
        url = reverse('actas:acta_list')
        response = client.get(url, {'sort': 'folio', 'order': 'desc'})
        assert response.status_code == 200
        folios = [a.folio for a in response.context['page_obj']]
        assert folios.index('ACT-002') < folios.index('ACT-001')

    def test_acta_list_sort_by_colaborador(self, client):
        """Verificar ordenamiento por nombre de colaborador"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        
        from actas.models import Acta
        c1 = ColaboradorFactory(first_name='Ana')
        c2 = ColaboradorFactory(first_name='Carlos')
        Acta.objects.create(colaborador=c1, tipo_acta='ENTREGA', folio='ACT-001')
        Acta.objects.create(colaborador=c2, tipo_acta='ENTREGA', folio='ACT-002')
        
        url = reverse('actas:acta_list')
        response = client.get(url, {'sort': 'colaborador', 'order': 'asc'})
        assert response.status_code == 200
        nombres = [a.colaborador.first_name for a in response.context['page_obj']]
        assert nombres.index('Ana') < nombres.index('Carlos')

    def test_acta_list_sort_preserves_search(self, client):
        """Verificar que el ordenamiento respeta el filtro de búsqueda"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        
        from actas.models import Acta
        c = ColaboradorFactory(first_name='Juan')
        Acta.objects.create(colaborador=c, tipo_acta='ENTREGA', folio='ACT-JUAN-001')
        Acta.objects.create(colaborador=ColaboradorFactory(first_name='Pedro'), tipo_acta='ENTREGA', folio='ACT-PEDRO-001')
        
        url = reverse('actas:acta_list')
        response = client.get(url, {'q': 'Juan', 'sort': 'folio', 'order': 'asc'})
        assert response.status_code == 200
        folios = [a.folio for a in response.context['page_obj']]
        assert 'ACT-JUAN-001' in folios
        assert 'ACT-PEDRO-001' not in folios

    def test_acta_list_has_paginator_visual(self, client):
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        for i in range(15):
            ActaFactory()
        url = reverse('actas:acta_list')
        response = client.get(url)
        assert response.status_code == 200
        assert 'page_obj' in response.context
        assert response.context['page_obj'].paginator.per_page == 10
        html = response.content.decode('utf-8')
        assert '<c-paginator' in html or 'Página 1 de' in html

    def test_acta_preview_post_success_returns_sideover(self, client):
        """Verificar que preview retorna side-over HTML con el acta renderizado"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')

        colaborador = ColaboradorFactory()
        asignacion = HistorialAsignacionFactory(colaborador=colaborador, acta=None)

        url = reverse('actas:acta_preview')
        response = client.post(
            url,
            {
                'colaborador': colaborador.pk,
                'tipo_acta': 'ENTREGA',
                'observaciones': 'Preview test',
                'asignaciones': [asignacion.pk],
            },
            HTTP_HX_REQUEST='true'
        )

        assert response.status_code == 200
        html = response.content.decode('utf-8')
        # Debe contener el side-over
        assert 'Vista Previa del Acta' in html
        assert 'Documento Preliminar' in html
        # Debe contener datos del colaborador y equipo
        assert colaborador.nombre_completo in html
        assert str(asignacion.dispositivo.numero_serie) in html
        # No debe crear acta en BD
        from actas.models import Acta
        assert Acta.objects.count() == 0

    def test_acta_preview_post_sin_asignaciones_returns_oob_error(self, client):
        """Verificar que preview sin asignaciones retorna error OOB"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')

        colaborador = ColaboradorFactory()

        url = reverse('actas:acta_preview')
        response = client.post(
            url,
            {
                'colaborador': colaborador.pk,
                'tipo_acta': 'ENTREGA',
                'observaciones': 'Sin equipos',
            },
            HTTP_HX_REQUEST='true'
        )

        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert 'id="acta-errors"' in html
        assert 'hx-swap-oob="true"' in html

    def test_acta_preview_post_form_invalid_returns_oob_error(self, client):
        """Verificar que preview con form inválido retorna error OOB"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')

        url = reverse('actas:acta_preview')
        response = client.post(
            url,
            {
                'tipo_acta': 'ENTREGA',
                # Falta colaborador (campo requerido)
            },
            HTTP_HX_REQUEST='true'
        )

        assert response.status_code == 200
        html = response.content.decode('utf-8')
        assert 'id="acta-errors"' in html
        assert 'hx-swap-oob="true"' in html

    def test_acta_preview_requires_login(self, client):
        """Verificar que preview requiere autenticación"""
        url = reverse('actas:acta_preview')
        response = client.post(url)
        assert response.status_code == 302  # Redirect a login

    def test_acta_preview_requires_permission(self, client):
        """Verificar que preview requiere permiso add_acta"""
        user = ColaboradorFactory(is_staff=False, is_superuser=False)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')

        url = reverse('actas:acta_preview')
        response = client.post(url)
        assert response.status_code == 403
