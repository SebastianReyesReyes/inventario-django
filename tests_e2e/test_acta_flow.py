import pytest
from playwright.sync_api import Page, expect
from core.tests.factories import ColaboradorFactory, HistorialAsignacionFactory, DispositivoFactory
from .pages.inventory_pages import LoginPage, ActasPage

@pytest.fixture
def e2e_user(db):
    user = ColaboradorFactory(username='admin_actas', is_superuser=True, is_staff=True)
    user.set_password('12345')
    user.save()
    return user

@pytest.mark.e2e
@pytest.mark.django_db
def test_create_acta_flow(live_server, page: Page, e2e_user):
    """Prueba E2E del flujo completo de creación de un acta de entrega via preview"""
    login_page = LoginPage(page)
    actas_page = ActasPage(page)

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
    actas_page.click_generate()
    expect(page.locator('h2:has-text("Generar")')).to_be_visible()

    # 5. Seleccionar colaborador
    actas_page.select_colaborador(f"{colaborador.first_name} {colaborador.last_name}")

    # 6. Esperar a que se carguen las asignaciones pendientes (HTMX)
    actas_page.check_asignacion()

    # 7. Previsualizar → Confirmar (nuevo flujo de 2 pasos)
    actas_page.click_preview()
    actas_page.expect_sideover_visible()
    actas_page.expect_preview_contains("PRELIMINAR")
    actas_page.expect_preview_contains(colaborador.nombre_completo)
    actas_page.expect_preview_contains("SN-E2E-123")
    actas_page.click_confirm()

    # 8. Validar que el modal se cierra y el acta aparece en la lista
    actas_page.expect_modal_hidden()

    # 9. Verificar que el acta aparece en el listado
    actas_page.expect_acta_in_list("Test E2E")


@pytest.mark.e2e
@pytest.mark.django_db
def test_preview_acta_and_cancel(live_server, page: Page, e2e_user):
    """Prueba E2E del flujo de preview: abrir preview, revisar, volver a editar, y luego confirmar"""
    login_page = LoginPage(page)
    actas_page = ActasPage(page)

    # 1. Login
    login_page.navigate(live_server.url + "/login/")
    login_page.login('admin_actas', '12345')
    page.wait_for_url(live_server.url + "/")

    # 2. Navegar a Actas
    page.click('text=Actas')
    page.wait_for_url(lambda url: "/actas/" in url)

    # 3. Datos previos
    colaborador = ColaboradorFactory(first_name="Preview", last_name="Test")
    dispositivo = DispositivoFactory(numero_serie="SN-PREV-456")
    HistorialAsignacionFactory(colaborador=colaborador, dispositivo=dispositivo, acta=None)

    # 4. Abrir modal
    actas_page.click_generate()
    expect(page.locator('h2:has-text("Generar")')).to_be_visible()

    # 5. Llenar formulario
    actas_page.select_colaborador(f"{colaborador.first_name} {colaborador.last_name}")
    actas_page.check_asignacion()

    # 6. Previsualizar → aparece side-over
    actas_page.click_preview()
    actas_page.expect_sideover_visible()

    # 7. Verificar contenido del preview (documento legal renderizado)
    actas_page.expect_preview_contains("Documento Preliminar")
    actas_page.expect_preview_contains("PENDIENTE")
    actas_page.expect_preview_contains(colaborador.nombre_completo)
    actas_page.expect_preview_contains("SN-PREV-456")
    actas_page.expect_preview_contains("Cláusulas de Responsabilidad")

    # 8. Volver a editar → side-over se cierra, modal sigue abierto
    actas_page.click_volver_a_editar()
    actas_page.expect_sideover_hidden()
    expect(page.locator('h2:has-text("Generar")')).to_be_visible()

    # 9. Previsualizar de nuevo y confirmar
    actas_page.click_preview()
    actas_page.expect_sideover_visible()
    actas_page.click_confirm()

    # 10. Verificar que se creó el acta
    actas_page.expect_modal_hidden()
    actas_page.expect_acta_in_list("Preview Test")
