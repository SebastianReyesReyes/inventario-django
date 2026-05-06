# 🗺️ Roadmap de Mejoras — Inventario JMIE

> **Fecha:** Mayo 2026  
> **Estado actual del sistema:** Release 1 completo (7 Épicas, 28 HUs), Dashboard Operacional implementado, Piloto UAT en progreso.
> **Audiencia:** Equipo técnico + stakeholders.

---

## Resumen Ejecutivo

El sistema ya cubre el ciclo de vida completo de hardware (registro → asignación → devolución → acta legal) y tiene un módulo de suministros funcional. El Dashboard Operacional entrega visibilidad inmediata a Katherine y al equipo.

Este roadmap identifica **32 oportunidades** organizadas en 5 horizontes de madurez, priorizadas por impacto operacional y complejidad técnica.

---

## Horizonte 1: Robustez Operativa (Sprint inmediato)
> _"Lo que debería funcionar antes de que más gente use el sistema."_

| # | Mejora | Impacto | Esfuerzo | Detalle |
|---|--------|---------|----------|---------|
| 1.1 | **Notificaciones de stock crítico** | 🔴 Alto | 🟢 Bajo | Cuando un suministro cruza el `stock_minimo`, enviar un email/alerta al responsable de compras. Hoy la alerta existe visual en el Dashboard, pero nadie se entera si no lo abre. Implementar vía Django signals en `MovimientoStock.post_save` + `django.core.mail`. |
| 1.2 | **Búsqueda global unificada** | 🟡 Medio | 🟡 Medio | Actualmente la búsqueda es por módulo (dispositivos tiene live search, suministros tiene filtro). Implementar un **Command Palette** (estilo `Ctrl+K`) con HTMX que busque en dispositivos, colaboradores y suministros simultáneamente. Un solo input, resultados agrupados. |
| 1.3 | **Audit log de acciones de usuario** | 🔴 Alto | 🟡 Medio | El `LOGGING` actual captura errores pero no _quién hizo qué_. Implementar un modelo `AuditLog` (app `core`) que registre: usuario, acción, modelo afectado, timestamp, IP. Middleware + decorador `@audit_action`. Crítico para cumplimiento legal dado que el sistema maneja actas. |
| 1.4 | **Validación de RUT chileno** | 🟡 Medio | 🟢 Bajo | El FODA lo identifica como deuda. Implementar un validador custom (`core/validators.py`) con algoritmo módulo 11 y aplicarlo en `Colaborador.rut`. Los RUTs inválidos en actas legales son un riesgo regulatorio. |
| ~~1.5~~ | ~~Exportación Excel de suministros~~ | — | — | ✅ **Ya implementado.** `SuministroResource` + `MovimientoStockResource` en `suministros/resources.py`. Vistas: `suministro_export_excel`, `suministro_movimientos_export_excel`. Tests incluidos. |

---

## Horizonte 2: Productividad del Usuario (1-2 meses)
> _"Funcionalidades que multiplican la velocidad del trabajo diario."_

