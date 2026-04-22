# Análisis FODA - Inventario JMIE

> Fecha: 17 de abril 2026
> Proyecto: Sistema de Inventario JMIE (Django 6.0.2 + HTMX + Alpine.js)

---

## FORTALEZAS (Internas)

### Arquitectura y Código
- **Service Layer bien implementado** en `actas/services.py` con transacciones atómicas, validación y prevención N+1
- **Prevención de N+1 consistente** con `select_related`/`prefetch_related` en views y servicios
- **Custom QuerySet** con métodos `activos()` y `con_detalles()` en `dispositivos/models.py`
- **Herencia multi-tabla** para dispositivos (Notebook, Smartphone, etc.) con auto-generación de IDs (`JMIE-SIGLA-NNNNN`)
- **Señales de auto-asignación** que cierran registros anteriores automáticamente
- **Patrón ledger append-only** en `HistorialAsignacion` y `EntregaAccesorio`
- **Bloqueo de actas firmadas** que impide modificaciones post-firma

### Testing
- **3 capas de testing**: unitarios, integración y E2E con Playwright
- **Factory-boy** con cadenas de SubFactory para datos de prueba
- **Signals bien testeados** incluyendo casos límite (cambio de dueño, subclases)
- **ActaService bien cubierto** con 7 tests incluyendo generación de PDF

### Frontend
- **HTMX + Alpine.js** con arquitectura sofisticada: eventos custom, self-healing modals, búsqueda debounced
- **Sistema de diseño cohesivo** con paleta JMIE, glassmorphism, tipografía Montserrat
- **Chart.js drill-down** interactivo que filtra dispositivos al hacer clic
- **Accesibilidad base**: ARIA labels, roles, sr-only, navegación por teclado

### Seguridad
- **Permisos granulares**: todos los views usan `@login_required` + `@permission_required`
- **Modelo de usuario custom** desde el inicio (`colaboradores.Colaborador`)
- **4 validadores de contraseña** configurados
- **Sin SQL raw ni mark_safe** -- buena protección contra inyección

---

## DEBILIDADES (Internas)

### Críticas
- **Templates duplicados**: `templates/colaboradores/` sombrea `colaboradores/templates/colaboradores/` con versiones desactualizadas
- **SECRET_KEY sin validación explícita**: si falta en entorno, el arranque puede fallar
- **`ALLOWED_HOSTS = ['*']`** -- vulnerabilidad a host header poisoning
- **`DEBUG` depende de variable sin parseo booleano** -- riesgo de configuración ambigua

### Altas
- **Service layer ausente** en `dashboard`, `core`, `colaboradores`. `dispositivos` tiene factory pero no service para operaciones de negocio
- **Views sin transacciones**: `dispositivo_create` y `dispositivo_update` no usan `@transaction.atomic` pese a escribir multi-tabla
- **Sin manejo de errores** en deletes (`dispositivo_delete`, `colaborador_delete`) -- IntegrityError no capturado
- **Sin logging configurado** -- no hay auditoría de eventos de seguridad
- **Race conditions** en generación de `identificador_interno` y `folio` (read-then-write sin locking)

### Medias
- **Marcadores pytest sin usar**: `@pytest.mark.unit` e `@pytest.mark.integration` definidos pero nunca aplicados
- **3 archivos de factories duplicados** con defaults inconsistentes
- **Cobertura de views baja**: ~10 de ~25+ views testeadas. CRUD de dispositivos, QR, Excel export sin tests
- **Sin tests de dispositivos especializados**: Notebook, Smartphone, Monitor, etc. sin tests
- **Código duplicado en `core/views.py`**: CRUD de 5 entidades es copy-paste (~150 líneas repetidas)
- **Print statements en producción** en `dispositivo_update` (líneas 433-434)
- **Tailwind CDN en producción** -- JIT compiler en runtime (~200KB+, sin tree-shaking)
- **Sin `dispatch_uid` en signals** -- riesgo de receivers duplicados
- **Sin validadores**: RUT, formato IMEI, MAC address, color hex

### Bajas
- **Sin `TemplateResponse`** pese a ser recomendado para HTMX
- **Sin `ordering` en Meta** de varios modelos
- **`unique_together` deprecated** en `Modelo` (debería usar `UniqueConstraint`)
- **Sin focus trapping** en modales
- **Sin `prefers-reduced-motion`** para animaciones

---

