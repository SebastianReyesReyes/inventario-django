"""
Regression tests for all 17 refactored view functions.

These tests verify that the views extracted from the monolithic dispositivos/views.py
into 6 modules (crud, trazabilidad, ajax, mantenimiento, accesorios, qr) preserve
the same behavior as the original implementation.

Modules tested:
  - crud.py:          dispositivo_create, dispositivo_list, dispositivo_detail,
                      dispositivo_update, dispositivo_delete
  - trazabilidad.py:  dispositivo_asignar, dispositivo_reasignar,
                      dispositivo_devolver, dispositivo_historial
  - ajax.py:          ajax_get_modelos, ajax_crear_modelo, ajax_get_tech_fields
  - mantenimiento.py:  mantenimiento_create, mantenimiento_update
  - accesorios.py:    colaborador_entrega_accesorio, colaborador_historial_accesorios
  - qr.py:            dispositivo_qr
"""

import pytest
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from core.tests.factories import (
    ColaboradorFactory,
    DispositivoFactory,
    EstadoDispositivoFactory,
    EstadoDisponibleFactory,
    EstadoAsignadoFactory,
    HistorialAsignacionFactory,
    TipoDispositivoFactory,
    FabricanteFactory,
    ModeloFactory,
    CentroCostoFactory,
    EntregaAccesorioFactory,
)
from dispositivos.models import Dispositivo, HistorialAsignacion, BitacoraMantenimiento, EntregaAccesorio
from core.models import Modelo, TipoDispositivo, Fabricante


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login_superuser(client):
    """Create a superuser and log in; return the user."""
    user = ColaboradorFactory(username='admin_regression', is_staff=True, is_superuser=True)
    user.set_password('password')
    user.save()
    client.login(username='admin_regression', password='password')
    return user


def _add_perm(user, codename, model):
    """Add a single permission to a user by codename and model class."""
    ct = ContentType.objects.get_for_model(model)
    perm = Permission.objects.get(codename=codename, content_type=ct)
    user.user_permissions.add(perm)


# ===========================================================================
# CRUD views (crud.py) — 5 views
# ===========================================================================

