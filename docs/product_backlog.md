# 📋 Product Backlog — Sistema de Inventario JMIE

> [!NOTE]
> Este documento es la **fuente de verdad** del backlog completo. Cada historia de usuario incluye sus criterios de aceptación (negocio) y directrices técnicas (implementación). Trabajamos en base a esto.

---

## Épica 1: Catálogos y Parametría (Las Bases)

**Scope:** Datos estáticos que alimentan selectores y listas desplegables. Sin estos, nada funciona.

---

### HU-01: Gestión de Tipos de Dispositivos

**Como** Administrador, **quiero** registrar Tipos de Dispositivos (Notebook, Impresora), **para** clasificar el inventario.

**Criterios de Aceptación:**

1. **Creación:** El sistema debe permitir ingresar un nombre para el nuevo tipo.
2. **Unicidad:** Error si se intenta crear un tipo que ya existe.
3. **Edición:** Se puede modificar el nombre de un tipo existente.
4. **Protección de Integridad:** Si un Tipo ya tiene equipos asociados, no se puede eliminar.

**Directrices Técnicas:**

- FK desde `Dispositivo` → `TipoDispositivo` con `on_delete=models.PROTECT`.
- CRUD vía modal Alpine.js (`x-data="{ modalAbierto: false }"`), formulario cargado con `hx-get`, enviado con `hx-post`.
- Éxito: nueva fila `<tr>` + `hx-swap-oob="true"` para notificación + `HX-Trigger` para cerrar modal.

---

### HU-02: Gestión de Fabricantes y Modelos

**Como** Administrador, **quiero** gestionar un catálogo de Fabricantes y Modelos, **para** evitar errores de escritura al ingresar equipos.

**Criterios de Aceptación:**

1. **Registro Base:** Fabricantes se registran independientemente (ej. "Lenovo", "Dell").
2. **Dependencia Lógica:** Un Modelo requiere asociarse a un Fabricante existente.
3. **Listado Anidado:** Los modelos deben poder filtrarse por fabricante.

**Directrices Técnicas:**

- Vista de Modelos con `select_related('fabricante')` obligatorio.
- Misma mecánica modal HTMX + Alpine.

---

### HU-03: Gestión de Centros de Costo

**Como** Administrador, **quiero** registrar los Centros de Costo, **para** asociar el equipamiento a la estructura contable correcta.

**Criterios de Aceptación:**

1. **Campos Obligatorios:** Nombre descriptivo + Código Contable alfanumérico.
2. **Código Único:** Dos centros de costo no comparten código contable.
3. **Baja Lógica Contable:** Al cerrarse un centro, se marca "Inactivo" (no se borra). Ya no aparece en selectores nuevos, pero se mantiene en historiales.

**Directrices Técnicas:**

- `CentroCosto.codigo_contable` con `unique=True`.
- Campo `activa = BooleanField(default=True)`.
- QuerySets de selectores filtran `activa=True`.

---

### HU-04: Definición de Estados de Inventario

**Como** Administrador, **quiero** definir los Estados (Disponible, Asignado, Reparación, Baja), **para** estandarizar el ciclo de vida del hardware.

**Criterios de Aceptación:**

1. **Carga Inicial:** Viene precargado con: Disponible, Asignado, En Reparación, De Baja.
2. **Flexibilidad:** Se pueden agregar estados nuevos (ej. "En Tránsito").
3. **Restricción de Borrado:** No se puede eliminar un Estado si hay equipos en ese estado.

**Directrices Técnicas:**

- `on_delete=models.PROTECT`.
- Data migration o fixture para la carga inicial de estados.

---

## Épica 2: Directorio de Colaboradores (Padrón Único)

**Scope:** Las personas que interactúan con los equipos. Modelo unificado con autenticación Django.

---

### HU-05: Registro de Colaborador Base

**Como** Administrador, **quiero** registrar a un nuevo Colaborador con sus datos básicos, **para** poder asignarle equipos.

**Criterios de Aceptación:**

