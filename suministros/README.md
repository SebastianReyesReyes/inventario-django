# Gestión de Suministros e Insumos

Esta aplicación administra el ciclo de vida de los consumibles y suministros técnicos (toners, tintas, repuestos, útiles) necesarios para la operación de los activos de la empresa.

## Propósito
Centralizar el control de stock de insumos, permitiendo rastrear su adquisición, consumo por parte de colaboradores y asignación a dispositivos específicos (principalmente impresoras).

## Modelo de Datos
- **Categoría de Suministro:** Clasificación lógica de los insumos. Permite definir compatibilidad general con tipos de dispositivos (ej: "Toners" son compatibles con "Impresoras Laser").
- **Suministro:** El catálogo de productos. Incluye SKU (código interno), fabricante, unidad de medida y niveles de stock mínimo para alertas.
- **Movimiento de Stock:** Libro de registro (ledger) que audita cada cambio en el inventario:
    - **Entradas:** Compras registradas con número de factura y costo unitario.
    - **Salidas:** Entregas a colaboradores, asignación a centros de costo o dispositivos específicos.
    - **Ajustes:** Correcciones por mermas, pérdidas o hallazgos en auditoría.

## Lógica de Compatibilidad
El sistema maneja una doble capa de compatibilidad para facilitar la entrega de insumos correctos:
1. **Por Categoría:** Vincula categorías de suministros con tipos de dispositivos.
2. **Por Modelo:** Vincula suministros específicos con modelos de hardware exactos (ej: El Toner TN-660 es compatible con la impresora HL-L2360DW).

## Control de Stock
- **Cálculo Automático:** El campo `stock_actual` se recalcula atómicamente en cada movimiento, evitando inconsistencias.
- **Alertas de Reposición:** Los suministros entran en estado de "Bajo Stock" cuando el inventario alcanza el nivel mínimo definido, permitiendo una gestión proactiva de compras.
- **Validación de Salidas:** El sistema impide registrar entregas de insumos que no tengan stock suficiente disponible.

## Componentes Técnicos
- **`registrar_movimiento_stock`:** Servicio transaccional que garantiza la integridad de los datos al actualizar el inventario.
- **QuerySets Personalizados:** Métodos para filtrar rápidamente suministros activos o aquellos que requieren reposición inmediata.
