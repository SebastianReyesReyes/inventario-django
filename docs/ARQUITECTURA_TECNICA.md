# Arquitectura Técnica - Sistema de Inventario JMIE

Este documento explica los patrones críticos del sistema para facilitar su escalabilidad y mantenimiento.

## 1. Sistema de Dispositivos (Polimorfismo Lite)
Para evitar la carga de librerías pesadas, el sistema usa un modelo de herencia manual.

*   **Modelos**: `Dispositivo` es la clase base. Modelos como `Notebook`, `Smartphone` y `Monitor` tienen un `OneToOneField` apuntando al padre.
*   **Extensibilidad**: Para añadir un nuevo tipo (ej: *Tablet*):
    1.  Crea el modelo en `dispositivos/models.py`.
    2.  Crea el formulario técnico en `dispositivos/forms.py`.
    3.  **Crítico**: Registra el nombre en `DispositivoFactory` (`dispositivos/services.py`). La fábrica usa búsqueda por subcadenas (insensible a mayúsculas), permitiendo que "Notebook" o "laptop" funcionen correctamente.

## 2. Motor de Interfaz (HTMX + Alpine.js)
El sistema utiliza una arquitectura de "Capas Apiladas" definida en `base.html`.

*   **Side-over**: Contenedor `#side-over-container` para detalles rápidos.
*   **Modales**: Contenedor `#modal-container` para formularios de acción (Reasignar, Devolver).
*   **Auto-sanación**: Si un script intenta abrir un modal y el contenedor no existe (debido a un swap de HTMX), `base.html` tiene un listener que lo re-crea dinámicamente y re-intenta la petición.

## 3. Trazabilidad Legal (Actas)
Las actas no son solo registros; son documentos legales vinculados a movimientos de inventario.

*   **Flujo**: `Vistas de Dispositivo` -> `ActaService` -> `Generación PDF`.
*   **Generación Automática**: Al realizar una asignación, se dispara el método `ActaService.crear_acta`. Este centraliza la lógica para asegurar que el folio sea correlativo y se vinculen los IDs de historial correctos.
*   **Aislamiento Transaccional**: La creación o edición del dispositivo y la generación del acta se ejecutan en bloques `transaction.atomic()` separados. Si la generación del acta falla, el registro del dispositivo no se revierte.
*   **Frontend**: La vista `trazabilidad_success.html` detecta la presencia de un objeto `acta` y gatilla un `window.open()` para entregar el PDF inmediatamente al usuario.

## 4. Manejo de Fechas
Los inputs de tipo `<input type="date">` de HTML5 requieren estrictamente el formato `YYYY-MM-DD`.
*   **Solución**: Todos los formularios que usen fechas deben forzar el formato en el widget:
    `forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})`.

## 5. Logging y Trazabilidad
El sistema configura loggers por aplicación (`dispositivos`, `actas`, `colaboradores`, `core`) que escriben en `inventario.log` en la raíz del proyecto. Esto permite auditar operaciones críticas (creación de equipos, generación de actas, cambios de asignación) sin depender de `print()`.

---
*Documentación actualizada el 24 de abril de 2026.*
