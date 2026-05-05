# Core App

La aplicación `core` es la base del sistema de inventario. Proporciona los modelos de catálogos compartidos, utilidades HTMX, componentes de interfaz reutilizables (Cotton) y validadores comunes.

## Propósito

Centralizar la lógica transversal que no pertenece a un dominio específico pero es requerida por múltiples módulos del sistema.

## Catálogos (Modelos Base)

El sistema utiliza varios catálogos para clasificar y organizar los activos y el personal:

*   **Fabricante:** Marcas de los dispositivos (ej: Dell, Apple, Samsung).
*   **Modelo:** Modelos específicos de hardware, vinculados a un fabricante y un tipo de dispositivo.
*   **Tipo de Dispositivo:** Categorías generales de hardware (ej: Notebook, Smartphone, Monitor).
*   **Estado de Dispositivo:** Estados del ciclo de vida (ej: Operativo, En Bodega, En Reparación, Baja).
*   **Departamento:** Unidades organizativas de la institución.
*   **Centro de Costo:** Unidades contables para el seguimiento financiero.

## Utilidades HTMX (`htmx.py`)

Se implementó un conjunto de helpers para estandarizar las respuestas HTMX:

*   `is_htmx(request)`: Detecta si la petición es de HTMX.
*   `htmx_trigger_response(trigger, status=204)`: Retorna una respuesta vacía con el header `HX-Trigger`.
*   `htmx_success_or_redirect`: Maneja el flujo de éxito: si es HTMX dispara un trigger; si es una petición normal, redirige.
*   `htmx_render_or_redirect`: Renderiza un parcial para peticiones HTMX o redirige para peticiones estándar.

### Patrones de Trigger comunes:
*   `fabricanteListChanged`, `modeloListChanged`, `tipoListChanged`, etc.
*   `showNotification`: Utilizado para mostrar mensajes Toast/Flash al usuario.

## Componentes Cotton

Ubicados en `templates/cotton/`, estos componentes permiten construir interfaces consistentes:

*   **Botones:** `<c-btn-primary>` y `<c-btn-secondary>`.
*   **Layout:** `<c-page-header>` y `<c-empty-state>`.
*   **Tablas:** `<c-th-sort>` y `<c-paginator>`.
*   **Feedback:** `<c-htmx-loader>` y `<c-confirm-dialog>`.
*   **Formularios:** `<c-search-input>` y `<c-form-label>`.

## Validadores y Utilidades (`utils.py`)

*   **Validación de RUT:** Incluye una función `validar_rut_chileno` (Algoritmo Módulo 11) y un validador de clase `RUTChilenoValidator` para ser usado directamente en modelos o formularios de Django.

## Vistas de Catálogos (`catalog_views.py`)

Contiene clases base (`CatalogCreateViewBase`, `CatalogUpdateViewBase`, `CatalogDeleteViewBase`) que implementan el contrato HTMX de manera uniforme para todos los catálogos, incluyendo validaciones de protección (ej: no eliminar un Fabricante si tiene Modelos asociados).