1. **Campos Obligatorios:** RUT, Nombre, Apellido, Cargo, Departamento, Centro de Costo.
2. **Unicidad:** No se permiten dos colaboradores con el mismo RUT.
3. **Dependencia de Catálogos:** Departamento y Centro de Costo se eligen de listas desplegables (no escritura manual).

**Directrices Técnicas:**

- Modelo `Colaborador` hereda de `AbstractUser`.
- `rut` con `unique=True`. FKs a `Departamento` y `CentroCosto`.
- Declarar como `AUTH_USER_MODEL` en `settings.py`.

---

### HU-06: Identificador de Directorio Corporativo

**Como** Administrador, **quiero** incluir el ID del directorio corporativo (Entra ID), **para** futuras sincronizaciones.

**Criterios de Aceptación:**

1. **Flexibilidad:** El campo es opcional al crear el usuario.
2. **Integridad:** Si se llena, no puede repetirse con otro colaborador.

**Directrices Técnicas:**

- `azure_id = CharField(null=True, blank=True, unique=True)`.

---

### HU-07: Baja Lógica de Personal

**Como** Administrador, **quiero** desactivar a un Colaborador que deja la empresa, **para** conservar intacto el historial de equipos que usó.

**Criterios de Aceptación:**

1. **Protección de Borrado:** No hay botón "Eliminar permanentemente". Solo "Desactivar".
2. **Restricción Operativa:** Un colaborador Inactivo no aparece en las listas de asignación.
3. **Preservación Histórica:** Su nombre sigue apareciendo en Actas e historiales pasados.

**Directrices Técnicas:**

- Sobrescribir `delete()`: intercepta `DELETE` y ejecuta `UPDATE is_active = False`.
- OOB Swap: badge verde "Activo" → badge roja "Inactivo" sin recargar.
- Modal de confirmación con Alpine.js antes de la petición HTMX.

---

### HU-08: Perfil Detallado y Auditoría Rápida

**Como** Auditor, **quiero** ver el perfil de un Colaborador con todos los equipos a su cargo, **para** auditar rápidamente.

**Criterios de Aceptación:**

1. **Vista Unificada:** Encabezado con datos del trabajador + tabla de hardware asignado.
2. **Contadores:** Total numérico de equipos asignados visible.

**Directrices Técnicas:**

- `prefetch_related` al historial de asignaciones vigentes.

---

## Épica 3: Inventario Físico (El Corazón del Sistema)

**Scope:** Registro de hardware con herencia de modelos, formularios dinámicos, QR y búsqueda en vivo.

---

### HU-09: Registro Base e Identificador Único

**Como** Técnico, **quiero** registrar un nuevo equipo con un identificador interno único y un número de serie, **para** identificarlo individualmente.

**Criterios de Aceptación:**

1. **Campos Obligatorios:** Número de Serie de fábrica + Identificador Interno (ej. JMIE-0001).
2. **Unicidad estricta:** Error si el Identificador o Serie ya existe.

**Directrices Técnicas:**

- `numero_serie` e `identificador_interno` con `unique=True`.
- Herencia multi-tabla: `Dispositivo` como modelo padre.

---

### HU-10: Información Contable del Activo

**Como** Técnico, **quiero** registrar fecha de compra y valor contable, **para** auditoría financiera.

**Criterios de Aceptación:**

1. **Lógica de Fechas:** No se permite fecha de compra futura.
2. **Valor numérico:** Solo valores positivos.

**Directrices Técnicas:**

- `valor_contable`: `PositiveIntegerField` o `DecimalField(max_digits=12, decimal_places=2)`.
- Validación en `clean()` para fecha no futura.

---

### HU-11: Formularios Dinámicos por Categoría

**Como** Técnico, **quiero** que al seleccionar la categoría aparezcan campos específicos (ej. IMEI para Smartphone), **para** guardar detalle técnico sin saturar la pantalla.

**Criterios de Aceptación:**

1. **Adaptabilidad Visual:** Campos específicos aparecen instantáneamente al elegir tipo.
2. **Validación Condicional:** IMEI obligatorio para Smartphone; inexistente para Monitor.

**Directrices Técnicas:**

