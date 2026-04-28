import re
from playwright.sync_api import Page, expect


class SuministrosListPage:
    def __init__(self, page: Page):
        self.page = page
        self.table = page.locator('table')
        self.search_input = page.locator('input[name="q"]')
        self.new_button = page.locator('a:has-text("Nuevo Suministro")')
        self.modal_container = page.locator('#modal-container')

    def navigate(self, base_url):
        self.page.goto(f"{base_url}/suministros/")

    def search(self, query: str):
        self.search_input.fill(query)
        self.search_input.press('Enter')

    def row_by_name(self, name: str):
        return self.page.locator(f'tr:has-text("{name}")')

    def expect_row_visible(self, name: str):
        expect(self.row_by_name(name)).to_be_visible()

    def open_movement_modal(self, name: str):
        row = self.row_by_name(name)
        row.locator('button:has-text("Movimiento")').click()

    def stock_badge(self, name: str):
        return self.row_by_name(name).locator('span').filter(has_text=re.compile(r'(OK|Bajo|Sin)'))


class MovimientoModal:
    def __init__(self, page: Page):
        self.page = page
        self.modal = page.locator('#modal-container >> div >> div >> div').first
        self.tipo_select = page.locator('select[name="tipo_movimiento"]')
        self.cantidad_input = page.locator('input[name="cantidad"]')
        self.notas_input = page.locator('textarea[name="notas"]')
        self.submit_button = page.locator('button:has-text("Confirmar")')
        self.close_button = page.locator('button:has-text("Cancelar")')

    def fill(self, tipo: str, cantidad: str, notas: str = ""):
        self.page.select_option('select[name="tipo_movimiento"]', tipo)
        self.cantidad_input.fill(cantidad)
        if notas:
            self.notas_input.fill(notas)

    def submit(self):
        self.submit_button.click()

    def expect_visible(self):
        expect(self.modal).to_be_visible()

    def expect_error(self, message: str):
        expect(self.page.locator('text=' + message)).to_be_visible()
