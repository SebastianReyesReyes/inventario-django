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
