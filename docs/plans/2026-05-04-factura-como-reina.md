# Factura como Reina: Optimización del Ingreso de Suministros

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Acelerar radicalmente el ingreso de stock al sistema permitiendo la carga masiva orientada a la factura y ofreciendo un flujo continuo de "Guardar y seguir" para ingresos rápidos.

**Architecture:** 
Implementaremos dos flujos de trabajo sin alterar la estructura fundamental del modelo `MovimientoStock`:
1. **Flujo Rápido (Guardar y Continuar):** Modificación del formulario actual de movimientos para permitir limpiar parcialmente los campos y seguir ingresando datos de la misma factura.
2. **Flujo Masivo (Modo Factura):** Una nueva vista basada en Django Formsets donde la factura es la cabecera, y los movimientos son las filas (detalles). Se integrará HTMX para la creación rápida de nuevos suministros (Catálogo) directamente desde las filas de la factura sin recargar la página.

**Tech Stack:** Django Formsets, HTMX, Tailwind CSS, Alpine.js (para interactividad en las filas).

---

### Task 1: Flujo Continuo - Checkbox "Guardar y Seguir"

**Files:**
- Modify: `suministros/forms.py`
- Modify: `suministros/views.py`
- Modify: `suministros/templates/suministros/movimiento_form.html`
- Modify: `suministros/tests/test_views.py` (o similar para testear el flujo)

**Step 1: Write the failing test**
Escribir un test en `test_views.py` que envíe una petición POST a `movimiento_create` incluyendo un parámetro `seguir_ingresando=True`, y verificar que la redirección sea a la misma URL de creación con parámetros precargados (`numero_factura`, etc.) en lugar de la vista de lista.

**Step 2: Modify Form**
Añadir el campo no persistente al formulario `MovimientoStockForm`:
```python
seguir_ingresando = forms.BooleanField(
    required=False,
    initial=False,
    label="Seguir registrando ítems de esta factura",
    widget=forms.CheckboxInput(attrs={'class': 'rounded border-white/10 bg-white/5 text-jmie-orange'})
)
```

**Step 3: Modify View**
En `movimiento_create` (`suministros/views.py`), al guardar exitosamente:
```python
if form.cleaned_data.get('seguir_ingresando'):
    base_url = reverse('suministros:movimiento_create')
    params = f"?tipo_movimiento={movimiento.tipo_movimiento}&numero_factura={movimiento.numero_factura or ''}"
    messages.success(request, f"Movimiento guardado. Continue con el siguiente ítem de la factura {movimiento.numero_factura}.")
    return redirect(base_url + params)
# else: redirect to list as usual
```
Y asegurarse de que el `GET` inicialice el formulario usando `request.GET`.

**Step 4: Modify Template**
Asegurar que el campo `seguir_ingresando` se renderiza al final del formulario cerca del botón de submit.

**Step 5: Run tests and Commit**
Ejecutar pruebas y hacer commit.


### Task 2: Vista de Carga Masiva - Backend Formset

**Files:**
- Create/Modify: `suministros/forms.py` (Crear `FacturaCabeceraForm` y el formset)
- Modify: `suministros/urls.py`
- Modify: `suministros/views.py`

**Step 1: Crear Formularios y Formset**
En `suministros/forms.py`, crear un formulario de cabecera virtual (no asociado a un modelo `Factura`, sino que sus campos se heredarán a los movimientos):
```python
class FacturaCabeceraForm(forms.Form):
    numero_factura = forms.CharField(...)
    fecha = forms.DateField(...)
```
Crear un `MovimientoFacturaForm` que herede de `MovimientoStockForm` pero oculte/ignore `numero_factura` y `tipo_movimiento` (serán fijos a ENTRADA).
Crear el `formset` usando `forms.formset_factory`.

**Step 2: Crear la Vista**
En `suministros/views.py`, crear la vista `factura_create`.
- **GET:** Inicializar `FacturaCabeceraForm` y un formset vacío con `extra=3`.
- **POST:** Validar cabecera y formset. Por cada form válido en el formset, inyectar el `numero_factura`, asignar `tipo_movimiento=ENTRADA`, y guardar. Agrupar la transacción con `transaction.atomic()`.

**Step 3: Registrar URL**
Añadir `path('ingreso-factura/', views.factura_create, name='factura_create')`.

**Step 4: Testear lógica base**
Añadir un test básico para asegurar que un POST válido crea múltiples movimientos con el mismo número de factura.

**Step 5: Commit**


### Task 3: Carga Masiva - Interfaz Gráfica (HTMX/Alpine)

**Files:**
- Create: `suministros/templates/suministros/factura_form.html`
- Modify: `suministros/templates/suministros/partials/suministro_list_toolbar.html` (para añadir el botón a la nueva vista)

**Step 1: Diseñar la pantalla (Cabecera y Detalle)**
Diseñar `factura_form.html`.
- Panel superior para los campos de `FacturaCabeceraForm`.
- Tabla inferior que itere sobre `formset.forms`.

**Step 2: Dinamismo para agregar filas**
Añadir lógica simple (Alpine.js o Javascript puro) para clonar el último `.form-row` vacío, limpiar sus inputs y actualizar los índices (`id_form-0-cantidad` a `id_form-1-cantidad`), incrementando el campo oculto `TOTAL_FORMS`.

**Step 3: Botón de acceso**
En la vista de listado de suministros o movimientos, añadir un botón llamativo: "Modo Ingreso por Factura" que dirija a `/ingreso-factura/`.

**Step 4: Commit**


### Task 4: Suministro Rápido desde la Factura (HTMX Modal)

**Files:**
- Modify: `suministros/views.py` (vista `suministro_create_modal`)
- Modify: `suministros/urls.py`
- Modify: `suministros/templates/suministros/factura_form.html`
- Create: `suministros/templates/suministros/partials/suministro_options.html`

**Step 1: Preparar la Vista Modal de Suministro**
Crear una vista `suministro_create_rapido` (o adaptar `suministro_create` para responder a HTMX) que devuelva solo el formulario en un modal, y al guardar devuelva una etiqueta `<option value="ID" selected>NOMBRE</option>` para inyectar en el select del formset, o dispare un evento para recargar la lista de suministros.

**Step 2: Botón "+" en las filas del Formset**
En `factura_form.html`, añadir un botón verde pequeño al lado del `select` de "Suministro" que haga un `hx-get` al formulario modal. El reto aquí es saber a *qué* fila devolver el resultado.
*Solución HTMX limpia:* Que el modal dispare un evento `suministroCreated` con el ID del nuevo suministro, y AlpineJS/JS capture ese evento en la fila actual para actualizar su select mediante una petición al catálogo.

**Step 3: Pruebas End-to-End manuales y Commit**
Verificar el flujo: Abrir Factura -> Llenar cabecera -> Buscar suministro -> No existe -> Clic '+' -> Crear suministro en modal -> El suministro aparece seleccionado en la fila -> Llenar cantidad -> Guardar Factura -> Se crean los N movimientos.

**Step 4: Commit y Cierre**
Revisar limpieza de código y convenciones del proyecto.