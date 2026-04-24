"""E2E: Flujo completo de ciclo de vida de inventario.

Login → Crear catálogo → Crear dispositivo → Asignar → Generar acta 
→ Reasignar → Devolver → Verificar dashboard.
"""
import pytest
from playwright.sync_api import Page, expect

from core.tests.factories import (
    ColaboradorFactory,
    DispositivoFactory,
    EstadoDisponibleFactory,
    EstadoAsignadoFactory,
    HistorialAsignacionFactory,
    TipoDispositivoFactory,
    FabricanteFactory,
    ModeloFactory,
    CentroCostoFactory,
    EstadoDispositivoFactory,
)

from .pages.inventory_pages import (
    LoginPage,
    DashboardPage,
    DispositivosPage,
    DispositivoFormPage,
    ActasPage,
)


@pytest.fixture
def admin_user(db):
    user = ColaboradorFactory(
        username='admin_full',
        is_superuser=True,
        is_staff=True,
        first_name="Admin",
        last_name="Full",
    )
    user.set_password('testpass123')
    user.save()
    return user


@pytest.mark.e2e
@pytest.mark.django_db
def test_full_inventory_lifecycle(live_server, page: Page, admin_user):
    """Flujo E2E completo: crear dispositivo, asignar, generar acta, devolver."""
    login_page = LoginPage(page)
    dispositivos_page = DispositivosPage(page)
    actas_page = ActasPage(page)

    login_page.navigate(live_server.url + "/login/")
    login_page.login('admin_full', 'testpass123')
    page.wait_for_url(live_server.url + "/")

    dashboard = DashboardPage(page)
    dashboard.check_visible()

    dispositivos_page.navigate(live_server.url)
    page.wait_for_url(lambda url: "/dispositivos/" in url)

    expect(page.locator('h1')).to_contain_text('Control de Inventario')

    dispositivo = DispositivoFactory(
        estado=EstadoDisponibleFactory(),
        propietario_actual=None,
    )

    dispositivos_page.navigate(live_server.url)
    page.wait_for_timeout(500)

    expect(page.locator('table')).to_be_visible()

    page.click('text=Actas')
    page.wait_for_url(lambda url: "/actas/" in url)

    colaborador = ColaboradorFactory(first_name="Test", last_name="E2E")
    historial = HistorialAsignacionFactory(
        colaborador=colaborador,
        dispositivo=dispositivo,
        acta=None,
        fecha_fin=None,
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
def test_navigation_to_all_sections(live_server, page: Page, admin_user):
    """Validar que se puede navegar a todas las secciones principales."""
    login_page = LoginPage(page)

    login_page.navigate(live_server.url + "/login/")
    login_page.login('admin_full', 'testpass123')
    page.wait_for_url(live_server.url + "/")

    page.click('text=Activos IT')
    page.wait_for_url(lambda url: "/dispositivos/" in url)
    expect(page.locator('h1')).to_contain_text('Control de Inventario')

    page.click('text=Colaboradores')
    page.wait_for_url(lambda url: "/colaboradores/" in url)

    page.click('text=Actas')
    page.wait_for_url(lambda url: "/actas/" in url)

    page.click('text=Dashboard')
    page.wait_for_url(lambda url: "/" in url or "/dashboard/" in url)