## OPORTUNIDADES (Externas)

### Mejoras Técnicas
- **Migrar a PostgreSQL**: SQLite limita concurrencia. PostgreSQL permitiría `select_for_update()` para race conditions, índices parciales, full-text search
- **Build step de Tailwind**: Reemplazar CDN con PostCSS + Tailwind CLI para producción (tree-shaking, menor payload)
- **Implementar logging**: Auditoría de seguridad con `LOGGING` dict config -- crítico para sistema con actas legales
- **Rate limiting en login**: Prevenir brute-force con django-ratelimit o similar
- **Consolidar factories**: Un solo `core/tests/factories.py` eliminaría duplicación y inconsistencias
- **Generic views**: Reemplazar CRUD copy-paste con CBVs genéricos o mixins reutilizables
- **Agregar `dispatch_uid`** a signals para prevenir duplicación

### Testing
- **Expandir E2E**: Cubrir CRUD de dispositivos, flujo de mantenimiento, búsqueda/filtros
- **Tests de permisos**: Verificar que usuarios no autorizados reciben 403
- **Tests de formularios**: Validación de DispositivoForm, AsignacionForm, DevolucionForm
- **Tests de casos límite**: dataset vacío, caracteres especiales, paginación, actas DEVOLUCION

### Producto
- **Exportación Excel** ya implementada vía django-import-export -- se puede expandir a otros módulos
- **QR codes** generados -- se pueden usar para escaneo rápido en inventario físico
- **MCP server** integrado -- abre puerta a integración con IA/agentes
- **NIST sanitization** -- cumplimiento normativo que puede ser diferenciador

---

## AMENAZAS (Externas)

### Seguridad
- **SECRET_KEY expuesta en VCS**: Si el repo se hace público, se pueden forjar sesiones, bypass CSRF, generar password reset tokens
- **Host header poisoning**: `ALLOWED_HOSTS = ['*']` permite manipular links de password reset y redirects
- **Brute-force en login**: Sin rate limiting ni account lockout
- **Cookies sin Secure flag**: `SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE` en `False` -- vulnerables en HTTP
- **Sin HSTS**: No hay HTTP Strict Transport Security

### Mantenimiento
- **Templates desactualizados**: Los templates root de colaboradores se usan en vez de los correctos del app -- bugs silenciosos
- **Tailwind CDN**: Si el CDN cambia o se cae, el sitio pierde estilos completamente
- **Sin CI/CD**: No hay pipeline automatizado de linting, tests, security scans

### Escalabilidad
- **SQLite**: No soporta escrituras concurrentes -- se degradará con múltiples usuarios
- **Sin caching**: dashboard queries se ejecutan en cada request sin caché
- **Sin paginación en algunas listas**: Podría degradar con miles de dispositivos
- **Signals en cada save**: Dispositivo signals se ejecutan en CADA save, no solo cuando cambia `propietario_actual`

### Regulatorio
- **Actas legales sin auditoría completa**: Sin logging de quién firmó, cuándo, ni trazabilidad de cambios
- **RUT sin validación**: Podrían ingresarse RUTs inválidos en documentos legales
- **Sin backup automatizado**: SQLite file sin estrategia de backup

---

## Resumen Priorizado

| Prioridad | Acción | Impacto |
|-----------|--------|---------|
| **P0** | Parsear `DEBUG` y validar `SECRET_KEY` al inicio | Seguridad y estabilidad |
| **P0** | Parametrizar `ALLOWED_HOSTS` por entorno | Seguridad crítica |
| **P0** | Eliminar `templates/colaboradores/` duplicado | Bugs silenciosos |
| **P1** | Agregar `@transaction.atomic` a dispositivo_create/update | Integridad de datos |
| **P1** | Configurar logging de seguridad | Auditoría |
| **P1** | Agregar `dispatch_uid` a signals | Prevención duplicación |
| **P1** | Manejo de errores en deletes | UX y estabilidad |
| **P2** | Consolidar factories | Mantenibilidad tests |
| **P2** | Agregar marcadores pytest unit/integration | Organización tests |
| **P2** | Validador de RUT | Integridad datos legales |
| **P2** | Service layer para dispositivos | Separación de responsabilidades |
| **P3** | Migrar a PostgreSQL | Escalabilidad |
| **P3** | Build step Tailwind | Performance |
| **P3** | Expandir cobertura de tests | Calidad |
