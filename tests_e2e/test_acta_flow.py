import pytest
from playwright.sync_api import Page, expect
from core.tests.factories import ColaboradorFactory, HistorialAsignacionFactory, DispositivoFactory
from .pages.inventory_pages import LoginPage

@pytest.fixture
def e2e_user(db):
    user = ColaboradorFactory(username='admin_actas', is_superuser=True, is_staff=True)
    user.set_password('12345')
    user.save()
    return user

@pytest.mark.e2e
@pytest.mark.django_db
def test_create_acta_flow(live_server, page: Page, e2e_user):
    """Prueba E2E del flujo completo de creación de un acta de entrega"""
    login_page = LoginPage(page)
    
    # 1. Login
    login_page.navigate(live_server.url + "/login/")
    login_page.login('admin_actas', '12345')
    page.wait_for_url(live_server.url + "/")
    
    # 2. Navegar a Actas
    page.click('text=Actas')
    page.wait_for_url(lambda url: "/actas/" in url)
    
    # 3. Datos previos: Colaborador con asignación pendiente
    colaborador = ColaboradorFactory(first_name="Test", last_name="E2E")
    dispositivo = DispositivoFactory(numero_serie="SN-E2E-123")
    HistorialAsignacionFactory(colaborador=colaborador, dispositivo=dispositivo, acta=None)
    
    # 4. Abrir modal de creación
    page.click('text=Generar Acta')
    # Esperamos que aparezca el título del modal
    expect(page.locator('h2:has-text("Generar")')).to_be_visible()
    
    # 5. Seleccionar colaborador
    # El select suele tener clases de htmx o django-widget-tweaks
    page.select_option('select[name="colaborador"]', label=f"{colaborador.first_name} {colaborador.last_name}")
    
    # 6. Esperar a que se carguen las asignaciones pendientes (HTMX)
    # Buscamos el checkbox de la asignación
    checkbox = page.locator('input[name="asignaciones"]')
    expect(checkbox).to_be_visible()
    checkbox.check()
    
    # 7. Enviar formulario
    page.click('button:has-text("Emitir Acta")')
    
    # 8. Validar que el modal se cierra y el acta aparece en la lista
    # (El modal se cierra al recibir el evento 'actaCreated')
    expect(page.locator('#modal-container')).not_to_be_visible()
    
    # 9. Verificar que el acta aparece en el listado (folio generado)
    # Refrescamos o esperamos el trigger de htmx
    expect(page.locator('#search-results')).to_contain_text("Test E2E")