| # | Mejora | Impacto | Esfuerzo | Detalle |
|---|--------|---------|----------|---------|
| 2.1 | **Flujo de Solicitud de Equipo (Workflow)** | 🔴 Alto | 🔴 Alto | Hoy un colaborador pide un equipo por correo/Teams. Digitalizar esto: un colaborador solicita → su jefatura aprueba → TI asigna. Estados: `Solicitado → Aprobado → Asignado / Rechazado`. Nuevo modelo `SolicitudEquipo` con FK a `Colaborador` y `TipoDispositivo`. Integra con el flujo de trazabilidad existente. |
| 2.2 | **Escaneo QR con cámara del celular** | 🟡 Medio | 🟡 Medio | Los QR ya se generan (`dispositivos/qr/`). Falta un **lector web** que use la cámara del dispositivo. Librería `html5-qrcode` (JS) + vista responsive que al escanear redirija al detalle del dispositivo. Ideal para inventarios físicos en terreno. |
| 2.3 | **Inventario Físico (Conciliación)** | 🔴 Alto | 🔴 Alto | Proceso formal de "contar lo que hay vs lo que dice el sistema". Crear un módulo `inventario_fisico` con: sesión de conteo, escaneo QR masivo, reporte de discrepancias (equipo faltante, equipo sobrante, ubicación incorrecta). Esto es un requerimiento típico de auditoría anual. |
| 2.4 | **Calendario de mantenimientos programados** | 🟡 Medio | 🟡 Medio | `BitacoraMantenimiento` registra mantenimientos pasados. Extender con `MantenimientoProgramado` (próxima fecha, tipo, frecuencia). Dashboard muestra equipos con mantenimiento vencido. Alerta por email X días antes. |
| 2.5 | **Reportes PDF automatizados** | 🟡 Medio | 🟡 Medio | Generar un reporte mensual automático: resumen de movimientos, equipos que entraron/salieron, suministros consumidos, costos. Usando el mismo pipeline de Playwright PDF que ya existe para actas. Configurable vía `django-constance`. |
| 2.6 | **Dashboard: Widget de alertas consolidadas** | 🟡 Medio | 🟢 Bajo | Un panel "Requiere Atención" en el Dashboard que consolide: equipos sin asignar hace >30 días, mantenimientos vencidos, suministros bajo stock, actas sin firmar hace >7 días. Un solo vistazo con links directos a la acción. |
| 2.7 | **Importación masiva de suministros** | 🟡 Medio | 🟢 Bajo | `import_devices` ya existe para dispositivos vía CSV. Replicar con `import_suministros` para carga inicial de catálogo de insumos con categorías, modelos compatibles y stock inicial. |

---

## Horizonte 3: Inteligencia y Automatización (3-4 meses)
> _"El sistema empieza a pensar por ti."_

| # | Mejora | Impacto | Esfuerzo | Detalle |
|---|--------|---------|----------|---------|
| 3.1 | **Predicción de reposición de suministros** | 🔴 Alto | 🔴 Alto | Usar el historial de `MovimientoStock` para calcular la tasa de consumo promedio por suministro y predecir la fecha en que el stock llegará a cero. Algoritmo: media móvil ponderada de los últimos N movimientos de salida. Sin ML, solo estadística descriptiva. Mostrar en Dashboard: "Toner X se agota en ~15 días". |
| 3.2 | **Depreciación automática de activos** | 🟡 Medio | 🟡 Medio | Calcular la depreciación lineal de cada dispositivo según su `valor_contable`, `fecha_compra` y vida útil estándar (configurable por `TipoDispositivo`). Nuevo campo calculado `valor_libro_actual`. Reporte de activos por depreciar y valor total del inventario actualizado. Relevante para contabilidad. |
| 3.3 | **Costo Total de Propiedad (TCO)** | 🟡 Medio | 🟡 Medio | Sumar para cada dispositivo: precio de compra + costos de mantenimiento (`BitacoraMantenimiento.costo_reparacion`) + suministros consumidos (`MovimientoStock` con `dispositivo_destino`). Dashboard card: "Top 10 equipos más caros de operar". Permite tomar decisiones de reemplazo informadas. |
| 3.4 | **Integración con Entra ID (Azure AD)** | 🟡 Medio | 🔴 Alto | El modelo `Colaborador` ya tiene `azure_id`. Implementar sincronización unidireccional: Azure AD → sistema. Cuando un colaborador se desactiva en el directorio corporativo, desactivarlo automáticamente aquí. Usar la Graph API de Microsoft con un management command programado (`cron`/`celery-beat`). |
| 3.5 | **Etiquetas y agrupaciones custom** | 🟢 Bajo | 🟡 Medio | Sistema de tags libre para dispositivos y suministros (ej: "Proyecto Minera X", "Equipo Crítico", "En préstamo temporal"). Modelo `Tag` M2M. Permite filtrar y agrupar en el Dashboard sin depender de campos fijos. |
| 3.6 | **API REST para integraciones** | 🟡 Medio | 🟡 Medio | Exponer endpoints read-only con Django REST Framework (o Django Ninja) para que sistemas externos consulten inventario: ERP, sistema contable, helpdesk. Autenticación vía Token. Documentación auto-generada con OpenAPI/Swagger. |

