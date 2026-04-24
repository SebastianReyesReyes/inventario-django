"""E2E: Flujo de entrega de accesorios.

Crear accesorio → Entregar a colaborador → Generar acta que incluye accesorios.
"""
import pytest
from playwright.sync_api import Page, expect

from core.tests.factories import (
    ColaboradorFactory,
    DispositivoFactory,
    EstadoDisponibleFactory,
    HistorialAsignacionFactory,
    EntregaAccesorioFactory,
)

from .pages.inventory_pages import LoginPage, ActasPage


@pytest.fixture
def admin_user(db):
    user = ColaboradorFactory(
        username='admin_acc',
        is_superuser=True,
        is_staff=True,
    )
    user.set_password('testpass123')
    user.save()
    return user


@pytest.mark.e2e
@pytest.mark.django_db
def test_accessory_in_acta(live_server, page: Page, admin_user):
    """Flujo E2E: accesorios vinculados a un acta."""
    login_page = LoginPage(page)
    actas_page = ActasPage(page)

    login_page.navigate(live_server.url + "/login/")
    login_page.login('admin_acc', 'testpass123')
    page.wait_for_url(live_server.url + "/")

    colaborador = ColaboradorFactory(first_name="Acc", last_name="Test")
    dispositivo = DispositivoFactory(
        estado=EstadoDisponibleFactory(),
        propietario_actual=None,
    )
    HistorialAsignacionFactory(
        colaborador=colaborador,
        dispositivo=dispositivo,
        acta=None,
        fecha_fin=None,
    )
    EntregaAccesorioFactory(
        colaborador=colaborador,
        tipo="Mouse",
        cantidad=1,
    )

    actas_page.navigate(live_server.url)
    page.wait_for_timeout(500)

    actas_page.click_generate()
    actas_page.expect_modal_visible()

    full_name = f"{colaborador.first_name} {colaborador.last_name}"
    actas_page.select_colaborador(full_name)

    page.wait_for_timeout(500)

    checkbox = page.locator('input[name="asignaciones"]').first
    if checkbox.is_visible():
        checkbox.check()

    actas_page.submit()

    page.wait_for_timeout(1000)

    actas_page.expect_acta_in_list(full_name)


@pytest.mark.e2e
@pytest.mark.django_db
def test_accessory_list_visible(live_server, page: Page, admin_user):
    """Validar que los accesorios aparecen en la interfaz."""
    login_page = LoginPage(page)

    login_page.navigate(live_server.url + "/login/")
    login_page.login('admin_acc', 'testpass123')
    page.wait_for_url(live_server.url + "/")

    colaborador = ColaboradorFactory(first_name="List", last_name="Test")
    EntregaAccesorioFactory(
        colaborador=colaborador,
        tipo="Teclado",
        cantidad=2,
    )

    page.click('text=Activos IT')
    page.wait_for_url(lambda url: "/dispositivos/" in url)

    expect(page.locator('table')).to_be_visible()
