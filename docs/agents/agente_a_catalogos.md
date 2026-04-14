# Agente A — Épica 1: Catálogos y Parametría

## Contexto del Proyecto

Eres un agente de desarrollo especializado trabajando en **Sistema de Inventario JMIE**, una aplicación Django para gestión de activos de TI en una empresa de construcción.

**Stack Tecnológico:**
- Backend: Django 6.x + Python 3.14
- Frontend: HTMX (sin React/Vue) + Alpine.js + Tailwind CSS
- Diseño: "Precision Console" — dark mode corporativo, tonos JMIE (naranja/azul oscuro)
- Base de datos: SQLite (dev) → PostgreSQL (prod)
- App donde trabajas: `core/` (catálogos base) y `dispositivos/` (referencia)
- **Principio de Desarrollo:** Aplicar DRY (Don't Repeat Yourself) y mantener la estructura de "Mini Apps" modular para facilitar el mantenimiento.

**Arquitectura de Apps Django:**
```
inventario_jmie/   ← settings, urls raíz
core/              ← TipoDispositivo, CentroCosto, Fabricante, Modelo, EstadoDispositivo
colaboradores/     ← Colaborador (AbstractUser)
dispositivos/      ← Dispositivo (modelo padre) + subclases (Notebook, Smartphone, Monitor, etc.)
actas/             ← Actas de entrega PDF
```

**Patrones Establecidos en el Proyecto:**
- Los templates viven en `app/templates/app/` 
- Los partials HTMX en `app/templates/app/partials/`
- Namespacing de URLs: `app_name = 'core'` → `{% url 'core:fabricante_list' %}`
- Los modales se abren/cierran con Alpine.js (`x-data="{ modalAbierto: false }"`)
- Formularios se cargan vía `hx-get` y se envían con `hx-post`
- Respuestas exitosas retornan partial HTML + `HX-Trigger` para cerrar modal
- Todo CRUD usa **borrado lógico** (campo `esta_activo` o `is_active`), nunca DELETE real

---

## Tu Misión: Épica 1 — Catálogos y Parametría

Implementar el CRUD completo de los **4 catálogos base** que alimentan toda la aplicación. Sin estos, ningún otro módulo puede funcionar correctamente.

---

## Historias de Usuario a Implementar

### HU-01: Tipos de Dispositivos

**Qué construir:** CRUD completo para `TipoDispositivo`.

**Modelo ya existe en `core/models.py`:**
```python
class TipoDispositivo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    sigla  = models.CharField(max_length=10, unique=True)  # Ej: "NTBK", "SMPH"
```

**Criterios de Aceptación:**
1. Crear tipo con nombre + sigla.
2. Error claro si nombre o sigla ya existen.
3. Editar nombre/sigla de un tipo existente.
4. **Protección:** Si el tipo tiene equipos asociados (`on_delete=PROTECT`), el botón "Eliminar" debe estar deshabilitado con un tooltip explicativo.

**Directrices Técnicas:**
- FK desde `Dispositivo` → `TipoDispositivo` ya tiene `on_delete=models.PROTECT`.
- CRUD vía modal Alpine.js, formulario cargado con `hx-get`, enviado con `hx-post`.
- Éxito: nueva fila `<tr>` insertada + `HX-Trigger: {"showNotification": "...", "closeModal": true}`.

---

### HU-02: Fabricantes y Modelos

**Qué construir:** CRUD anidado de `Fabricante` y `Modelo`.

**Modelos ya existen en `core/models.py`:**
```python
class Fabricante(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

class Modelo(models.Model):
    nombre    = models.CharField(max_length=100)
    fabricante = models.ForeignKey(Fabricante, on_delete=models.PROTECT, related_name='modelos')
```

**Criterios de Aceptación:**
1. Fabricantes se gestionan independientemente.
2. Al crear un Modelo, el selector de Fabricante es obligatorio.
3. La vista de lista de Modelos muestra la columna "Fabricante" y permite filtrar por él.

**Directrices Técnicas:**
- `select_related('fabricante')` obligatorio en el QuerySet de Modelos.
- Misma mecánica modal HTMX + Alpine que HU-01.
- El filtro por fabricante puede ser un `hx-get` con query param `?fabricante_id=X`.

---

### HU-03: Centros de Costo

**Qué construir:** CRUD de `CentroCosto` con baja lógica.

**Modelo ya existe en `core/models.py`:**
```python
class CentroCosto(models.Model):
    nombre           = models.CharField(max_length=100)
    codigo_contable  = models.CharField(max_length=20, unique=True)
    activa           = models.BooleanField(default=True)  # ← AGREGAR si no existe
```

**Criterios de Aceptación:**
1. Nombre descriptivo + Código contable alfanumérico únicos.
2. **Baja Lógica:** Botón "Desactivar" (no borrar). Al desactivar, el CC desaparece de los selectores pero permanece en datos históricos.
3. Los CCs inactivos muestran un badge rojo "Inactivo" en la lista.

**Directrices Técnicas:**
- Todos los `ModelChoiceField` que usen `CentroCosto` deben filtrar `activa=True`.
- Vista de toggle: `hx-post` al endpoint `cc/<id>/toggle-activa/` → retorna badge actualizado via OOB Swap.

---

### HU-04: Estados de Inventario

**Qué construir:** Fixture de datos iniciales + CRUD simple de `EstadoDispositivo`.

**Modelo sugerido:**
```python
class EstadoDispositivo(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    color  = models.CharField(max_length=7, default='#6B7280')  # hex para badge
```

**Criterios de Aceptación:**
1. El sistema viene con 4 estados precargados: `Disponible`, `Asignado`, `En Reparación`, `De Baja`.
2. Se pueden agregar estados nuevos (ej. "En Tránsito").
3. **Restricción:** No se puede eliminar un estado con equipos en ese estado (`on_delete=PROTECT`).

**Directrices Técnicas:**
- Crear un **data migration** o fixture `core/fixtures/estados_iniciales.json`.
- CRUD igual que los anteriores (modal + HTMX).

---

## Estilo Visual Requerido

Mantener el design system "Precision Console" usando **Tailwind CSS**:

- Tablas: `bg-slate-900 border border-white/5 rounded-xl overflow-hidden`.
- Filas: `hover:bg-white/5 transition-colors`.
- Botones primarios: `bg-orange-600 hover:bg-orange-500 text-white font-bold py-2 px-4 rounded-lg`.
- Badges: `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium`.
- Notificaciones: Toast con `bg-slate-800 border-l-4 border-orange-500`.

---

## Entregables Esperados

Al finalizar esta Épica, el proyecto debe tener:

- [ ] `core/views.py` con vistas CRUD para los 4 catálogos.
- [ ] `core/urls.py` con todas las rutas bajo `app_name = 'core'`.
- [ ] Templates: `tipo_list.html`, `fabricante_list.html`, `cc_list.html`, `estado_list.html` + sus partials modales.
- [ ] Forms en `core/forms.py` con validaciones de unicidad.
- [ ] Data migration o fixture para estados iniciales (`HU-04`).
- [ ] El campo `activa` agregado a `CentroCosto` con su migración correspondiente.
- [ ] Tests mínimos: uno por HU cubriendo el happy path y la restricción principal.

---

## ⚠️ Restricciones Importantes

- **NO** usar `DeleteView` de Django. Solo borrado lógico o protección por FK.
- **NO** mezclar lógica de negocio en las vistas. Usar `clean()` o `save()` en los modelos/forms.
- **NO** alterar modelos de otras apps (`dispositivos/`, `colaboradores/`) a menos que sea agregar una FK.
- Toda respuesta HTMX exitosa debe incluir un `HX-Trigger` apropiado para actualizar la UI sin reload.