- Alpine.js: `x-data="{ tipoEquipo: '' }"` + `x-show="tipoEquipo === 'smartphone'"`.
- Sin viajes de red al cambiar selector.

---

### HU-12: Registro de Condición Física

**Como** Técnico, **quiero** un campo de texto obligatorio para registrar golpes/rayas/desgaste, **para** constancia legal.

**Criterios de Aceptación:**

1. **Obligatorio** al crear equipo nuevo y al reasignar.
2. **Impresión Legal:** Viaja automáticamente al PDF del Acta.

**Directrices Técnicas:**

- `notas_condicion = TextField()` en modelo `Dispositivo`.

---

### HU-13: Escaneo de Código QR Físico

**Como** Técnico, **quiero** escanear un QR pegado en el equipo, **para** abrir instantáneamente su hoja de vida.

**Criterios de Aceptación:**

1. **Redirección exacta:** El QR contiene la URL del equipo.
2. **Acceso al historial:** Muestra dueño actual, centro de costo, botón de historial.

**Directrices Técnicas:**

- QR = URL absoluta (`/dispositivos/<uuid>/`). Petición GET estándar.
- Librería `qrcode` para generación.

---

### HU-14: Búsqueda Rápida (Live Search)

**Como** Técnico, **quiero** una barra de búsqueda que filtre mientras escribo, **para** encontrar un equipo en segundos.

**Criterios de Aceptación:**

1. **Multibúsqueda:** Por Número de Serie o Identificador Interno.
2. **Filtro en vivo:** Resultados aparecen sin presionar botón ni recargar.

**Directrices Técnicas:**

- `hx-get` con `hx-trigger="keyup changed delay:300ms"` (debounce obligatorio).
- QuerySet con `select_related('centro_costo', 'estado', 'tipo')`.
- Retorna `{% partial %}` de la tabla.

---

### HU-15: Bitácora de Mantenimiento

**Como** Técnico, **quiero** registrar eventos de mantenimiento, **para** un histórico de reparaciones.

**Criterios de Aceptación:**

1. **Registro:** Fecha, falla reportada, reparación realizada. Vinculado al dispositivo.
2. **Cambio de Estado Automático:** Al enviar a servicio técnico → "En Reparación".

---

## Épica 4: Trazabilidad y Asignaciones (Transacciones)

**Scope:** Movimientos de equipos entre bodega y colaboradores. Núcleo transaccional con ledger inmutable.

---

### HU-16: Asignación de Bodega a Colaborador

**Como** Administrador, **quiero** asignar un equipo de bodega a un Colaborador.

**Criterios de Aceptación:**

1. **Validación:** Solo equipos en estado "Disponible".
2. **Cambio Automático:** Estado → "Asignado" + fecha actual.
3. **Condición Física:** Obligatorio actualizar/confirmar notas de condición.

**Directrices Técnicas:**

- `transaction.atomic()` obligatorio.
- OOB Swaps: tabla de equipos + contador + lista de bodega.
- `hx-disabled-elt="this"` para bloqueo de doble envío.

---

### HU-17: Reasignación Directa entre Colaboradores

**Como** Administrador, **quiero** reasignar un equipo directamente de un Colaborador a otro.

**Criterios de Aceptación:**

1. **Cierre de Ciclo:** Fecha de fin automática al colaborador anterior.
2. **Apertura de Ciclo:** Nuevo registro de asignación con fecha de inicio.
3. **Flujo Continuo:** Un solo paso, sin devolver manualmente a bodega.

**Directrices Técnicas:**

- `transaction.atomic()`: cerrar historial previo + crear nuevo + actualizar dispositivo.

---

### HU-18: Devolución a Bodega

**Como** Administrador, **quiero** devolver un equipo a bodega.

**Criterios de Aceptación:**

1. **Liberación:** Registra fecha de devolución, propietario → "Ninguno/Bodega".
2. **Estado:** Vuelve a "Disponible", o "En Reparación" si vuelve dañado.

---

### HU-19: Auditoría del Historial de Movimientos

**Como** Auditor, **quiero** ver el historial completo de movimientos de un equipo.

