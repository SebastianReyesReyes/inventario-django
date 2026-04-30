from playwright.sync_api import Page, expect


class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.username_input = page.locator('input[name="username"]')
        self.password_input = page.locator('input[name="password"]')
        self.submit_button = page.locator('button[type="submit"]')

    def navigate(self, url):
        self.page.goto(url)

    def login(self, username, password):
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.submit_button.click()


class DashboardPage:
    def __init__(self, page: Page):
        self.page = page
        self.navbar = page.locator('nav')
        self.sidebar = page.locator('aside')

    def check_visible(self):
        expect(self.navbar).to_be_visible()


class DispositivosPage:
    """Page Object para el listado y CRUD de dispositivos."""

    def __init__(self, page: Page):
        self.page = page
        self.table = page.locator('table')
        self.new_button = page.locator('a:has-text("Nuevo"), button:has-text("Nuevo")')
        self.search_input = page.locator('input[placeholder*="Buscar"], input[name="q"]')

    def navigate(self, base_url):
        self.page.goto(f"{base_url}/dispositivos/")

    def click_new(self):
        self.new_button.click()

    def search(self, query):
        self.search_input.fill(query)

    def device_row(self, identifier):
        return self.page.locator(f'tr:has-text("{identifier}")')

    def expect_device_visible(self, identifier):
        expect(self.device_row(identifier)).to_be_visible()

    def expect_device_not_visible(self, identifier):
        expect(self.device_row(identifier)).not_to_be_visible()

    def row_count(self):
        return self.page.locator('tbody tr').count()


class DispositivoFormPage:
    """Page Object para el formulario de creación/edición de dispositivo."""

    def __init__(self, page: Page):
        self.page = page
        self.form = page.locator('form')
        self.submit_button = page.locator('button[type="submit"]')

    def fill_field(self, name, value):
        field = self.page.locator(f'input[name="{name}"], select[name="{name}"], textarea[name="{name}"]')
        if field.count() > 0:
            tag = field.first.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                self.page.select_option(f'[name="{name}"]', str(value))
            else:
                field.first.fill(str(value))

    def select_option(self, name, label):
        self.page.select_option(f'select[name="{name}"]', label=label)

    def submit(self):
        self.submit_button.click()

    def expect_error(self, text):
        expect(self.page.locator(f'.errorlist:has-text("{text}"), .text-red:has-text("{text}")')).to_be_visible()


class ColaboradoresPage:
    """Page Object para el listado de colaboradores."""

    def __init__(self, page: Page):
        self.page = page
        self.table = page.locator('table')
        self.new_button = page.locator('a:has-text("Nuevo"), button:has-text("Nuevo")')

    def navigate(self, base_url):
        self.page.goto(f"{base_url}/colaboradores/")

    def colaborador_row(self, name):
        return self.page.locator(f'tr:has-text("{name}")')


class ActasPage:
    """Page Object para el listado y generación de actas."""

    def __init__(self, page: Page):
        self.page = page
        self.table = page.locator('table')
        # Selector más específico para evitar duplicados con el empty state
        self.generate_button = page.locator('header button:has-text("Generar Acta"), header a:has-text("Generar Acta")').first
        self.modal = page.locator('#modal-container, [role="dialog"]')
        self.sideover = page.locator('text=Vista Previa del Acta').locator('xpath=ancestor::div[contains(@class, "fixed")]')

    def navigate(self, base_url):
        self.page.goto(f"{base_url}/actas/")

    def click_generate(self):
        self.generate_button.click()

    def expect_modal_visible(self):
        expect(self.modal).to_be_visible()

    def expect_modal_hidden(self):
        expect(self.modal).not_to_be_visible()

    def select_colaborador(self, label):
        self.page.select_option('select[name="colaborador"]', label=label)

    def check_asignacion(self):
        checkbox = self.page.locator('input[name="asignaciones"]').first
        checkbox.check()

    def click_preview(self):
        """Hace clic en el botón Previsualizar Acta."""
        self.page.click('button:has-text("Previsualizar Acta")')

    def click_confirm(self):
        """Hace clic en Confirmar y Generar Acta dentro del side-over."""
        self.page.click('button:has-text("Confirmar y Generar Acta")')

    def click_volver_a_editar(self):
        """Hace clic en Volver a Editar dentro del side-over."""
        self.page.click('button:has-text("Volver a Editar")')

    def expect_sideover_visible(self):
        expect(self.page.locator('text=Vista Previa del Acta')).to_be_visible()

    def expect_sideover_hidden(self):
        expect(self.page.locator('text=Vista Previa del Acta')).not_to_be_visible()

    def expect_preview_contains(self, text):
        expect(self.page.locator('.preview-document')).to_contain_text(text)

    def submit(self):
        """Flujo completo: preview + confirmar (para compatibilidad con tests antiguos)."""
        self.click_preview()
        self.expect_sideover_visible()
        self.click_confirm()

    def expect_acta_in_list(self, text):
        expect(self.page.locator('#search-results, table')).to_contain_text(text)

    def acta_row(self, folio):
        return self.page.locator(f'tr:has-text("{folio}")')


class AsignacionPage:
    """Page Object para asignar dispositivo a colaborador."""

    def __init__(self, page: Page):
        self.page = page
        self.form = page.locator('form')

    def select_colaborador(self, label):
        self.page.select_option('select[name="colaborador"]', label=label)

    def fill_condicion(self, text):
        self.page.fill('textarea[name="condicion_fisica"], input[name="condicion_fisica"]', text)

    def check_generar_acta(self):
        checkbox = self.page.locator('input[name="generar_acta"]')
        checkbox.check()

    def submit(self):
        self.page.locator('button[type="submit"]').click()


class DevolucionPage:
    """Page Object para devolver dispositivo a bodega."""

    def __init__(self, page: Page):
        self.page = page
        self.form = page.locator('form')

    def fill_condicion(self, text):
        self.page.fill('textarea[name="condicion_fisica"], input[name="condicion_fisica"]', text)

    def select_estado_llegada(self, value):
        self.page.select_option('select[name="estado_llegada"]', value=value)

    def check_generar_acta(self):
        checkbox = self.page.locator('input[name="generar_acta"]')
        checkbox.check()

    def submit(self):
        self.page.locator('button[type="submit"]').click()


class MantenimientoPage:
    """Page Object para registrar mantenimiento."""

    def __init__(self, page: Page):
        self.page = page
        self.form = page.locator('form')

    def fill_falla(self, text):
        self.page.fill('textarea[name="falla_reportada"], input[name="falla_reportada"]', text)

    def fill_reparacion(self, text):
        self.page.fill('textarea[name="reparacion_realizada"], input[name="reparacion_realizada"]', text)

    def submit(self):
        self.page.locator('button[type="submit"]').click()
