import pytest
from playwright.sync_api import Page, expect
from core.tests.factories import ColaboradorFactory
from suministros.tests.factories import CategoriaSuministroFactory, SuministroFactory
from tests_e2e.pages.inventory_pages import LoginPage
from tests_e2e.pages.suministros_pages import SuministrosListPage, MovimientoModal
from suministros.tests.factories import MovimientoStockFactory


@pytest.fixture
def test_user(db):
    user = ColaboradorFactory(username='e2e_suministros', is_superuser=True, is_staff=True)
    user.set_password('12345')
    user.save()
    return user


@pytest.mark.e2e
@pytest.mark.django_db
def test_suministros_list_and_stock_badge(live_server, page: Page, test_user):
    cat = CategoriaSuministroFactory(nombre="Tintas")
    SuministroFactory(nombre="Tinta Negra", categoria=cat, stock_actual=10, stock_minimo=2)
    SuministroFactory(nombre="Tinta Cyan", categoria=cat, stock_actual=1, stock_minimo=2)
    SuministroFactory(nombre="Tinta Magenta", categoria=cat, stock_actual=0, stock_minimo=2)

    # Login
    login = LoginPage(page)
    login.navigate(live_server.url + "/login/")
    login.login('e2e_suministros', '12345')
    page.wait_for_url(live_server.url + "/")

    # Navigate
    list_page = SuministrosListPage(page)
    list_page.navigate(live_server.url)
    expect(page.locator('h1')).to_contain_text('Gestión de Suministros')

    # Verify rows and badges
    list_page.expect_row_visible('Tinta Negra')
    list_page.expect_row_visible('Tinta Cyan')
    list_page.expect_row_visible('Tinta Magenta')


@pytest.mark.e2e
@pytest.mark.django_db
def test_register_movement_updates_stock(live_server, page: Page, test_user):
    from suministros.models import MovimientoStock
    cat = CategoriaSuministroFactory()
    s = SuministroFactory(nombre="Papel A4", categoria=cat, stock_actual=5, stock_minimo=2)
    MovimientoStockFactory(suministro=s, tipo_movimiento=MovimientoStock.TipoMovimiento.ENTRADA, cantidad=5)
    s.recalcular_stock()

    login = LoginPage(page)
    login.navigate(live_server.url + "/login/")
    login.login('e2e_suministros', '12345')
    page.wait_for_url(live_server.url + "/")

    list_page = SuministrosListPage(page)
    list_page.navigate(live_server.url)

    # Open modal
    list_page.open_movement_modal('Papel A4')
    modal = MovimientoModal(page)
    modal.expect_visible()

    # Fill and submit
    modal.fill('SALIDA', '2', 'Entrega a operaciones')
    modal.submit()

    # Toast + updated badge (wait for HTMX refresh)
    expect(page.locator('text=Movimiento registrado')).to_be_visible(timeout=5000)
    expect(list_page.row_by_name('Papel A4').locator('text=OK (3)')).to_be_visible()


@pytest.mark.e2e
@pytest.mark.django_db
def test_oversale_shows_error_in_modal(live_server, page: Page, test_user):
    cat = CategoriaSuministroFactory()
    s = SuministroFactory(nombre="Tóner", categoria=cat, stock_actual=1, stock_minimo=1)

    login = LoginPage(page)
    login.navigate(live_server.url + "/login/")
    login.login('e2e_suministros', '12345')
    page.wait_for_url(live_server.url + "/")

    list_page = SuministrosListPage(page)
    list_page.navigate(live_server.url)
    list_page.open_movement_modal('Tóner')

    modal = MovimientoModal(page)
    modal.fill('SALIDA', '99')
    modal.submit()

    modal.expect_error('No hay suficiente stock')