---

## Horizonte 4: Escala y Rendimiento (6+ meses)
> _"Preparar el sistema para crecer sin dolor."_

| # | Mejora | Impacto | Esfuerzo | Detalle |
|---|--------|---------|----------|---------|
| 4.1 | **Migración a PostgreSQL** | 🔴 Alto | 🟡 Medio | SQLite no soporta escrituras concurrentes. Con múltiples usuarios en UAT, esto será el primer cuello de botella. PostgreSQL habilita: `select_for_update()` (race conditions en folios/IDs), índices parciales, full-text search nativo, y `LISTEN/NOTIFY` para notificaciones en tiempo real. La migración es relativamente directa porque Django abstrae el backend. |
| 4.2 | **Caché de dashboard con Redis** | 🟡 Medio | 🟡 Medio | Las queries del Dashboard Estratégico (aggregations + charts) se ejecutan en cada request. Implementar cache por usuario/rol con TTL de 5 minutos usando `django.core.cache` + Redis. Invalidar selectivamente al registrar movimientos. |
| 4.3 | **Build de Tailwind CSS** | 🟡 Medio | 🟢 Bajo | Actualmente se usa el CDN de Tailwind (~200KB+, sin tree-shaking). Configurar `tailwindcss` CLI con PostCSS para generar un CSS optimizado (~15-30KB). Mejora significativa en tiempo de carga. Integrar en el flujo Docker existente. |
| 4.4 | **Background jobs con Celery/django-q2** | 🟡 Medio | 🟡 Medio | Generación de PDFs de actas, envío de emails de alerta, y reportes pesados deberían ejecutarse en background. Evita timeouts y mejora la UX. `django-q2` es más simple que Celery para este scale. |
| 4.5 | **Multi-sede / Multi-bodega** | 🔴 Alto | 🔴 Alto | Si JMIE opera en varias obras o sedes, el inventario necesita saber _dónde_ está cada equipo físicamente. Modelo `Ubicacion` (Sede + Bodega). Filtros de Dashboard por ubicación. Transferencias entre bodegas como un tipo de movimiento nuevo. |
| 4.6 | **CI/CD Pipeline** | 🟡 Medio | 🟡 Medio | No hay pipeline automatizado. Configurar GitHub Actions: `pytest` → `ruff` lint → `safety` check → build Docker → deploy a staging. Bloquear merge a `main` sin tests pasando. |

---

## Horizonte 5: Experiencia Premium (Ongoing)
> _"Detalles que transforman una herramienta en un producto."_

| # | Mejora | Impacto | Esfuerzo | Detalle |
|---|--------|---------|----------|---------|
| 5.1 | **Modo oscuro** | 🟢 Bajo | 🟢 Bajo | El design system JMIE ya tiene una paleta sólida. Agregar `prefers-color-scheme: dark` con toggle manual. Almacenar preferencia en `localStorage`. |
| 5.2 | **PWA (Progressive Web App)** | 🟡 Medio | 🟡 Medio | Manifest + Service Worker básico para que el sistema se pueda "instalar" en el escritorio/celular. Offline-first no es necesario, pero el acceso rápido sin abrir Chrome sí mejora la adopción. |
| 5.3 | **Firma digital en tablet** | 🔴 Alto | 🔴 Alto | Reemplazar la firma en papel por un canvas de firma digital (`signature_pad.js`). Capturar la firma como imagen PNG y adjuntarla al PDF del acta automáticamente. Reduce el ciclo de firma de días (imprimir → firmar → escanear → subir) a segundos. |
| 5.4 | **Onboarding interactivo** | 🟢 Bajo | 🟡 Medio | Tour guiado para nuevos usuarios usando `intro.js` o `driver.js`. Muestra las funciones clave del sistema la primera vez que inician sesión. Reduce la curva de aprendizaje y las consultas al equipo TI. |
| 5.5 | **Shortcuts de teclado** | 🟢 Bajo | 🟢 Bajo | `Ctrl+K` → búsqueda global, `N` → nuevo dispositivo, `S` → nuevo suministro. Alpine.js `@keydown.window` para capturar. Acelera a usuarios power. |
| 5.6 | **Internacionalización (i18n)** | 🟢 Bajo | 🟡 Medio | El sistema está en español chileno (`es-cl`). Si JMIE expande operaciones a otro país, el framework de i18n de Django ya está habilitado (`USE_I18N = True`). Solo falta marcar strings con `{% trans %}` y generar archivos `.po`. |