**Criterios de Aceptación:**

1. **Inmutabilidad:** Registros cronológicos que no se pueden editar ni eliminar.
2. **Accesibilidad:** Visible desde el perfil del equipo, a un clic.

**Directrices Técnicas:**

- Tablas `HistorialAsignacion` y `EntregaAccesorios` → **Append-Only (Ledger)**.
- Prohibido implementar `delete()` en vistas de estas tablas.
- `select_related('colaborador', 'dispositivo')` obligatorio.

---

### HU-20: Entrega Masiva de Accesorios

**Como** Administrador, **quiero** registrar entrega masiva de accesorios (mouses, mochilas).

**Criterios de Aceptación:**

1. **Descuento de Stock:** Resta automática del stock disponible.
2. **Registro Simplificado:** Sin número de serie. Solo tipo, cantidad, colaborador.

**Directrices Técnicas:**

- Modal Alpine.js para selección de cantidades.
- Llamada de red solo al confirmar.

---

## Épica 5: Documentos y Actas (Respaldo Legal)

**Scope:** Generación de PDFs legales, folios únicos, blindaje de registros firmados.

---

### HU-21: Consolidación de Asignaciones

**Como** Administrador, **quiero** agrupar asignaciones recientes en un solo registro de Acta.

**Criterios de Aceptación:**

1. **Filtro de Vigencia:** Solo equipos actualmente asignados y no incluidos en Acta anterior.
2. **Folio Único:** Autogenerado correlativo (ej. ACT-2026-001).

**Directrices Técnicas:**

- Sobrescribir `save()` del modelo `Acta` para generar folio pre-INSERT.

---

### HU-22: Generación Automática de PDF

**Como** Administrador, **quiero** generar un PDF del Acta automáticamente.

**Criterios de Aceptación:**

1. **Formato Corporativo:** Logo, fecha, datos completos del colaborador.
2. **Detalle del Equipo:** Identificador Interno, Serie, Tipo, Marca, Modelo.

**Directrices Técnicas:**

- `xhtml2pdf` para renderizado.
- Botón como `<a href="..." target="_blank">` (NO usar hx-get para binarios).
- QuerySet con `select_related` + `prefetch_related` intensivo.

---

### HU-23: Cláusula de Condición Física

**Como** Administrador, **quiero** que el PDF incluya las notas de condición física.

**Criterios de Aceptación:**

1. **Transparencia:** Texto exacto del campo "Condición Física" debajo de cada equipo.
2. **Firmas:** Dos espacios: "Entregué Conforme (TI)" y "Recibí Conforme (Colaborador)".

---

### HU-24: Cierre del Ciclo Legal

**Como** Auditor, **quiero** marcar un Acta como "Firmada/Archivada".

**Criterios de Aceptación:**

1. **Cambio de Estado:** "Generada" → "Firmada/Archivada".
2. **Protección de Edición:** Una vez firmada, no se pueden modificar los equipos del Acta.

**Directrices Técnicas:**

- `ValidationError` si `firmada=True` y se intenta mutar.
- `hx-post` + `X-CSRFToken` para el cambio de estado.
- Modal Alpine.js de confirmación irreversible.

---

## Épica 6: Dashboard y Analítica (Centro de Mando)

**Scope:** Visibilidad en tiempo real de la salud del inventario. Gráficos y contadores dinámicos.

---

### HU-25: Métricas Clave

**Como** Administrador, **quiero** ver contadores en tiempo real al iniciar sesión (Disponibles, Asignados, En Reparación, De Baja), **para** conocer la salud general del inventario.

**Criterios de Aceptación:**

1. **Panel principal:** Contadores visibles en el dashboard, al iniciar sesión.
2. **Datos reales:** Los contadores deben reflejar exclusivamente la realidad operativa actual. Es obligatorio que las consultas excluyan los registros con baja lógica (ej. filtrando por `esta_activo=True` o excluyendo el estado "De Baja") para no inflar artificialmente las métricas.

**Directrices Técnicas:**

