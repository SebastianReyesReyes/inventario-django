# Arquitectura Técnica - Sistema de Inventario JMIE

Este documento explica los patrones críticos del sistema para facilitar su escalabilidad y mantenimiento.

## 1. Sistema de Dispositivos (Herencia Manual)
El sistema usa un modelo de herencia manual (multi-table inheritance de Django) para evitar complejidad innecesaria.

*   **Modelo Base**: `Dispositivo` contiene campos comunes (identificador_interno, numero_serie, tipo, estado, modelo, propietario_actual, centro_costo, fecha_compra, valor_contable, notas_condicion, foto_equipo).
*   **Modelos Especializados** (OneToOne implícito vía multi-table inheritance):
    - `Notebook`: procesador, ram_gb, almacenamiento, sistema_operativo, mac_address, ip_asignada
    - `Smartphone`: imei_1, imei_2, numero_telefono
    - `Impresora`: es_multifuncional, tipo_tinta, mac_address, ip_asignada
    - `Servidor`: rack_u, configuracion_raid, procesadores_fisicos, criticidad
    - `EquipoRed`: subtipo, firmware_version, mac_address, ip_gestion
    - `Monitor`: pulgadas, resolucion
*   **Identificador Automático**: Formato configurable `PREFIX-SIGLA-NNNN` (ej: `JMIE-NB-0001`). Se genera en `save()` usando `django-constance` para el prefijo y la sigla del `TipoDispositivo`.
*   **Extensibilidad**: Para añadir un nuevo tipo (ej: *Tablet*):
    1. Crea el modelo en `dispositivos/models.py` heredando de `Dispositivo`.
    2. Crea el formulario técnico en `dispositivos/forms.py`.
    3. Registra en `DispositivoFactory` (`dispositivos/services.py`) para mapeo tipo→form.

## 2. Motor de Interfaz (HTMX + Alpine.js + Cotton)
El sistema utiliza una arquitectura de "Capas Apiladas" definida en `base.html`.

*   **Side-over**: Contenedor `#side-over-container` para detalles rápidos.
*   **Modales**: Contenedor `#modal-container` para formularios de acción (Reasignar, Devolver).
*   **Auto-sanación**: Si un script intenta abrir un modal y el contenedor no existe (debido a un swap de HTMX), `base.html` tiene un listener que lo re-crea dinámicamente y re-intenta la petición.
*   **Componentes Cotton**: Se usa `django-cotton` para componentes reutilizables (`btn_primary`, `empty_state`, `glass_panel`, `page_header`, `search_input`, `th_sort`, etc.).

## 3. Trazabilidad Legal (Actas)
Las actas no son solo registros; son documentos legales vinculados a movimientos de inventario.

*   **Flujo**: `Vistas de Dispositivo` → `TrazabilidadService` → `ActaService` → `Generación PDF`.
*   **Tipos de Acta**: ENTREGA, DEVOLUCIÓN, DESTRUCCIÓN (configurable).
*   **Generación Automática**: Al realizar una asignación, reasignación, devolución o edición con cambio de propietario, se dispara `ActaService.crear_acta`. Este centraliza la lógica para asegurar que el folio sea correlativo y se vinculen los IDs de historial correctos.
*   **Aislamiento Transaccional**: La creación o edición del dispositivo y la generación del acta se ejecutan en bloques `transaction.atomic()` separados. Si la generación del acta falla, el registro del dispositivo no se revierte.
*   **Firma Digital**: Las actas pueden ser firmadas digitalmente vía `ActaService.firmar_acta()` usando pyHanko.
*   **Ministro de Fe**: Cada acta puede tener un ministro de fe (administrador de la misma obra/centro de costo).
*   **Frontend**: La vista detecta la presencia de un objeto `acta` y gatilla la descarga/visualización del PDF.
*   **Accesorios**: `EntregaAccesorio` también se vincula a actas para trazabilidad completa.

## 4. Manejo de Fechas
Los inputs de tipo `<input type="date">` de HTML5 requieren estrictamente el formato `YYYY-MM-DD`.
*   **Solución**: Todos los formularios que usen fechas deben forzar el formato en el widget:
    `forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})`.

## 5. Logging y Trazabilidad
El sistema configura loggers por aplicación (`dispositivos`, `actas`, `colaboradores`, `core`) que escriben en `inventario.log` en la raíz del proyecto. Esto permite auditar operaciones críticas (creación de equipos, generación de actas, cambios de asignación) sin depender de `print()`.

---
*Documentación actualizada el 24 de abril de 2026.*