@pytest.mark.django_db
class TestDispositivoCreate:
    """Regression tests for dispositivo_create (crud.py)."""

    def test_create_get_renders_form(self, client):
        """GET request renders the creation form with tech_forms context."""
        user = _login_superuser(client)
        url = reverse('dispositivos:dispositivo_create')
        response = client.get(url)
        assert response.status_code == 200
        assert 'form' in response.context
        assert 'tech_forms' in response.context
        assert 'titulo' in response.context
        assert response.context['titulo'] == 'Registrar Nuevo Equipo'

    def test_create_post_valid_data_creates_dispositivo(self, client):
        """POST with valid data creates a new Dispositivo and redirects."""
        user = _login_superuser(client)
        tipo = TipoDispositivoFactory(nombre="Impresora")
        estado = EstadoDispositivoFactory(nombre="Disponible")
        fabricante = FabricanteFactory()
        modelo = ModeloFactory(fabricante=fabricante, tipo_dispositivo=tipo)
        cc = CentroCostoFactory()

        url = reverse('dispositivos:dispositivo_create')
        response = client.post(url, {
            'numero_serie': 'SN-REG-001',
            'tipo': tipo.pk,
            'estado': estado.pk,
            'modelo': modelo.pk,
            'centro_costo': cc.pk,
            'fabricante': fabricante.pk,
            'notas_condicion': 'Nuevo',
            'valor_contable': 500000,
        })
        # Without generar_acta, should redirect to detail
        assert response.status_code == 302
        assert Dispositivo.objects.filter(numero_serie='SN-REG-001').exists()

    def test_create_post_with_acta_generates_acta(self, client):
        """POST with generar_acta creates Dispositivo AND Acta, renders detail with modal."""
        user = _login_superuser(client)
        colaborador = ColaboradorFactory()
        tipo = TipoDispositivoFactory(nombre="Impresora")
        estado = EstadoDisponibleFactory()
        fabricante = FabricanteFactory()
        modelo = ModeloFactory(fabricante=fabricante, tipo_dispositivo=tipo)
        cc = CentroCostoFactory()

        url = reverse('dispositivos:dispositivo_create')
        response = client.post(url, {
            'numero_serie': 'SN-ACTA-001',
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
        assert response.context['show_acta_modal'] is True
        from actas.models import Acta
        assert Acta.objects.filter(colaborador=colaborador).exists()

    def test_create_requires_permission(self, client):
        """Unprivileged user gets 403 on dispositivo_create."""
        user = ColaboradorFactory(username='noperm_create')
        user.set_password('password')
        user.save()
        client.login(username='noperm_create', password='password')
        url = reverse('dispositivos:dispositivo_create')
        response = client.get(url)
        assert response.status_code == 403

    def test_create_requires_login(self, client):
        """Unauthenticated user is redirected to login."""
        url = reverse('dispositivos:dispositivo_create')
        response = client.get(url)
        assert response.status_code == 302
        assert '/login' in response.url


@pytest.mark.django_db
class TestDispositivoList:
    """Regression tests for dispositivo_list (crud.py)."""

    def test_list_returns_200(self, client):
        """Authenticated user can access the list view."""
        user = _login_superuser(client)
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_list_htmx_returns_partial(self, client):
        """HTMX request returns the table partial, not the full page."""
        user = _login_superuser(client)
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/dispositivo_list_table.html' in templates

    def test_list_htmx_modal_returns_sideover(self, client):
        """HTMX request with _modal=true returns the sideover partial."""
        user = _login_superuser(client)
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'_modal': 'true'}, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/dispositivo_sideover_list.html' in templates

    def test_list_search_filters_by_query(self, client):
        """Query parameter 'q' filters dispositivos by identificador, serie, modelo."""
        user = _login_superuser(client)
        d1 = DispositivoFactory(numero_serie="FINDME-001")
        d2 = DispositivoFactory(numero_serie="OTHER-002")
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'q': 'FINDME'})
        assert response.status_code == 200
        ids = [d.pk for d in response.context['dispositivos']]
        assert d1.pk in ids
        assert d2.pk not in ids

    def test_list_sort_by_estado(self, client):
        """Sort by estado works correctly."""
        user = _login_superuser(client)
        est1 = EstadoDispositivoFactory(nombre="Asignado")
        est2 = EstadoDispositivoFactory(nombre="Disponible")
        DispositivoFactory(estado=est1)
        DispositivoFactory(estado=est2)
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'sort': 'estado', 'order': 'asc'})
        assert response.status_code == 200
        estados = [d.estado.nombre for d in response.context['dispositivos']]
        assert estados.index("Asignado") < estados.index("Disponible")

    def test_list_pagination(self, client):
        """Pagination works with per_page=20."""
        user = _login_superuser(client)
        for i in range(25):
            DispositivoFactory()
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url)
        assert response.status_code == 200
        assert 'page_obj' in response.context
        assert response.context['page_obj'].paginator.per_page == 20

    def test_list_alerta_mantenimiento(self, client):
        """Alerta=mantenimiento filters by estado 'Reparación'."""
        user = _login_superuser(client)
        estado_rep = EstadoDispositivoFactory(nombre="En Reparación")
        estado_disp = EstadoDisponibleFactory()
        d_rep = DispositivoFactory(estado=estado_rep)
        d_disp = DispositivoFactory(estado=estado_disp)
        url = reverse('dispositivos:dispositivo_list')
        response = client.get(url, {'alerta': 'mantenimiento'})
        assert response.status_code == 200
        ids = [d.pk for d in response.context['dispositivos']]
        assert d_rep.pk in ids
        assert d_disp.pk not in ids


