# Plan de Implementación: Dashboard Operacional y Estratégico

## Contexto
El sistema JMIE requiere separar las métricas del Centro de Mando en tres enfoques (Hardware, Suministros y Vista Estratégica) para mejorar la usabilidad y rapidez de las operaciones del día a día, sin perder la capacidad de análisis profundo en los filtros avanzados.

## Objetivos
- Reducir el ruido visual en el día a día para el equipo TI.
- Exponer "Qué hardware tengo disponible ahora".
- Exponer "Qué packs de suministros están disponibles por familia de impresoras".
- Mantener la vista de analítica avanzada bajo una pestaña separada.

## Fases de Implementación

### Fase 1: Backend & Servicios (Completado)
1. **`DashboardMetricsService` (`dashboard/services.py`)**:
   - Agregar método `get_hardware_availability(cls)` para agrupar disponibilidad por `TipoDispositivo`.
   - Agregar método `get_suministros_packs(cls)` para agrupar por fingerprint de compatibilidad.
   - Renombrar `build_context` a `build_strategic_context`.

### Fase 2: Views & URLs (Completado)
1. **Vistas HTMX (`dashboard/views.py`)**:
   - `dashboard_principal`: Solo renderiza el shell base con Alpine.js.
   - `tab_hardware`: Retorna la vista parcial con `hardware_data`.
   - `tab_suministros`: Retorna la vista parcial con `packs_data`.
   - `tab_estrategico`: Ejecuta filtros y retorna el dashboard analítico original.
2. **Enrutamiento (`dashboard/urls.py`)**:
   - Agregar endpoints `tab-hardware/`, `tab-suministros/`, `tab-estrategico/`.

### Fase 3: Templates & Frontend (Completado)
1. **Shell (`dashboard/index.html`)**:
   - Implementar Tabs con `x-data="{ activeTab: 'hardware' }"`.
   - Botones con `hx-get` apuntando a las nuevas URLs y `hx-target="#tab-content"`.
2. **Parcial Hardware (`dashboard/partials/tab_hardware.html`)**:
   - Grid de tarjetas mostrando Tipo de Equipo, Stock y Semáforo de disponibilidad (Rojo/Amarillo/Verde) basado en el umbral.
3. **Parcial Suministros (`dashboard/partials/tab_suministros.html`)**:
   - Grid de Packs mostrando familias de modelos y lista interna de suministros (con flag de stock crítico).
4. **Parcial Estratégico (`dashboard/partials/tab_estrategico.html`)**:
   - Migrar el panel de filtros y la inclusión del `dashboard_content.html` original.

## Siguientes Pasos
- Verificar que el script de gráficos de Chart.js funciona correctamente en recargas parciales.
- Ejecutar migraciones o tests faltantes de la capa de Suministros.
