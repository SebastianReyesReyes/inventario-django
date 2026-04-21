# Guía del Entorno y Stack Tecnológico

Bienvenido al proyecto **Inventario JMIE**. Este documento te ayudará a entender la base fundamental de las tecnologías utilizadas para mantener todo el sistema funcionando correctamente y de forma optimizada.

## Stack Tecnológico Principal

### Backend
- **Python 3.12+ / Django 6.x:** Utilizamos el framework web más maduro de Python para gestionar nuestra base de datos, autenticación y vistas seguras.
- **Django REST Framework (DRF):** Utilizado para proveer conectividad REST en las áreas donde necesitamos consumir datos desde herramientas de terceros o asíncronas no gestionadas por HTMX.

### Frontend
- **HTMX (`django-htmx`):** Este proyecto adopta activamente la filosofía *hypermedia*. En lugar de utilizar React, Angular, o construir una SPA completa, insertamos atributos HTMX directamente en las plantillas de Django para lograr reactividad y actualizaciones de porciones de la interfaz web (DOM).
- **Alpine.js:** Se encarga del comportamiento de UI puro (Modales, tooltips, estados visuales sin ir al servidor). Maneja eventos del lado del cliente.
- **Tailwind CSS (`crispy-tailwind`):** Todo el sistema "Consola de Precisión" está estilizado utilizado componentes y utilitarios de Tailwind CSS acoplados a Django Crispy Forms, para una renderización automática de nuestros formularios web.

### Pruebas y Aseguramiento de Calidad (QA)
- **Pytest:** Como *test runner* por defecto, usando librerías adjuntas como `pytest-django`, y soporte de *mocking* con `factory-boy`.
- **Playwright (`pytest-playwright`):** Utilizado para las pruebas de E2E (End-to-End). Playwright realiza flujos automatizados para comprobar los diálogos, modales HTMX o cambios renderizados por Alpine.js.

### Reportes
- **xHtml2Pdf / ReportLab:** Dedicado a la rasterización y diseño de plantillas HTML para exportar documentos PDF (Actas, Entregas, Inventario seriado).

## Flujo Básico de Configuración del Entorno de Desarrollo (Local)

1. **Clonar e Inicializar el Entorno (Windows):**
   ```powershell
   git clone <repo-url>
   cd inventario-django
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Instalar Dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Migraciones e Inicio:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py runserver
   ```

> [!NOTE]
> Siempre que se deban añadir bibliotecas nuevas, prioriza las utilidades que refuercen HTMX o el ecosistema nativo de Django, para no generar sobrecargas con tecnologías de SPA (Evitar React o Vue.js).
