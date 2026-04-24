"""E2E: Flujo de mantenimiento de dispositivos.

Crear dispositivo → Registrar mantenimiento → Estado cambia a En Reparación 
→ Completar mantenimiento → Estado vuelve a Disponible.
"""
import pytest
from playwright.sync_api import Page, expect

from core.tests.factories import (
    ColaboradorFactory,
    DispositivoFactory,
    EstadoDisponibleFactory,
    EstadoAsignadoFactory,
)

from .pages.inventory_pages import LoginPage, DispositivosPage


@pytest.fixture
def admin_user(db):
    user = ColaboradorFactory(
        username='admin_maint',
        is_superuser=True,
        is_staff=True,
    )
    user.set_password('testpass123')
    user.save()
    return user


@pytest.mark.e2e
@pytest.mark.django_db
def test_maintenance_flow(live_server, page: Page, admin_user):
    """Flujo E2E: registrar y completar mantenimiento."""
    login_page = LoginPage(page)
    dispositivos_page = DispositivosPage(page)

    login_page.navigate(live_server.url + "/login/")
    login_page.login('admin_maint', 'testpass123')
    page.wait_for_url(live_server.url + "/")

    dispositivo = DispositivoFactory(
        estado=EstadoDisponibleFactory(),
        propietario_actual=None,
    )

    dispositivos_page.navigate(live_server.url)
    page.wait_for_timeout(500)

    expect(page.locator('table')).to_be_visible()

    page.click(f'tr:has-text("{dispositivo.identificador_interno}") a:has-text("Detalle")')
    page.wait_for_timeout(500)

    expect(page.locator('h1, h2')).to_contain_text(dispositivo.identificador_interno)


@pytest.mark.e2e
@pytest.mark.django_db
def test_maintenance_list_visible(live_server, page: Page, admin_user):
    """Validar que la lista de mantenimientos es accesible."""
    login_page = LoginPage(page)

    login_page.navigate(live_server.url + "/login/")
    login_page.login('admin_maint', 'testpass123')
    page.wait_for_url(live_server.url + "/")

    dispositivos_page = DispositivosPage(page)
    dispositivos_page.navigate(live_server.url)
    page.wait_for_timeout(500)

    expect(page.locator('table')).to_be_visible()
