---
date: 2026-04-30
topic: "Modal de Doble Confirmación para Anulación de Actas"
status: approved
---

# Modal de Doble Confirmación para Anulación de Actas

<section name="problem">

El sistema actual no permite eliminar o anular actas desde la interfaz de usuario. Las actas no firmadas funcionan como borradores y necesitan poder descartarse con cierta frecuencia. Las actas firmadas son documentos legales que rara vez requieren anulación, pero cuando ocurre necesitan protección contra acciones accidentales.

El usuario requiere un flujo de anulación con **doble confirmación visual** (doble alert) implementado con **django-cotton**, **Alpine.js** y **HTMX**, sin introducir complejidad de doble aprobación de personas distintas ni soft-delete generalizado.

</section>

<section name="findings">

### Branch: confirm_mechanic

**Finding:** La segunda capa de confirmación usará un patrón `text_guard`: el usuario deberá transcribir manualmente un texto específico (ej. `'ANULAR'` o el folio del acta) para habilitar el botón de confirmación final. Esto proporciona una barrera de fricción deliberada ante la acción destructiva, integrándose con Alpine.js para la validación en tiempo real del campo y HTMX para el envío final.

**Opciones evaluadas:**
- `text_guard` (elegida): Fricción óptima para evitar clics accidentales sin ser tedioso.
- `two_modals`: Demasiado intrusivo y lento para el flujo habitual.
- `checkbox_guard`: Demasiado fácil de clickear accidentalmente.
- `delayed_button`: No previene clics intencionales accidentales, solo fuerza espera.

### Branch: component_arch

**Finding:** La arquitectura de componentes utilizará una jerarquía reutilizable en django-cotton:
- `<c-modal.base>`: overlay y layout genérico.
- `<c-modal.confirm>`: contenido de la capa de confirmación.
- `<c-modal.text-guard>`: especializado para la segunda capa de fricción.

La integración HTMX/Alpine.js será híbrida: Alpine.js controla el estado local del flujo de dos pasos (avance entre pasos y validación en tiempo real del texto de guarda), mientras que HTMX se encarga exclusivamente del request final de anulación condicional (`hx-post`/`hx-delete`) al backend. El componente padre expone slots (`header`, `body`, `actions`) para que las vistas Django inyecten el contexto específico del acta (folio, tipo, estado firmado/borrador).

**Opciones evaluadas:**
- `hierarchy` (elegida): Máxima reutilización en otros catálogos del sistema.
- `single_param`: Menos flexible para estados complejos.
- `inline_alpine`: Difícil de mantener y no aprovecha Cotton.
- `htmx_oob`: Más magia de la necesaria; rompe la coherencia del componente.

### Branch: backend_operation

**Finding:** El backend ejecutará una operación de **eliminación condicional** mediante una capa de servicio:
- **Borradores (no firmadas):** borrado físico (`DELETE`) dado que carecen de valor legal.
- **Actas firmadas:** anulación lógica (soft delete) que actualiza el estado a `anulada` registrando fecha, motivo y usuario responsable, preservando el registro legal.

La operación se envuelve en `transaction.atomic()` y responde con `204 + HX-Trigger` ante éxito, o con el HTML del modal de error + toast en caso de fallo de validación o integridad.

**Opciones evaluadas:**
- `conditional_delete` (elegida): Limpio para borradores, seguro para legales.
- `hard_delete`: Inaceptable para actas firmadas; pierde trazabilidad legal.
- `status_voided`: Forzaría soft-delete incluso en borradores; genera ruido innecesario.
- `soft_flag`: Mismo problema que status_voided; borradores no necesitan persistir.

### Branch: state_differentiation

**Finding:** La experiencia de usuario se bifurca según el estado legal del acta:

1. **Borradores:** modal de severidad media (tonos ámbar/naranja), con `text_guard` simplificado (ej. escribir `'ELIMINAR'`), sin campo de motivo obligatorio. El copy enfatiza que la acción es irreversible pero sin trazabilidad legal.

2. **Actas firmadas:** modal de severidad máxima (rojo/alerta crítica), con `text_guard` estricto (transcribir el folio completo o `'ANULAR-{folio}'`), más un campo de motivo de anulación obligatorio con validación de longitud mínima. El copy advierte explícitamente la conservación del registro legal.

3. **Adaptación dinámica:** el backend inyecta flags semánticos en el contexto del componente (`severity`, `guard_mode`, `guard_target_text`, `requires_reason`, `reason_min_length`), que Alpine.js consume para configurar el estado local del modal antes de que HTMX dispare la petición.

**Opciones evaluadas:**
- `mechanic_diff` (elegida): Escalabilidad de fricción según riesgo legal.
- `unified_ui`: Subestima el riesgo de las firmadas.
- `dual_entrypoints`: Fragmenta innecesariamente la UX.
- `conditional_block`: Demasiado restrictivo; las firmadas sí pueden necesitar anulación eventualmente.

</section>

<section name="recommendation">

## Arquitectura Recomendada

### 1. Componentes django-cotton (Reutilizables)

**`<c-modal.base>`**
- Overlay, centrado, backdrop blur, click-outside para cerrar.
- Slots: `header`, `body`, `actions`.

