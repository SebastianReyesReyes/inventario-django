# Convenciones de Nombres de URLs (URL Naming Conventions)

Para asegurar la escalabilidad, la mantenibilidad y el principio **DRY (Don't Repeat Yourself)** en todo el proyecto JMIE Inventario, este documento establece la convención estricta para nombrar las rutas de las aplicaciones en `urls.py`.

## 1. La Regla de Oro
**Todas las URLs que realizan operaciones CRUD sobre un modelo deben tener como prefijo el nombre del modelo de Django exacto (en minúsculas), seguido de la acción que realizan.**

Formato esperado: `[nombre_del_modelo_en_minusculas]_[accion]`

### Ejemplos Correctos
- `dispositivo_list`, `dispositivo_create`, `dispositivo_update`, `dispositivo_delete`
- `colaborador_detail`, `colaborador_update`
- `tipodispositivo_create`, `tipodispositivo_delete`
- `centrocosto_update`, `centrocosto_toggle_activa`

### Ejemplos Incorrectos (Lo que NO debes hacer)
- ❌ `tipo_create` (El modelo se llama `TipoDispositivo`)
- ❌ `estado_edit` (El modelo se llama `EstadoDispositivo`. Además, la acción estandarizada es `_update`, no `_edit`)
- ❌ `cc_list` (El modelo se llama `CentroCosto`)
- ❌ `acta_crear` (Usa el idioma de acción estándar: `create`, `update`, `delete`, `list`, `detail`)

## 2. ¿Por qué es Crítico? (Polimorfismo con `render_actions`)
El proyecto utiliza un Template Tag inteligente llamado `{% render_actions %}` (ubicado en `core/templatetags/action_tags.py`). Este tag genera automáticamente los botones de **Ver, Editar, Eliminar y Alternar Estado (Toggle)** en las tablas, evaluando los permisos del usuario activo.

Para que este tag funcione dinámicamente y sin requerir que escribas el HTML de los botones para cada tabla, el código en Python extrae el nombre del modelo del objeto que le pasas:

```python
model_name = obj._meta.model_name # Ej: "tipodispositivo", "centrocosto"
```

Luego, intenta construir la URL buscando el patrón:
```python
reverse(f"{app_label}:{model_name}_update", args=[pk])
```

**Si no sigues la convención, el tag lanzará una excepción `NoReverseMatch` (Error 500) y la tabla no cargará.**

## 3. Hard Delete vs Soft Delete (Toggle)
El tag de acciones soporta inteligentemente dos tipos de "Borrado":

*   **Hard Delete (Eliminación Física):** 
    Si la URL se llama `[modelo]_delete`, el tag renderiza el icono del **Basurero Rojo**. Al hacer clic, hace un `hx-delete` a esa URL. (Ej: `fabricante_delete`).
*   **Soft Delete / Toggle (Desactivación Lógica):** 
    Si la URL se llama `[modelo]_toggle_activa` o `[modelo]_toggle`, el tag **ignora el basurero** y renderiza un **Interruptor (Switch)** verde/gris. Al hacer clic, hace un `hx-post` (o patch) para cambiar el estado. (Ej: `centrocosto_toggle_activa`).

## 4. Buenas Prácticas y Toasts
Al programar las vistas de `delete` o `toggle` con HTMX, **nunca devuelvas un Error 400 silenciado** si la acción está protegida (ej: intentar borrar un tipo de equipo que ya tiene dispositivos asociados).

En su lugar, devuelve un `HTTP 200` o `204` y utiliza el encabezado `HX-Trigger` para notificar al usuario mediante un Toast visual:

```python
# Ejemplo Correcto
if Dispositivo.objects.filter(tipo=tipo).exists():
    return HttpResponse(status=204, headers={'HX-Trigger': json.dumps({"showNotification": "Protegido: Existen dispositivos de este tipo"})})
```
