import pytest
from playwright.sync_api import Page, expect
from core.tests.factories import ColaboradorFactory
from .pages.inventory_pages import LoginPage, DashboardPage

@pytest.fixture
def test_user(db):
    user = ColaboradorFactory(username='admin_e2e', is_superuser=True, is_staff=True)
    user.set_password('12345')
    user.save()
    return user

@pytest.mark.e2e
@pytest.mark.django_db
def test_login_and_dashboard_render(live_server, page: Page, test_user):
    """Prueba E2E que valida el inicio de sesión y renderización del dashboard"""
    login_page = LoginPage(page)
    dashboard_page = DashboardPage(page)
    
    # 1. Navegar al Login
    login_page.navigate(live_server.url + "/login/")
    
    # 2. Iniciar sesión
    login_page.login('admin_e2e', '12345')
    
    # 3. Validar redirección a Home / Dashboard
    page.wait_for_url(live_server.url + "/")
    
    # 4. Validar visibilidad del dashboard (usando Page Object)
    dashboard_page.check_visible()
    
    # 5. Validar que la URL es correcta
    assert live_server.url in page.url

@pytest.mark.e2e
@pytest.mark.django_db
def test_navigation_to_dispositivos(live_server, page: Page, test_user):
    """Prueba la navegación hacia el listado de dispositivos desde el dashboard"""
    login_page = LoginPage(page)
    
    # Login directo
    login_page.navigate(live_server.url + "/login/")
    login_page.login('admin_e2e', '12345')
    page.wait_for_url(live_server.url + "/")
    
    # Navegar a dispositivos
    # El texto real en base.html es 'Activos IT'
    page.click('text=Activos IT') 
    page.wait_for_url(lambda url: "/dispositivos/" in url)
    
    expect(page.locator('h1')).to_contain_text('Control de Inventario')