@pytest.mark.django_db
class TestDispositivoDetail:
    """Regression tests for dispositivo_detail (crud.py)."""

    def test_detail_returns_200(self, client):
        """Authenticated user can view dispositivo detail."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:dispositivo_detail', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['d'].pk == dispositivo.pk

    def test_detail_htmx_returns_sideover(self, client):
        """HTMX request returns the sideover partial."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:dispositivo_detail', kwargs={'pk': dispositivo.pk})
        response = client.get(url, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/dispositivo_detail_sideover.html' in templates

    def test_detail_404_for_nonexistent(self, client):
        """Nonexistent pk returns 404."""
        user = _login_superuser(client)
        url = reverse('dispositivos:dispositivo_detail', kwargs={'pk': 99999})
        response = client.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestDispositivoUpdate:
    """Regression tests for dispositivo_update (crud.py)."""

    def test_update_get_renders_form(self, client):
        """GET request renders the update form with existing data."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:dispositivo_update', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert 'form' in response.context
        assert 'tech_forms' in response.context
        assert dispositivo.identificador_interno in response.context['titulo']

    def test_update_post_valid_data(self, client):
        """POST with valid data updates the dispositivo."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        estado = EstadoDispositivoFactory(nombre="Disponible")
        url = reverse('dispositivos:dispositivo_update', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'numero_serie': dispositivo.numero_serie,
            'tipo': dispositivo.modelo.tipo_dispositivo.pk,
            'estado': estado.pk,
            'modelo': dispositivo.modelo.pk,
            'centro_costo': dispositivo.centro_costo.pk,
            'fabricante': dispositivo.modelo.fabricante.pk,
            'notas_condicion': 'Actualizado',
            'valor_contable': 600000,
        })
        # Without generar_acta and no owner change, should redirect
        assert response.status_code == 302
        dispositivo.refresh_from_db()
        assert dispositivo.notas_condicion == 'Actualizado'

    def test_update_with_acta_renders_modal(self, client):
        """POST with owner change + generar_acta renders detail with acta modal."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        nuevo_colaborador = ColaboradorFactory()
        estado = EstadoDisponibleFactory()
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
        assert response.context['show_acta_modal'] is True

    def test_update_requires_permission(self, client):
        """Unprivileged user gets 403 on dispositivo_update."""
        user = ColaboradorFactory(username='noperm_update')
        user.set_password('password')
        user.save()
        client.login(username='noperm_update', password='password')
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:dispositivo_update', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 403


@pytest.mark.django_db
class TestDispositivoDelete:
    """Regression tests for dispositivo_delete (crud.py)."""

    def test_delete_get_renders_confirm(self, client):
        """GET request renders the confirmation modal."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:dispositivo_delete', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/dispositivo_confirm_delete.html' in templates

    def test_delete_post_htmx_returns_204_with_redirect(self, client):
        """POST via HTMX deletes and returns 204 with HX-Redirect."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        pk = dispositivo.pk
        url = reverse('dispositivos:dispositivo_delete', kwargs={'pk': pk})
        response = client.post(url, HTTP_HX_REQUEST='true')
        assert response.status_code == 204
        assert response['HX-Redirect'] == reverse('dispositivos:dispositivo_list')
        assert not Dispositivo.objects.filter(pk=pk).exists()

    def test_delete_post_non_htmx_redirects(self, client):
        """POST without HTMX deletes and redirects to list."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        pk = dispositivo.pk
        url = reverse('dispositivos:dispositivo_delete', kwargs={'pk': pk})
        response = client.post(url)
        assert response.status_code == 302
        assert response.url == reverse('dispositivos:dispositivo_list')
        assert not Dispositivo.objects.filter(pk=pk).exists()

    def test_delete_cascades_historial(self, client):
        """Deleting a dispositivo cascades to related HistorialAsignacion (CASCADE FK)."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        historial = HistorialAsignacionFactory(dispositivo=dispositivo)
        pk = dispositivo.pk
        url = reverse('dispositivos:dispositivo_delete', kwargs={'pk': pk})
        response = client.post(url, HTTP_HX_REQUEST='true')
        # CASCADE delete: dispositivo and historial both deleted
        assert response.status_code == 204
        assert not Dispositivo.objects.filter(pk=pk).exists()
        assert not HistorialAsignacion.objects.filter(pk=historial.pk).exists()

    def test_delete_requires_permission(self, client):
        """Unprivileged user gets 403 on dispositivo_delete."""
        user = ColaboradorFactory(username='noperm_delete')
        user.set_password('password')
        user.save()
        client.login(username='noperm_delete', password='password')
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:dispositivo_delete', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 403


# ===========================================================================
# Trazabilidad views (trazabilidad.py) — 4 views
# ===========================================================================

@pytest.mark.django_db
class TestDispositivoAsignar:
    """Regression tests for dispositivo_asignar (trazabilidad.py)."""

    def test_asignar_get_renders_modal(self, client):
        """GET renders the asignacion form modal."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoDisponibleFactory())
        url = reverse('dispositivos:dispositivo_asignar', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/asignacion_form_modal.html' in templates

    def test_asignar_post_htmx_success(self, client):
        """POST via HTMX assigns dispositivo and returns success partial."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoDisponibleFactory(), propietario_actual=None)
        colaborador = ColaboradorFactory()
        url = reverse('dispositivos:dispositivo_asignar', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'colaborador': colaborador.pk,
            'condicion_fisica': 'Buen estado',
            'generar_acta': '',
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert response['HX-Trigger'] == 'asignacion-saved'
        dispositivo.refresh_from_db()
        assert dispositivo.propietario_actual == colaborador

    def test_asignar_post_non_htmx_redirects(self, client):
        """POST without HTMX redirects to detail."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoDisponibleFactory(), propietario_actual=None)
        colaborador = ColaboradorFactory()
        url = reverse('dispositivos:dispositivo_asignar', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'colaborador': colaborador.pk,
            'condicion_fisica': 'Buen estado',
            'generar_acta': '',
        })
        assert response.status_code == 302
        assert response.url == reverse('dispositivos:dispositivo_detail', kwargs={'pk': dispositivo.pk})

    def test_asignar_requires_permission(self, client):
        """Unprivileged user gets 403."""
        user = ColaboradorFactory(username='noperm_asignar')
        user.set_password('password')
        user.save()
        client.login(username='noperm_asignar', password='password')
        dispositivo = DispositivoFactory(estado=EstadoDisponibleFactory())
        url = reverse('dispositivos:dispositivo_asignar', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 403


@pytest.mark.django_db
class TestDispositivoReasignar:
    """Regression tests for dispositivo_reasignar (trazabilidad.py)."""

    def test_reasignar_get_renders_modal(self, client):
        """GET renders the reasignacion form modal."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory())
        HistorialAsignacionFactory(dispositivo=dispositivo, fecha_fin=None)
        url = reverse('dispositivos:dispositivo_reasignar', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/reasignacion_form_modal.html' in templates

    def test_reasignar_post_htmx_closes_previous(self, client):
        """POST via HTMX reassigns and closes previous assignment."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory())
        anterior = ColaboradorFactory()
        nuevo = ColaboradorFactory()
        hist = HistorialAsignacionFactory(dispositivo=dispositivo, colaborador=anterior, fecha_fin=None)
        url = reverse('dispositivos:dispositivo_reasignar', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'colaborador': nuevo.pk,
            'condicion_fisica': 'Con rayones leves',
            'generar_acta': '',
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert response['HX-Trigger'] == 'asignacion-saved'
        hist.refresh_from_db()
        assert hist.fecha_fin is not None
        dispositivo.refresh_from_db()
        assert dispositivo.propietario_actual == nuevo


@pytest.mark.django_db
class TestDispositivoDevolver:
    """Regression tests for dispositivo_devolver (trazabilidad.py)."""

    def test_devolver_get_renders_modal(self, client):
        """GET renders the devolucion form modal."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory())
        HistorialAsignacionFactory(dispositivo=dispositivo, fecha_fin=None)
        url = reverse('dispositivos:dispositivo_devolver', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/devolucion_form_modal.html' in templates

    def test_devolver_post_htmx_buen_estado(self, client):
        """POST with estado_llegada=bueno returns dispositivo to Disponible."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory())
        colaborador = ColaboradorFactory()
        HistorialAsignacionFactory(dispositivo=dispositivo, colaborador=colaborador, fecha_fin=None)
        url = reverse('dispositivos:dispositivo_devolver', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'condicion_fisica': 'Perfecto estado',
            'estado_llegada': 'bueno',
            'generar_acta': '',
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert response['HX-Trigger'] == 'asignacion-saved'
        dispositivo.refresh_from_db()
        assert dispositivo.estado.nombre == 'Disponible'
        assert dispositivo.propietario_actual is None

    def test_devolver_post_htmx_danado(self, client):
        """POST with estado_llegada=danado sets estado to En Reparación."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory(estado=EstadoAsignadoFactory())
        colaborador = ColaboradorFactory()
        HistorialAsignacionFactory(dispositivo=dispositivo, colaborador=colaborador, fecha_fin=None)
        url = reverse('dispositivos:dispositivo_devolver', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'condicion_fisica': 'Pantalla rota',
            'estado_llegada': 'danado',
            'generar_acta': '',
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        dispositivo.refresh_from_db()
        assert dispositivo.estado.nombre == 'En Reparación'
        assert dispositivo.propietario_actual is None


@pytest.mark.django_db
class TestDispositivoHistorial:
    """Regression tests for dispositivo_historial (trazabilidad.py)."""

    def test_historial_returns_timeline(self, client):
        """GET returns historial timeline partial with assignments."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        HistorialAsignacionFactory(dispositivo=dispositivo)
        HistorialAsignacionFactory(dispositivo=dispositivo)
        url = reverse('dispositivos:dispositivo_historial', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/historial_timeline.html' in templates
        assert response.context['historial'].count() == 2

    def test_historial_404_for_nonexistent(self, client):
        """Nonexistent dispositivo pk returns 404."""
        user = _login_superuser(client)
        url = reverse('dispositivos:dispositivo_historial', kwargs={'pk': 99999})
        response = client.get(url)
        assert response.status_code == 404


# ===========================================================================
# AJAX views (ajax.py) — 3 views
# ===========================================================================

@pytest.mark.django_db
class TestAjaxGetModelos:
    """Regression tests for ajax_get_modelos (ajax.py)."""

    def test_get_modelos_with_fabricante(self, client):
        """Returns modelos filtered by fabricante."""
        user = _login_superuser(client)
        fabricante = FabricanteFactory()
        tipo = TipoDispositivoFactory()
        modelo = ModeloFactory(fabricante=fabricante, tipo_dispositivo=tipo)
        url = reverse('dispositivos:ajax_get_modelos')
        response = client.get(url, {'fabricante': fabricante.pk})
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/modelo_options.html' in templates

    def test_get_modelos_with_tipo(self, client):
        """Returns modelos filtered by tipo."""
        user = _login_superuser(client)
        tipo = TipoDispositivoFactory()
        fabricante = FabricanteFactory()
        modelo = ModeloFactory(fabricante=fabricante, tipo_dispositivo=tipo)
        url = reverse('dispositivos:ajax_get_modelos')
        response = client.get(url, {'tipo': tipo.pk})
        assert response.status_code == 200

    def test_get_modelos_no_params_returns_empty(self, client):
        """Without fabricante or tipo, returns empty queryset."""
        user = _login_superuser(client)
        url = reverse('dispositivos:ajax_get_modelos')
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['modelos'].count() == 0

    def test_get_modelos_does_not_require_login(self, client):
        """ajax_get_modelos has no login_required decorator."""
        # This view does NOT have @login_required
        url = reverse('dispositivos:ajax_get_modelos')
        response = client.get(url)
        # Should not redirect to login
        assert response.status_code == 200


@pytest.mark.django_db
class TestAjaxCrearModelo:
    """Regression tests for ajax_crear_modelo (ajax.py)."""

    def test_crear_modelo_post_creates_new(self, client):
        """POST creates a new Modelo and returns updated options."""
        user = _login_superuser(client)
        fabricante = FabricanteFactory()
        tipo = TipoDispositivoFactory()
        url = reverse('dispositivos:ajax_crear_modelo')
        response = client.post(url, {
            'fabricante': fabricante.pk,
            'tipo': tipo.pk,
            'nuevo_modelo_nombre': 'Modelo Test Nuevo',
        })
        assert response.status_code == 200
        assert Modelo.objects.filter(nombre='Modelo Test Nuevo').exists()
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/modelo_options.html' in templates

    def test_crear_modelo_post_missing_params(self, client):
        """POST with missing params returns options without creating."""
        user = _login_superuser(client)
        url = reverse('dispositivos:ajax_crear_modelo')
        response = client.post(url, {
            'nuevo_modelo_nombre': 'Orphan Model',
        })
        assert response.status_code == 200
        assert not Modelo.objects.filter(nombre='Orphan Model').exists()

    def test_crear_modelo_duplicate_case_insensitive(self, client):
        """Creating a model with same name (different case) returns existing."""
        user = _login_superuser(client)
        fabricante = FabricanteFactory()
        tipo = TipoDispositivoFactory()
        ModeloFactory(nombre='Existing Model', fabricante=fabricante, tipo_dispositivo=tipo)
        url = reverse('dispositivos:ajax_crear_modelo')
        response = client.post(url, {
            'fabricante': fabricante.pk,
            'tipo': tipo.pk,
            'nuevo_modelo_nombre': 'existing model',  # lowercase
        })
        assert response.status_code == 200
        # Should not create a duplicate
        assert Modelo.objects.filter(fabricante=fabricante, tipo_dispositivo=tipo, nombre__iexact='existing model').count() == 1


@pytest.mark.django_db
class TestAjaxGetTechFields:
    """Regression tests for ajax_get_tech_fields (ajax.py)."""

    def test_get_tech_fields_notebook(self, client):
        """Returns NotebookTechForm for notebook type."""
        user = _login_superuser(client)
        tipo = TipoDispositivoFactory(nombre="Notebook")
        url = reverse('dispositivos:ajax_get_tipo_fields')
        response = client.get(url, {'tipo': tipo.pk})
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/tipo_especifico_fields.html' in templates

    def test_get_tech_fields_smartphone(self, client):
        """Returns SmartphoneTechForm for smartphone type."""
        user = _login_superuser(client)
        tipo = TipoDispositivoFactory(nombre="Smartphone")
        url = reverse('dispositivos:ajax_get_tipo_fields')
        response = client.get(url, {'tipo': tipo.pk})
        assert response.status_code == 200

    def test_get_tech_fields_monitor(self, client):
        """Returns MonitorTechForm for monitor type."""
        user = _login_superuser(client)
        tipo = TipoDispositivoFactory(nombre="Monitor")
        url = reverse('dispositivos:ajax_get_tipo_fields')
        response = client.get(url, {'tipo': tipo.pk})
        assert response.status_code == 200

    def test_get_tech_fields_unknown_type(self, client):
        """Unknown type returns empty response."""
        user = _login_superuser(client)
        tipo = TipoDispositivoFactory(nombre="Impresora")
        url = reverse('dispositivos:ajax_get_tipo_fields')
        response = client.get(url, {'tipo': tipo.pk})
        assert response.status_code == 200
        # Should return empty HttpResponse
        assert response.content == b''

    def test_get_tech_fields_no_tipo_param(self, client):
        """Missing tipo parameter returns empty response."""
        user = _login_superuser(client)
        url = reverse('dispositivos:ajax_get_tipo_fields')
        response = client.get(url)
        assert response.status_code == 200
        assert response.content == b''

    def test_get_tech_fields_requires_login(self, client):
        """Unauthenticated user is redirected to login."""
        url = reverse('dispositivos:ajax_get_tipo_fields')
        response = client.get(url)
        assert response.status_code == 302
        assert '/login' in response.url


# ===========================================================================
# Mantenimiento views (mantenimiento.py) — 2 views
# ===========================================================================

@pytest.mark.django_db
class TestMantenimientoCreate:
    """Regression tests for mantenimiento_create (mantenimiento.py)."""

    def test_mantenimiento_create_get_renders_modal(self, client):
        """GET renders the mantenimiento form modal."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:mantenimiento_create', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/mantenimiento_form_modal.html' in templates
        assert 'dispositivo' in response.context

    def test_mantenimiento_create_post_valid(self, client):
        """POST creates a BitacoraMantenimiento entry."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:mantenimiento_create', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'falla_reportada': 'Pantalla no enciende',
            'reparacion_realizada': 'Reemplazo de pantalla',
            'costo_reparacion': 50000,
            'cambio_estado_automatico': False,
        })
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/mantenimiento_success.html' in templates
        assert BitacoraMantenimiento.objects.filter(dispositivo=dispositivo).exists()

    def test_mantenimiento_create_with_cambio_estado(self, client):
        """POST with cambio_estado_automatico changes dispositivo estado to Disponible."""
        user = _login_superuser(client)
        estado_reparacion = EstadoDispositivoFactory(nombre="En Reparación")
        dispositivo = DispositivoFactory(estado=estado_reparacion)
        url = reverse('dispositivos:mantenimiento_create', kwargs={'pk': dispositivo.pk})
        response = client.post(url, {
            'falla_reportada': 'Pantalla rota',
            'reparacion_realizada': 'Pantalla reemplazada',
            'costo_reparacion': 80000,
            'cambio_estado_automatico': True,
        })
        assert response.status_code == 200
        dispositivo.refresh_from_db()
        assert dispositivo.estado.nombre == 'Disponible'

    def test_mantenimiento_create_requires_permission(self, client):
        """Unprivileged user gets 403."""
        user = ColaboradorFactory(username='noperm_manto')
        user.set_password('password')
        user.save()
        client.login(username='noperm_manto', password='password')
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:mantenimiento_create', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 403


@pytest.mark.django_db
class TestMantenimientoUpdate:
    """Regression tests for mantenimiento_update (mantenimiento.py)."""

    def test_mantenimiento_update_get_renders_modal(self, client):
        """GET renders the mantenimiento edit form modal."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        mantenimiento = BitacoraMantenimiento.objects.create(
            dispositivo=dispositivo,
            falla_reportada='Falla original',
            reparacion_realizada='Reparación original',
            costo_reparacion=30000,
        )
        url = reverse('dispositivos:mantenimiento_update', kwargs={'pk': mantenimiento.pk})
        response = client.get(url)
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/mantenimiento_form_modal.html' in templates
        assert response.context['edit_mode'] is True

    def test_mantenimiento_update_post_valid(self, client):
        """POST updates the BitacoraMantenimiento entry."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        mantenimiento = BitacoraMantenimiento.objects.create(
            dispositivo=dispositivo,
            falla_reportada='Falla original',
            reparacion_realizada='Reparación original',
            costo_reparacion=30000,
        )
        url = reverse('dispositivos:mantenimiento_update', kwargs={'pk': mantenimiento.pk})
        response = client.post(url, {
            'falla_reportada': 'Falla actualizada',
            'reparacion_realizada': 'Reparación actualizada',
            'costo_reparacion': 45000,
            'cambio_estado_automatico': False,
        })
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/mantenimiento_success.html' in templates
        mantenimiento.refresh_from_db()
        assert mantenimiento.falla_reportada == 'Falla actualizada'
        assert mantenimiento.costo_reparacion == 45000

    def test_mantenimiento_update_requires_permission(self, client):
        """Unprivileged user gets 403."""
        user = ColaboradorFactory(username='noperm_manto_upd')
        user.set_password('password')
        user.save()
        client.login(username='noperm_manto_upd', password='password')
        dispositivo = DispositivoFactory()
        mantenimiento = BitacoraMantenimiento.objects.create(
            dispositivo=dispositivo,
            falla_reportada='Test',
        )
        url = reverse('dispositivos:mantenimiento_update', kwargs={'pk': mantenimiento.pk})
        response = client.get(url)
        assert response.status_code == 403


# ===========================================================================
# Accesorios views (accesorios.py) — 2 views
# ===========================================================================

@pytest.mark.django_db
class TestColaboradorEntregaAccesorio:
    """Regression tests for colaborador_entrega_accesorio (accesorios.py)."""

    def test_entrega_accesorio_get_renders_modal(self, client):
        """GET renders the accesorio form modal."""
        user = _login_superuser(client)
        colaborador = ColaboradorFactory()
        url = reverse('dispositivos:colaborador_entrega_accesorio', kwargs={'pk': colaborador.pk})
        response = client.get(url)
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/accesorio_form_modal.html' in templates
        assert response.context['colaborador'].pk == colaborador.pk

    def test_entrega_accesorio_post_htmx_success(self, client):
        """POST via HTMX creates EntregaAccesorio and returns success partial."""
        user = _login_superuser(client)
        colaborador = ColaboradorFactory()
        url = reverse('dispositivos:colaborador_entrega_accesorio', kwargs={'pk': colaborador.pk})
        response = client.post(url, {
            'tipo': 'Mouse',
            'cantidad': 2,
            'descripcion': 'Mouse inalámbrico',
        }, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert response['HX-Trigger'] == 'accesorio-saved'
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/accesorio_success.html' in templates
        assert EntregaAccesorio.objects.filter(colaborador=colaborador, tipo='Mouse').exists()

    def test_entrega_accesorio_post_non_htmx_redirects(self, client):
        """POST without HTMX redirects to colaborador detail."""
        user = _login_superuser(client)
        colaborador = ColaboradorFactory()
        url = reverse('dispositivos:colaborador_entrega_accesorio', kwargs={'pk': colaborador.pk})
        response = client.post(url, {
            'tipo': 'Teclado',
            'cantidad': 1,
            'descripcion': 'Teclado mecánico',
        })
        assert response.status_code == 302
        assert response.url == reverse('colaboradores:colaborador_detail', kwargs={'pk': colaborador.pk})

    def test_entrega_accesorio_requires_permission(self, client):
        """Unprivileged user gets 403."""
        user = ColaboradorFactory(username='noperm_accesorio')
        user.set_password('password')
        user.save()
        client.login(username='noperm_accesorio', password='password')
        colaborador = ColaboradorFactory()
        url = reverse('dispositivos:colaborador_entrega_accesorio', kwargs={'pk': colaborador.pk})
        response = client.get(url)
        assert response.status_code == 403


@pytest.mark.django_db
class TestColaboradorHistorialAccesorios:
    """Regression tests for colaborador_historial_accesorios (accesorios.py)."""

    def test_historial_accesorios_returns_list(self, client):
        """GET returns accesorios list partial."""
        user = _login_superuser(client)
        colaborador = ColaboradorFactory()
        EntregaAccesorioFactory(colaborador=colaborador, tipo='Mouse')
        EntregaAccesorioFactory(colaborador=colaborador, tipo='Teclado')
        url = reverse('dispositivos:colaborador_historial_accesorios', kwargs={'pk': colaborador.pk})
        response = client.get(url)
        assert response.status_code == 200
        templates = [t.name for t in response.templates]
        assert 'dispositivos/partials/accesorios_list.html' in templates
        assert response.context['accesorios'].count() == 2

    def test_historial_accesorios_404_for_nonexistent(self, client):
        """Nonexistent colaborador pk returns 404."""
        user = _login_superuser(client)
        url = reverse('dispositivos:colaborador_historial_accesorios', kwargs={'pk': 99999})
        response = client.get(url)
        assert response.status_code == 404


# ===========================================================================
# QR view (qr.py) — 1 view
# ===========================================================================

@pytest.mark.django_db
class TestDispositivoQR:
    """Regression tests for dispositivo_qr (qr.py)."""

    def test_qr_returns_png_image(self, client):
        """GET returns a PNG image response."""
        user = _login_superuser(client)
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:dispositivo_qr', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        assert 'qr_' in response.get('Content-Disposition', '')

    def test_qr_404_for_nonexistent(self, client):
        """Nonexistent dispositivo pk returns 404."""
        user = _login_superuser(client)
        url = reverse('dispositivos:dispositivo_qr', kwargs={'pk': 99999})
        response = client.get(url)
        assert response.status_code == 404

    def test_qr_requires_login(self, client):
        """Unauthenticated user is redirected to login."""
        dispositivo = DispositivoFactory()
        url = reverse('dispositivos:dispositivo_qr', kwargs={'pk': dispositivo.pk})
        response = client.get(url)
        assert response.status_code == 302
        assert '/login' in response.url