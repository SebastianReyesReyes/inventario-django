---
date: 2026-04-30
topic: "Protección y Anulación de Actas"
status: validated
---

# Protección y Anulación de Actas

## Problem Statement

El sistema de actas permite eliminar registros físicamente sin restricciones significativas (solo el blindaje de `save()` impide ediciones, pero `delete()` está desprotegido). Esto genera riesgos críticos:

1. **Pérdida de trazabilidad legal**: Los folios correlativos (`ACT-YYYY-XXXX`) quedan con huecos si se elimina un acta.
2. **Asignaciones huérfanas**: `HistorialAsignacion` y `EntregaAccesorio` quedan con `acta=NULL`, perdiendo el vínculo documental.
3. **Sin auditoría de firma**: No se registra quién firmó ni cuándo.
4. **Sin mecanismo de corrección**: No existe forma legítima de "deshacer" un acta erroneo sin destruir evidencia.

## Constraints

- **Folio inmutable**: El folio es único y correlativo por año; nunca debe reutilizarse ni desaparecer.
- **Soft delete obligatorio**: No se permite eliminación física (`DELETE`) de actas que ya tengan folio asignado.
- **Doble autorización para firmadas**: Las actas firmadas requieren un segundo aprobador (supervisor/admin) para ser anuladas.
- **Auditoría mínima**: Todo evento de creación, firma y anulación debe quedar registrado.
- **HTMX + SSR**: Las acciones deben exponerse vía HTMX, respondiendo con HTML parcial o `204 + HX-Trigger`.
- **Django ORM**: Usar transacciones atómicas para escrituras multi-campo.

## Approach

**Enfoque elegido: Anulación lógica (Soft Delete) con protección física.**

- Todas las actas (firmadas o no) se **anulan**, nunca se eliminan físicamente.
- El modelo `Acta` bloqueará explícitamente `delete()` si tiene folio.
- Las no firmadas se anulan con un motivo y permiso estándar.
- Las firmadas requieren un **segundo aprobador** con rol adecuado.
- El PDF original se conserva; opcionalmente se regenera con marca "ANULADA".
- Se agregan campos de auditoría faltantes (`firmada_por`, `fecha_firma`).

**Alternativas consideradas y descartadas:**
- *Eliminación física con doble confirmación*: Destruye numeración y evidencia. No aceptable para documentos legales.
- *Bloqueo total sin anulación*: No permite corregir errores humanos legítimos antes de la firma.

## Architecture

### Estados del Acta

```
[CREADA] --firma--> [FIRMADA] --anulación firmada--> [ANULADA]
[CREADA] --anulación borrador--> [ANULADA]
```

| Estado | firmada | anulada | Editable | Anulable |
|--------|---------|---------|----------|----------|
| Creada/Borrador | False | False | Sí | Sí (1 autor) |
| Firmada | True | False | No | Sí (2 autores) |
| Anulada | * | True | No | No |

### Capas

1. **Modelo**: Extensión de campos + override de `delete()`.
2. **Servicio**: `ActaService.anular_acta()` con lógica de autorización y atomicidad.
3. **Vista**: Endpoint HTMX `acta_anular` con validación de formulario.
4. **UI**: Modal de anulación con campo motivo; condicionalmente selector de aprobador.

## Components

### 1. Modelo `Acta` (Extensiones)

**Nuevos campos:**
- `firmada_por`: `ForeignKey(Colaborador, on_delete=SET_NULL, null=True, blank=True, related_name='actas_firmadas')`
- `fecha_firma`: `DateTimeField(null=True, blank=True)`
- `anulada`: `BooleanField(default=False)`
- `anulada_por`: `ForeignKey(Colaborador, on_delete=SET_NULL, null=True, blank=True, related_name='actas_anuladas')`
- `fecha_anulacion`: `DateTimeField(null=True, blank=True)`
- `motivo_anulacion`: `TextField(null=True, blank=True)`

**Métodos:**
- `delete()`: Lanza `ValidationError` o `ProtectedError` si `self.folio` está asignado. Bloquea eliminación física.
- `clean()`: Valida que `anulada=True` implique `motivo_anulacion` no vacío.

### 2. Servicio `ActaService`

**Método nuevo: `anular_acta(acta, usuario, motivo, aprobador_id=None)`**

Responsabilidades:
- Verificar que el acta no esté ya anulada.
- Si `acta.firmada=True`:
  - Validar que `aprobador_id` esté presente.
  - Validar que el aprobador tenga rol de supervisor o permiso `actas.aprobar_anulacion`.
  - Validar que `aprobador_id != usuario.id`.
- Si `acta.firmada=False`:
  - Solo requiere permiso `actas.delete_acta`.
- Ejecutar dentro de `transaction.atomic()`.
- Actualizar campos de anulación.
- Loggear evento en logger `'actas'`.
- Retornar acta actualizada.

**Ajuste a `firmar_acta()`:**
- Actualizar `firmada_por` y `fecha_firma` al momento de la firma.