- Carga asíncrona con `hx-get` + `hx-trigger="load"`.
- Polling opcional: `hx-trigger="every 30s"` para mantener datos frescos.
- QuerySet con `.values('estado__nombre').annotate(Count('id'))`.

---

### HU-26: Gráficos Dinámicos

**Como** Administrador, **quiero** visualizar un gráfico de distribución por Centro de Costo o Departamento, **para** identificar qué áreas concentran más inversión.

**Criterios de Aceptación:**

1. **Gráfico visual:** Distribución clara por centro de costo/departamento.
2. **Interactivo:** Se puede cambiar entre vistas (por CC o por Departamento).

**Directrices Técnicas:**

- Chart.js inicializado desde Alpine.js (`x-data`) para mantener Localidad del Comportamiento.
- Datos del gráfico cargados vía `hx-get` como JSON o fragmento HTML con data-attributes.

---

## Épica 7: Seguridad y Control de Accesos

**Scope:** Autenticación, roles granulares y protección de vistas. Operativo incluso en red interna.

---

### HU-27: Autenticación

**Como** Usuario del sistema, **quiero** ingresar con una pantalla de Login seguro, **para** que se registre mi identidad en cada movimiento.

**Criterios de Aceptación:**

1. **Login obligatorio:** Sin credenciales válidas, no se accede a nada.
2. **Registro de identidad:** Cada acción queda vinculada al usuario autenticado.

**Directrices Técnicas:**

- `django.contrib.auth` nativo para sesiones y cifrado de contraseñas.
- `@login_required` (funciones) / `LoginRequiredMixin` (clases) en TODAS las vistas.

---

### HU-28: Roles Granulares

**Como** Administrador de TI, **quiero** asignar roles específicos ("Técnico", "Administrador", "Auditor"), **para** delimitar responsabilidades.

**Criterios de Aceptación:**
**Matriz de Permisos:**

| Capacidad                                                          | Técnico | Administrador  | Auditor      |
| ------------------------------------------------------------------ | -------- | -------------- | ------------ |
| Crear/editar equipos (`add_dispositivo`, `change_dispositivo`) | ✅       | ✅             | ❌           |
| Registrar mantenimiento                                            | ✅       | ✅             | ❌           |
| Ver inventario                                                     | ✅       | ✅             | ✅           |
| Asignar/reasignar equipos                                          | ❌       | ✅             | ❌           |
| Generar actas/PDF                                                  | ❌       | ✅             | ❌           |
| Baja lógica de equipos y personal                                 | ❌       | ✅ (exclusivo) | ❌           |
| Ver Dashboard, historiales, perfiles                               | ✅       | ✅             | ✅           |
| Botones de acción mutacional (POST/PUT/DELETE)                    | Limitado | ✅             | ❌ (ocultos) |

**Directrices Técnicas:**

- Grupos de Django: `Administradores`, `Técnicos`, `Lectura/Auditoría`.
- `PermissionRequiredMixin` en vistas mutacionales.
- Auditor = **solo lectura estricta**. Ningún botón de acción mutacional (POST, PUT, DELETE) debe ser visible ni accesible para este rol. Se ocultan en plantillas con `{% if perms.app.permiso %}`.

---

## Resumen del Backlog

| Épica           | Scope               | Historias      | Prioridad            |
| ---------------- | ------------------- | -------------- | -------------------- |
| 1. Catálogos    | Las bases           | HU-01 → HU-04 | 🔴 Release 1         |
| 2. Colaboradores | Padrón de personas | HU-05 → HU-08 | 🔴 Release 1         |
| 3. Inventario    | Hardware + detalles | HU-09 → HU-15 | 🔴 Release 1         |
| 4. Trazabilidad  | Asignaciones        | HU-16 → HU-20 | 🔴 Release 1         |
| 5. Actas/PDF     | Respaldo legal      | HU-21 → HU-24 | 🔴 Release 1         |
| 6. Dashboard     | Centro de mando     | HU-25 → HU-26 | 🟡 Release 1 (final) |
| 7. Seguridad     | Login + roles       | HU-27 → HU-28 | 🔴 Release 1         |

> **Total: 7 Épicas, 28 Historias de Usuario.**
