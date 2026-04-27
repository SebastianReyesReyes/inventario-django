# Plan de Implementación: Refactorización Core y App Suministros

Este plan detalla los pasos para reestructurar la base de datos (aprovechando que se borrará y empezará desde cero) y crear el nuevo módulo de `suministros`.

## User Review Required

> [!WARNING]
> **Reinicio de Base de Datos:**
> Este plan asume que eliminaremos la base de datos actual (`db.sqlite3`) y todas las carpetas `migrations` de las apps existentes para generar un estado inicial limpio. Esto evitará problemas de datos heredados y nos dará una arquitectura perfectamente normalizada.

## Proposed Changes

### 1. Limpieza Inicial y Reestructuración Core

- **Eliminar** `db.sqlite3` y el historial de migraciones de `core`, `dispositivos`, `actas` y `dashboard`.
- **`core/models.py`:**
  - Añadir el campo `descripcion` (opcional) al modelo `TipoDispositivo`.
  - Mover la relación de tipo al modelo: `Modelo` tendrá un `ForeignKey` a `TipoDispositivo`.
  - Ajustar el método `__str__` de `Modelo` para que no repita la marca si no es necesario (o lo manejaremos en la vista).
- **`dispositivos/models.py`:**
  - Eliminar el campo `tipo` de `Dispositivo`.
  - Actualizar la lógica de generación de ID (ej. `JMIE-SIGLA-0001`) para que lea `self.modelo.tipo_dispositivo.sigla`.
- **Vistas y Formularios (Core/Dispositivos):**
  - Ajustar formularios para no pedir el tipo al crear un dispositivo.
  - Actualizar los queries (`select_related`) para apuntar a `modelo__tipo_dispositivo`.

### 2. Creación de la App `suministros`

- Ejecutar `python manage.py startapp suministros`.
- **Modelos a crear (`suministros/models.py`):**
  1. `CategoriaSuministro`: `nombre`, `descripcion`.
  2. `Suministro`: `nombre`, `categoria` (FK), `modelos_compatibles` (M2M con `core.Modelo`), `es_alternativo` (Boolean), `umbral_minimo` (Integer, default 2), `stock_actual` (Integer, default 0).
  3. `EntradaSuministro`: `suministro` (FK), `cantidad`, `precio_factura` (Decimal), `fecha_entrada`, `comprobante`.
  4. `SalidaSuministro`: `suministro` (FK), `cantidad`, `fecha_salida`, `motivo/destino`.
- **Lógica de Stock:**
  - Añadir señales (`signals.py`) o sobreescribir el método `save` en Entradas/Salidas para sumar o restar al `stock_actual` del `Suministro`.

### 3. Formularios y UI Reactiva (HTMX)

- **Creación de Suministro:**
  - Implementar un formulario donde al seleccionar la `CategoriaSuministro` (ej. "Tinta de Impresora"), se dispare una petición HTMX.
  - Esa petición filtrará el campo `modelos_compatibles` para que **solo** muestre modelos de impresoras, evitando que salgan modelos de notebooks.
- **Admin/UI:**
  - En la vista de creación de suministros, asegurar que la representación de los modelos compatibles sea limpia (ej. "T920DW" en vez de "Brother Brother MFC-T920DW").

### 4. Actualización de Tests

- Reescribir los `factories` en `tests/factories.py` para adaptarse a que `Modelo` ahora requiere un `TipoDispositivo`.
- Añadir tests para la nueva app `suministros` (asegurando que las entradas/salidas afectan el stock correctamente).

## Verification Plan

### Automated Tests
- Correr toda la suite de pruebas desde cero con la nueva base de datos.
- Tests unitarios para las señales de actualización de stock.

### Manual Verification
1. Generar la BD limpia y poblar catálogos iniciales.
2. Crear un Modelo (ej. "Impresora L3150").
3. Crear un Dispositivo asignándole solo ese Modelo, y ver que adopte el tipo "Impresora" y genere su ID correctamente.
4. Crear un Suministro (ej. "Tinta Alternativa 544"), probar el filtro HTMX de modelos compatibles y registrar una Entrada de Stock con precio de factura. Verificar que el stock se actualice.
