# Dashboard y Analítica de Inventario

Esta aplicación proporciona una interfaz centralizada para la visualización de métricas clave y el análisis del estado global del inventario de dispositivos y activos de la empresa.

## Propósito
El módulo de Dashboard actúa como la capa de inteligencia del sistema, transformando los datos crudos de dispositivos, mantenimientos y asignaciones en indicadores procesables para la toma de decisiones.

## Métricas Principales
El sistema calcula y muestra dinámicamente:
- **Estado Operativo:** Conteo de dispositivos disponibles, asignados, en reparación o de baja.
- **Salud del Inventario:** Porcentaje de asignación de activos y cantidad de colaboradores activos.
- **Métricas Financieras:** Valor contable total del inventario y costos acumulados de mantenimiento/reparación.
- **Disponibilidad Crítica:** Stock en tiempo real de equipos de alta demanda (Notebooks, Smartphones, Impresoras).
- **Actividad Reciente:** Resumen de mantenimientos realizados en los últimos 30 días.

## Sistema de Filtros (Drill-down)
La aplicación utiliza un sistema de filtros avanzados (`AnaliticaInventarioFilter`) que permite segmentar todas las métricas y gráficos por:
- **Rango de Fechas:** Basado en la fecha de adquisición de los equipos.
- **Ubicación Técnica:** Filtrado por Centro de Costo u Obra.
- **Taxonomía:** Por Tipo de Dispositivo o Fabricante.
- **Estado:** Filtrado por situación actual (Ej: Ver solo equipos en "Reparación").

## Visualización de Datos
Incluye datasets preparados para representaciones gráficas:
1. **Distribución por Tipo:** Proporción de equipos por categoría (Notebooks vs Desktop, etc.).
2. **Estado de Dispositivos:** Resumen visual del ciclo de vida.
3. **Top 10 Centros de Costo:** Identificación de las unidades con mayor carga de activos o valor contable.
4. **Tendencia de Adquisiciones:** Historial de compras de los últimos 12 meses.

## Componentes Técnicos
- **`DashboardMetricsService`:** Servicio centralizado que encapsula la lógica de agregación y cálculo de KPIs.
- **Integración con Chart.js:** Los datos se sirven listos para ser consumidos por librerías de gráficos en el frontend.