**`<c-modal.confirm>`**
- Consume `<c-modal.base>`.
- Añade icono de alerta, título dinámico, descripción.
- Props: `severity` (amber | red), `title`, `description`.

**`<c-modal.text-guard>`**
- Consume `<c-modal.confirm>`.
- Añade input de texto + label indicando qué escribir.
- Botón de acción deshabilitado hasta que el input coincida con `guard_target_text`.
- Props: `guard_target_text`, `button_text`, `button_class`.

**`<c-modal.delete-acta>`** (Componente de negocio específico)
- Orquesta el flujo completo de dos pasos usando Alpine.js (`x-data`).
- Paso 1: Información del acta + botón "Continuar".
- Paso 2: `<c-modal.text-guard>` con variables inyectadas desde Django.
- Condicionalmente muestra textarea de motivo si `requires_reason=True`.
- HTMX: el form final hace `hx-post` a la URL de anulación.

### 2. Estado Alpine.js (Flujo de 2 pasos)

```javascript
// Dentro de <c-modal.delete-acta>
x-data="{
  step: 1,
  guardInput: '',
  reason: '',
  guardTarget: '{{ guard_target_text }}',
  requiresReason: {{ requires_reason|yesno:'true,false' }},
  reasonMinLength: {{ reason_min_length|default:0 }},
  get canProceed() {
    return this.guardInput === this.guardTarget && 
           (!this.requiresReason || this.reason.length >= this.reasonMinLength);
  }
}"
```

### 3. Backend (Vista + Servicio)

**Vista `acta_anular` (HTMX-only):**
- `GET`: Renderiza el modal `<c-modal.delete-acta>` con contexto semántico (severity, guard_target_text, etc.).
- `POST`: Recibe `acta_id`, valida estado, delega a servicio.
  - Respuesta éxito: `204 + HX-Trigger('actaAnulada')`.
  - Respuesta error: HTML del modal con errores + `HX-Trigger('showToast')`.

**Servicio `ActaService.anular(acta, usuario, motivo=None)`:**
- Si `acta.firmada=False`: `acta.delete()` (hard delete).
- Si `acta.firmada=True`: valida motivo presente, actualiza campos de anulación lógica (si existen en modelo) o lanza `NotImplementedError` si aún no hay campos de soft-delete.
- Todo dentro de `transaction.atomic()`.

### 4. Flujo Visual

| Paso | Borrador | Firmada |
|------|----------|---------|
| **1** | Modal ámbar: "Eliminar borrador ACT-XXXX" | Modal rojo: "Anular acta firmada ACT-XXXX" |
|     | Descripción: "Esta acción no se puede deshacer." | Descripción: "El documento legal será anulado y conservado en registros." |
|     | Botón: "Continuar" | Campo motivo (obligatorio, min 20 chars) + Botón: "Continuar" |
| **2** | Text guard: Escribe "ELIMINAR" | Text guard: Escribe "ANULAR-ACT-XXXX" |
|     | Botón "Eliminar definitivamente" habilitado al coincidir | Botón "Anular definitivamente" habilitado al coincidir + motivo válido |
| **3** | `hx-delete` → 204 → toast "Borrador eliminado" | `hx-post` → 204 → toast "Acta anulada" |

### 5. Integración en Tablas

- Agregar icono de papelera en `acta_table_rows.html` solo si `perms.actas.delete_acta`.
- `hx-get="{% url 'actas:acta_anular' acta.pk %}"` con `hx-target="#modal-container"`.
- Post-anulación: evento `actaAnulada` recarga la tabla vía `hx-trigger`.

### 6. Testing (Plan)

- **Unit:** Servicio `ActaService.anular` con mocks para borrador vs firmada.
- **Integration:** Vista POST retorna 204 y 400 según estado y payload.
- **E2E (Playwright):** 
  - Click papelera en borrador → modal aparece → escribir "ELIMINAR" → click eliminar → fila desaparece.
  - Click papelera en firmada → modal aparece → intentar submit sin motivo → error visible → escribir motivo + text guard → click anular → fila muestra badge "ANULADA".

## Archivos a Crear / Modificar (Resumen)

**Nuevos:**
- `templates/cotton/modal/base.html`
- `templates/cotton/modal/confirm.html`
- `templates/cotton/modal/text_guard.html`
- `actas/templates/actas/partials/acta_delete_modal.html` (o reutilizar el untracked `acta_anular_modal.html`)

**Modificados:**
- `actas/views.py` — Añadir `acta_anular` (GET/POST)
- `actas/urls.py` — Ruta `acta_anular`
- `actas/services.py` — Método `anular`
- `actas/templates/actas/partials/acta_table_rows.html` — Botón papelera + badge anulada
- `actas/templates/actas/acta_list.html` — Contenedor `#modal-container` + listeners de eventos

## Notas de Implementación

- No se requieren cambios de modelo para borradores (hard delete).
- Si se desea anular firmadas, se necesitan los campos de soft-delete ya presentes en la migración `0003` (que existe como untracked). Si no se usan, la anulación de firmadas puede lanzar `NotImplementedError` o ser bloqueada en UI hasta que se migren esos campos.
- El componente `<c-modal.text-guard>` debe ser genérico para reutilizarse en la eliminación de dispositivos, colaboradores, etc.

</section>
