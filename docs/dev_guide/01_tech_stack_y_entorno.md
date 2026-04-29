# Guía del Entorno y Stack Tecnológico

Bienvenido al proyecto **Inventario JMIE**. Este documento te ayudará a entender la base fundamental de las tecnologías utilizadas para mantener todo el sistema funcionando correctamente y de forma optimizada.

## Stack Tecnológico Principal

### Backend
- **Python 3.12+ / Django 6.0.2:** Utilizamos el framework web más maduro de Python para gestionar nuestra base de datos, autenticación y vistas seguras.
- **Django REST Framework (DRF 3.16.1):** Utilizado para proveer conectividad REST en las áreas donde necesitamos consumir datos desde herramientas de terceros o asíncronas no gestionadas por HTMX.
- **django-constance:** Configuración dinámica (ej: prefijo de IDs de equipos) editable desde Django admin.
- **django-cotton:** Componentes HTML reutilizables tipo Web Components para templates Django.
- **django-filter:** Filtrado avanzado en listados y dashboard analítico.
- **django-import-export:** Importación y exportación de datos (CSV, Excel).
- **django-imagekit:** Procesamiento de imágenes (thumbnails para fotos de equipos).

### Frontend
- **HTMX (`django-htmx`):** Este proyecto adopta activamente la filosofía *hypermedia*. En lugar de utilizar React, Angular, o construir una SPA completa, insertamos atributos HTMX directamente en las plantillas de Django para lograr reactividad y actualizaciones de porciones de la interfaz web (DOM).
- **Alpine.js:** Se encarga del comportamiento de UI puro (Modales, tooltips, estados visuales sin ir al servidor). Maneja eventos del lado del cliente.
- **Tailwind CSS:** El proyecto usa utilitarios Tailwind en templates y formularios estilizados con `BaseStyledForm`.

### Pruebas y Aseguramiento de Calidad (QA)
- **Pytest:** Como *test runner* por defecto, usando librerías adjuntas como `pytest-django`, y soporte de *mocking* con `factory-boy`.
- **Playwright (`pytest-playwright`):** Utilizado para las pruebas de E2E (End-to-End). Playwright realiza flujos automatizados para comprobar los diálogos, modales HTMX o cambios renderizados por Alpine.js.

### Reportes
- **Playwright/Chromium:** Generación de PDFs mediante renderizado HTML→PDF. Usa un pool de browsers headless para performance.
- **pyHanko:** Firma digital de documentos PDF con certificado.
- **pypdf:** Manipulación de PDFs (verificación de firmas, extracción).
- **qrcode:** Generación de códigos QR para cada dispositivo.

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
    playwright install chromium  # Requerido para generación de PDFs
    ```

 3. **Configurar Variables de Entorno:**
    ```bash
    cp .env.example .env
    # Editar .env: rellenar SECRET_KEY con un valor seguro (>30 chars).
    # Opcional: definir DB_PATH si deseas ubicar la base de datos fuera de la raíz.
    ```

 4. **Migraciones e Inicio:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    python manage.py runserver
    ```

> [!NOTE]
> Siempre que se deban añadir bibliotecas nuevas, prioriza las utilidades que refuercen HTMX o el ecosistema nativo de Django, para no generar sobrecargas con tecnologías de SPA (Evitar React o Vue.js).

## Comandos de utilidad

### Importación masiva de dispositivos
El proyecto incluye un comando de administración para importar dispositivos desde CSV:

```bash
# Ejecución normal
python manage.py import_devices ruta/al/archivo.csv

# Modo simulación (sin guardar en base de datos)
python manage.py import_devices ruta/al/archivo.csv --dry-run
```

El comando detecta automáticamente múltiples variantes de nombres de columna, normaliza números de serie vacíos como `AUTO-XXXXXXXX`, genera siglas para nuevos tipos de dispositivo y reporta un resumen de filas creadas, actualizadas o con error.

## Política de dependencias

Para mantener el stack limpio, revisa la guía de higiene de dependencias:
- [`docs/dev_guide/dependency_hygiene.md`](dependency_hygiene.md)