### 3. Vista `acta_anular`

- **Método**: POST (HTMX).
- **Permiso**: `@permission_required('actas.delete_acta')`.
- **Payload**: `motivo` (texto), `aprobador_id` (opcional, requerido si firmada).
- **Respuestas**:
  - Éxito: `204 No Content` + `HX-Trigger: actaAnulada`.
  - Error validación: HTML del modal con errores + `HX-Trigger: showToast` con mensaje de error.
  - Error permiso: `403` + toast.

### 4. UI / Templates

- **Modal `acta_anular_modal.html`**:
  - Campo `motivo` (textarea, requerido).
  - Condicionalmente: dropdown `aprobador` (solo supervisores) si `acta.firmada`.
  - Botón "Confirmar Anulación" con `hx-confirm` adicional para firmadas.
- **Badges en tablas**:
  - Acta normal: sin badge especial.
  - Acta anulada: badge rojo/gris "ANULADA".
- **Botón de acción**:
  - Visible solo si `not acta.anulada` y usuario tiene permiso.
  - Oculto o deshabilitado si ya está anulada.

### 5. Auditoría y Logging

- Logger `'actas'` (ya configurado en settings).
- Eventos:
  - `INFO`: `"Acta {folio} creada por {usuario}"`
  - `INFO`: `"Acta {folio} firmada por {usuario}"`
  - `WARNING`: `"Acta {folio} anulada por {usuario}. Motivo: {motivo}. Aprobador: {aprobador}"`

## Data Flow

```
Usuario hace click en "Anular Acta"
  → HTMX GET carga modal con formulario (pre-carga datos del acta)
    → Usuario completa motivo (+ selecciona aprobador si firmada)
      → HTMX POST a /actas/<id>/anular/
        → Vista valida permisos y datos del formulario
          → Llama ActaService.anular_acta(...)
            → Valida estado y autorizaciones
              → transaction.atomic()
                → Actualiza campos anulada*, motivo_anulacion
                → Guarda acta
                → Emite log de auditoría
              → Retorna acta
          → Responde 204 + HX-Trigger('actaAnulada')
      → Frontend refresca tabla vía evento
        → Fila del acta ahora muestra badge "ANULADA"
```

## Error Handling

| Escenario | Error | Respuesta al usuario |
|-----------|-------|----------------------|
| Acta ya anulada | ValidationError | Toast: "Esta acta ya fue anulada." |
| Motivo vacío | ValidationError | Modal con error en campo motivo |
| Acta firmada sin aprobador | ValidationError | Modal con error en campo aprobador |
| Aprobador no tiene permisos | PermissionDenied | Toast: "El aprobador seleccionado no tiene permisos." |
| Aprobador = solicitante | ValidationError | Modal: "El aprobador no puede ser el mismo solicitante." |
| Usuario sin permiso `delete_acta` | PermissionDenied | Toast: "No tienes permisos para anular actas." |
| Intento de eliminación física (ORM/Admin) | ProtectedError / ValidationError | Error 500 o mensaje en admin: "No se puede eliminar un acta. Use la anulación." |

## Testing Strategy

### Unit Tests
- `test_delete_bloqueado_si_tiene_folio`: Verificar que `acta.delete()` lance excepción.
- `test_anular_borrador_sin_aprobador`: Acta no firmada se anula con solo motivo.
- `test_anular_firmada_requiere_aprobador`: Sin aprobador, lanza `ValidationError`.
- `test_anular_firmada_aprobador_sin_permiso`: Aprobador sin rol adecuado falla.
- `test_anular_firmada_aprobador_igual_solicitante`: Debe fallar.

### Integration Tests
- `test_post_anular_acta_borrador`: Endpoint HTMX retorna 204 y actualiza estado.
- `test_post_anular_acta_firmada_sin_aprobador`: Endpoint retorna 400 con error en modal.
- `test_tabla_muestra_badge_anulada`: GET de listado incluye clase CSS/badge en acta anulada.

### E2E Tests (Playwright)
- Flujo completo: Crear acta → Anular → Verificar badge en tabla.
- Flujo completo: Crear acta → Firmar → Intentar anular sin aprobador (debe bloquear) → Anular con aprobador → Verificar badge.

## Open Questions

1. **Visibilidad de anuladas en reportes**: ¿Aparecen en exportaciones Excel con estado "ANULADA" o se excluyen por defecto?
   - *Asunción*: Se incluyen con estado "ANULADA" para auditoría, pero filtradas por defecto en la UI.
2. **Marca de agua en PDF anulado**: ¿Se regenera el PDF con marca "ANULADA" o se conserva el original?
   - *Asunción*: Se mantiene el PDF original; la marca de agua es mejora futura (out of scope inicial).
3. **Recuperación de anulación**: ¿Permitir "des-anular" un acta anulada por error?
   - *Asunción*: No. La anulación es irrevocable (como un delete lógico definitivo). Corregir requiere crear nueva acta.
