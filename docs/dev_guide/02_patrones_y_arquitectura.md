# Arquitectura y Patrones de Diseño

El sistema está dividido en módulos o 'apps' según los principios de Django enfocados al negocio. Para escalar y asegurar la calidad, implementamos patrones de diseño consolidados.

## Arquitectura de Aplicaciones (Apps)

1. **`core`:** Toda la infraestructura global del sistema. Incluye los *templates* base, layouts (sidebar, navbars), utilidades transversales, helpers HTMX (`core/htmx.py`), componentes Cotton reutilizables, templatetags (`ui_tags`, `nav_tags`, `url_tags`, `action_tags`), y comando de importación masiva (`import_devices`).
2. **`dispositivos`:** Maneja el núcleo del sistema: gestión de inventario con 6 tipos especializados (Notebook, Smartphone, Impresora, Servidor, EquipoRed, Monitor), mantenimientos, asignaciones, devoluciones, reasignaciones, accesorios, generación de QR, y trazabilidad completa.
3. **`colaboradores`:** Módulo aislado para la asignación y gestión del personal. Define el `AUTH_USER_MODEL` (`Colaborador`), con soporte para RUT chileno, centros de costo, cargos, y soft delete (`esta_activo`).
4. **`actas`:** Centraliza la lógica de actas legales (ENTREGA, DEVOLUCIÓN, DESTRUCCIÓN), generación de folios correlativos, firma digital con pyHanko, exportación PDF con Playwright/Chromium, y gestión de ministros de fe.
5. **`dashboard`:** Proveedor de vistas estadísticas y operativa global, métricas, contadores, filtros analíticos (`django-filter`), gráficos Chart.js con drill-down a listados filtrados, y exportación de reportes.

## Patrones de Diseño Utilizados

### 1. Patrón Layered / Services Pattern (Patrón Servicios)
En Django, es usual pecar de vistas obesas ("Fat Views"). En este proyecto derivamos lógica transaccional y compleja a una **Capa de Servicios**:
* Ejemplo: Para asignar múltiples dispositivos, cambiar el estado del mismo, e incrementar los conteos, esta orquestación reside en clases agrupadas como `ActaService` (`actas/services.py`) y `DispositivoFactory` / `TrazabilidadService` (`dispositivos/services.py`).
* Favorece la "separación de preocupaciones" (*Separation of Concerns*). La vista de Django sólo se encarga de recibir HTTP, procesarlo en la capa servicio y retornar `TemplateResponse` o una respuesta HTMX.

### Transacciones anidadas y aislamiento de fallos
Cuando una vista realiza una escritura principal (ej. crear un `Dispositivo`) y luego una operación secundaria que puede fallar (ej. generar un acta legal), se utilizan **bloques `transaction.atomic()` separados**. De este modo, el fallo de la operación secundaria no revierte la escritura principal.

### 2. Patrón Repositorio (vía Django ORM)
Django automáticamente funciona con el patrón de Active Record bajo su ORM. Extendemos `models.Manager` y `models.QuerySet` para agregar lógica específica de la base de datos (por ejemplo, buscar dispositivos filtrados por centro de costos específicos de un proyecto).

### 3. HATEOAS (Level 3 REST) y Diseño Hypermedia
Dado que usamos HTMX, evitamos enviar JSON. El servidor envía los *estado* al cliente, encapsulado en trozos (partials) de HTML.

> [!TIP]
> Si la regla de negocio afecta más de dos modelos a la vez, o necesita transacciones DB garantizadas por `atomic`, **debes usar un Servicio** en vez de escribir la lógica dentro de la misma función en `views.py`.
