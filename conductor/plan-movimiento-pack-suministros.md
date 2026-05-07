# Plan de Implementación: Movimientos de Pack de Suministros

**Objetivo:** Permitir el registro masivo de movimientos de stock para suministros que forman un pack (ej: kits de toner CMYK) de forma atómica, manteniendo la trazabilidad por destinatario y validando stock en tiempo real.

## 1. Capa de Servicios (`suministros/services.py`)

- **`get_pack_siblings(suministro)`**: Método para encontrar suministros "hermanos" basados en el fingerprint de modelos compatibles (mismo conjunto exacto de IDs).
- **`registrar_movimiento_pack(datos_movimientos, registrado_by)`**: 
    - Recibe una lista de diccionarios `[{'suministro_id': ID, 'cantidad': N, ...}]`.
    - Utiliza `transaction.atomic` y `select_for_update` para garantizar integridad.
    - Reutiliza la lógica de alertas de consumo inusual ya existente.

## 2. Capa de Vistas (`suministros/views.py`)

- **`movimiento_pack_create`**: 
    - **GET**: Renderiza `partials/movimiento_pack_modal.html`. Puede recibir `ids[]` por query string.
    - **POST**: Procesa el formulario múltiple.
- **`ajax_get_pack_siblings`**: Endpoint para que el modal individual pueda "expandirse" a un pack dinámicamente.

## 3. UI y Templates

### Listado de Suministros
- Modificar `suministro_list_results.html` para añadir checkboxes en cada fila.
- Modificar `suministro_list.html` para añadir un botón de "Movimiento Pack" que se habilita mediante Alpine.js al seleccionar ítems.
- El botón disparará `hx-get` a `movimiento_pack_create` pasando los IDs seleccionados.

### Modal de Pack (`partials/movimiento_pack_modal.html`)
- **Sección Superior:** Datos comunes (Tipo, Destinatario, CC, Dispositivo).
- **Sección Tabla:** Lista de suministros con Alpine.js para:
    - Control de cantidades individuales.
    - Validación inmediata contra `stock_actual`.
    - Cálculo de estado (habilitar/deshabilitar botón de Confirmar).
- **Integración con Modal Individual:** Añadir botón "Cargar Pack Completo" en `movimiento_modal.html` que redirija al modal de pack.

## 4. Verificación y Pruebas

- **Pruebas Unitarias:**
    - Verificar que `get_pack_siblings` identifique correctamente a los hermanos CMYK.
    - Verificar atomicidad: si un movimiento falla (ej: stock insuficiente), ninguno debe registrarse.
- **Pruebas E2E:**
    - Flujo completo: Seleccionar 4 toners -> Registrar Salida a Colaborador -> Verificar 4 movimientos en el historial.

## 5. Componentes Cotton a Reutilizar
- `c-page-header` para el modal.
- `c-btn-primary` para la confirmación.
- `c-form-label` para los campos comunes.

---
**Gemini:** Una vez aprobado este plan, procederé con la creación del Service y la Vista.