---

## Deuda Técnica Pendiente (del FODA)

Estas no son funcionalidades nuevas, sino correcciones identificadas en auditorías previas que deben atenderse en paralelo:

| Prioridad | Deuda | Estado |
|-----------|-------|--------|
| ~~P0~~ | ~~Parsear DEBUG y validar SECRET_KEY~~ | ✅ Resuelto |
| ~~P0~~ | ~~Parametrizar ALLOWED_HOSTS~~ | ✅ Resuelto |
| ~~P0~~ | ~~Eliminar `templates/colaboradores/` duplicado (shadow templates)~~ | ✅ No aplica — `templates/colaboradores/` es la ubicación canónica (no existe `colaboradores/templates/`). No hay shadow. |
| P1 | `dispatch_uid` en signals de dispositivos | ⏳ Pendiente |
| P1 | Manejo de `IntegrityError`/`ProtectedError` en deletes | ⏳ Pendiente |
| P2 | Consolidar 3 archivos de factories en 1 | ⏳ Pendiente |
| P2 | Aplicar marcadores `@pytest.mark.unit`/`integration` | ⏳ Pendiente |
| P2 | Reemplazar `unique_together` por `UniqueConstraint` en Modelo | ⏳ Pendiente |
| P3 | Eliminar `print()` statements en `dispositivo_update` | ⏳ Pendiente |
| P3 | Focus trapping en modales | ⏳ Pendiente |
| P3 | `prefers-reduced-motion` para animaciones | ⏳ Pendiente |

---

## Matriz de Priorización Visual

```
                    IMPACTO ALTO
                         │
    ┌────────────────────┼────────────────────┐
    │  3.1 Predicción    │ 1.1 Notificaciones │
    │  2.1 Solicitudes   │ 1.3 Audit Log      │
    │  4.1 PostgreSQL    │ 1.4 Validar RUT    │
    │  2.3 Inv. Físico   │ 2.6 Widget Alertas  │
    │  4.5 Multi-sede    │ 2.7 Import Sumin.   │
    │  5.3 Firma Digital │                     │
ESFUERZO                 │                ESFUERZO
ALTO ────────────────────┼──────────────── BAJO
    │  3.4 Entra ID      │ 4.3 Tailwind Build  │
    │  3.6 API REST      │ 5.1 Modo Oscuro     │
    │  4.4 Background    │ 5.5 Shortcuts       │
    │  4.6 CI/CD         │                     │
    │  5.2 PWA           │                     │
    │  5.4 Onboarding    │                     │
    └────────────────────┼────────────────────┘
                         │
                    IMPACTO BAJO
```

> **Quick Wins** (esquina inferior derecha): 1.1, 1.4, 2.6, 2.7, 4.3, 5.1, 5.5
> **Proyectos Estratégicos** (esquina superior izquierda): 2.1, 2.3, 4.1, 4.5, 5.3

---

## Recomendación de Ejecución

1. **Ahora (durante UAT):** Horizonte 1 completo + deuda P0/P1
2. **Post-UAT estable:** Horizonte 2 (pick 3-4 items de mayor valor)  
3. **Q3-Q4 2026:** Horizonte 3 + PostgreSQL (4.1)
4. **2027:** Horizontes 4-5 según necesidades del negocio

> [!IMPORTANT]  
> Este roadmap es un documento vivo. Priorizarlo junto con Katherine y el equipo según la retroalimentación del Piloto UAT.
