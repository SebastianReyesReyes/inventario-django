# 🎨 JMIE Precision Console — Guía Maestra de Estilos

> **Uso**: Referencia obligatoria para todos los agentes antes de escribir HTML/Tailwind.
> **Framework CSS**: Tailwind CSS v3 (CDN Play) — `tailwind.config` inline en `base.html`.

---

## 1. Paleta de Colores (Design Tokens)

### Colores de Marca JMIE
| Token | Hex | Uso |
|:---|:---|:---|
| `jmie-blue` | `#003594` | Acento corporativo, focus rings, badges informativos |
| `jmie-orange` | `#ED8B00` | CTA primarios, botón "Nuevo Registro", scroll thumb hover, highlights activos |
| `jmie-gray` | `#7C878E` | Texto secundario, labels, subtítulos, descriptores |

### Superficies (Dark Mode — de más oscuro a más claro)
| Token | Hex | Uso |
|:---|:---|:---|
| `background` | `#0a0c14` | Fondo global del body y sidebar |
| `surface-container-low` | `#10141e` | Cards de métricas, paneles estáticos |
| `surface-container` | `#171c28` | Inputs, selects, textareas (bg de campos) |
| `surface-container-high` | `#1e2533` | Filas hover, glass panels, modales |
| `surface-container-highest` | `#2a3344` | Badges, tooltips, toasts, avatares |
| `surface-bright` | `#354052` | Hover fuerte, estados activos de card |

### Texto
| Token | Hex | Uso |
|:---|:---|:---|
| `on-background` | `#f0f3f8` | Texto principal (blanco cálido) |
| `on-surface` | `#c8cdd5` | Texto de párrafos, descripciones largas |
| `on-surface-variant` | `#7C878E` | Texto muted (= `jmie-gray`) |

### Semánticos
| Token | Hex | Uso |
|:---|:---|:---|
| `accent` | `#ED8B00` | Alias de `jmie-orange` para consistencia |
| `on-accent` | `#1a0800` | Texto sobre botones naranjas |
| `success` | `#34d399` | Badges "Activo", tendencia positiva |
| `error` | `#ef4444` | Badges "Baja", acciones destructivas |
| `info` | `#60a5fa` | Badges "Disponible", enlaces informativos |

---

## 2. Tipografía

| Propiedad | Valor |
|:---|:---|
| **Font Family** | `Montserrat` (Variable Font, cargado localmente) |
| **Fallback** | `system-ui, sans-serif` |
| **Tailwind Token** | `font-sans` |

### Jerarquía Tipográfica
| Elemento | Clases Tailwind |
|:---|:---|
| Título de página (h1) | `text-3xl lg:text-4xl font-black tracking-tighter` |
| Subtítulo | `text-sm font-bold text-jmie-gray` |
| Label de card/métrica | `text-[10px] uppercase font-bold tracking-widest text-jmie-gray` |
| Dato numérico grande | `text-4xl font-black text-on-background` |
| Texto de tabla celdas | `text-sm font-semibold text-on-background` |
| Header de tabla | `text-[11px] font-bold text-jmie-gray uppercase tracking-widest` |
| Texto de badge | `text-[10px] font-bold uppercase tracking-wider` |
| Placeholder de input | `placeholder:text-jmie-gray` |

---

## 3. Border Radius

| Token | Valor | Uso |
|:---|:---|:---|
| `rounded` (default) | `0.375rem` | Chips, badges pequeños |
| `rounded-lg` | `0.5rem` | Inputs, selects |
| `rounded-xl` | `0.75rem` | Cards, paneles, side-over |
| `rounded-2xl` | `1rem` | Glass panels, modales |
| `rounded-full` | `9999px` | Avatares, pills, search input |

---

## 4. Borders

| Uso | Clase |
|:---|:---|
| División general | `border border-white/5` |
| División de tabla | `divide-y divide-white/5` |
| Border de input normal | `border-[1px] border-white/5` |
| Border de input focus | `focus:border-jmie-blue/50 focus:ring-1 focus:ring-jmie-blue/40` |
| Border CTA naranja | `border-jmie-orange/30` |
| Línea separadora sidebar | `border-b border-white/5` |

---

## 5. Componentes Reutilizables

### 5.1 Componentes Cotton (django-cotton)
Preferir el uso de componentes Cotton para mantener la consistencia y reducir el boilerplate.

| Componente | Uso |
|:---|:---|
| `<c-btn_primary>` | Botón naranja principal para CTAs importantes. |
| `<c-btn_secondary>` | Botón ghost para acciones secundarias. |
| `<c-page_header>` | Encabezado estándar con título y slot para acciones. |
| `<c-search_input>` | Input de búsqueda con integración HTMX opcional. |
| `<c-glass_panel>` | Panel con fondo translúcido y desenfoque. |
| `<c-empty_state>` | Estado visual cuando no hay datos. |
| `<c-confirm_dialog>` | Diálogo de confirmación Alpine.js (para eliminaciones). |
| `<c-th_sort>` | Celda de encabezado de tabla con ordenamiento. |

**Ejemplo de uso:**
```html
<c-page_header title="Equipos IT">
    <c-btn_primary hx-get="{% url 'crear' %}" hx-target="#modal-container">
        <span class="material-symbols-outlined mr-2">add</span>
        Nuevo Equipo
    </c-btn_primary>
</c-page_header>
```

### 5.2 Inputs / Campos de Formulario
```html
<!-- Input de texto estándar -->
<input type="text"
    class="w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background placeholder:text-jmie-gray focus:ring-1 focus:border-jmie-blue focus:ring-jmie-blue/40 transition-all">

<!-- Select estándar -->
<select class="w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background appearance-none">

<!-- Textarea -->
<textarea rows="3"
    class="w-full bg-surface-container-high border-[1px] border-white/5 rounded-lg px-4 py-3 text-on-background placeholder:text-jmie-gray focus:ring-1 focus:border-jmie-blue focus:ring-jmie-blue/40 transition-all">
</textarea>

<!-- Checkbox (Orange-themed) -->
<input type="checkbox"
    class="w-5 h-5 rounded border-white/10 bg-surface-container-high text-jmie-orange focus:ring-jmie-orange/40 transition-all">
```

> **Nota para agentes**: No escribir estas clases manualmente. Usar `BaseStyledForm` de `core/forms.py` que las aplica automáticamente.

### 5.2 Botones
```html
<!-- CTA Primario (Naranja) -->
<button class="px-5 py-2.5 bg-jmie-orange text-white text-sm font-bold rounded-lg hover:brightness-110 transition-all shadow-[0_0_15px_rgba(237,139,0,0.3)]">

<!-- Botón Secundario (Ghost) -->
<button class="px-5 py-2.5 bg-white/5 hover:bg-white/10 text-on-background text-sm font-bold border border-white/10 rounded-lg transition-all">

<!-- Botón Icono (Inline) -->
<button class="text-jmie-gray hover:text-jmie-orange transition-colors p-2 rounded-lg hover:bg-white/5">
    <span class="material-symbols-outlined text-[18px]">edit</span>
</button>

<!-- Botón Destructivo (Delete) -->
<button class="text-jmie-gray hover:text-error transition-colors p-2 rounded-lg hover:bg-white/5">
    <span class="material-symbols-outlined text-[18px]">delete</span>
</button>
```

### 5.3 Cards de Métrica
```html
<div class="bg-surface-container-low p-6 rounded-xl border-b-[3px] border-{COLOR}/30 hover:bg-surface-bright transition-colors cursor-default">
    <div class="flex items-center justify-between mb-2">
        <span class="text-[10px] uppercase font-bold tracking-widest text-jmie-gray">LABEL</span>
        <span class="material-symbols-outlined text-{COLOR} text-sm">ICON</span>
    </div>
    <div class="text-4xl font-black text-on-background mt-1">{{ valor }}</div>
    <div class="mt-2 text-xs font-bold text-{COLOR} flex items-center">
        <span class="material-symbols-outlined text-[14px] mr-1">trending_up</span>
        Subtexto
    </div>
</div>
```

### 5.4 Tabla Estándar
```html
<div class="bg-surface-container-low rounded-xl border border-white/5 overflow-hidden">
    <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-white/5">
            <thead class="bg-surface-container-high/50">
                <tr>
                    <th class="px-6 py-4 text-left text-[11px] font-bold text-jmie-gray uppercase tracking-widest border-b border-white/5">Header</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-white/5 bg-transparent">
                <tr class="hover:bg-white/[0.03] transition-colors group">
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-on-background">Dato</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
```

### 5.5 Modales y Diálogos

#### A. Modales HTMX (Inyectados)
Se inyectan desde el servidor en `#modal-container`. Ideales para formularios complejos.

```html
<!-- Se inyecta en #modal-container -->
<div class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm"
     x-data="{ open: false }"
     x-init="setTimeout(() => open = true, 50)"
     x-show="open"
     @modal-close.window="open = false; setTimeout(() => $el.remove(), 300)"
     x-transition:enter="transition ease-out duration-300"
     x-transition:enter-start="opacity-0"
     x-transition:enter-end="opacity-100"
     x-transition:leave="transition ease-in duration-200"
     x-transition:leave-start="opacity-100"
     x-transition:leave-end="opacity-0">
    <!-- ... (resto del modal igual) -->
</div>
```

#### B. Diálogos de Confirmación (Cotton)
Para acciones rápidas (ej: eliminar) que no requieren ir al servidor solo para mostrar el diálogo.

```html
<c-confirm_dialog 
    dialog_title="¿Eliminar equipo?" 
    message="Esta acción no se puede deshacer."
    hx-delete="URL"
    hx-target="closest tr"
>
    <span class="material-symbols-outlined">delete</span>
</c-confirm_dialog>
```

### 5.6 Badge de Estado
```html
<!-- Usar color dinámico del modelo EstadoDispositivo -->
<span class="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider"
      style="background-color: {{ estado.color }}20; color: {{ estado.color }};">
    {{ estado.nombre }}
</span>
```

### 5.7 Toast Notification (dispatch desde HTMX)
```javascript
// Desde backend (HX-Trigger header):
headers = {'HX-Trigger': json.dumps({"showNotification": "Mensaje de éxito"})}

// Desde frontend (Alpine.js):
$dispatch('show-notification', {value: 'Operación completada'})
```

---

## 6. Patrones HTMX

| Operación | Patrón |
|:---|:---|
| **Abrir modal** | `hx-get="URL" hx-target="#modal-container"` |
| **Abrir side-over** | `hx-get="URL" hx-target="#side-over-container"` |
| **Guardar y cerrar** | Backend retorna `HttpResponse(status=204)` con `HX-Trigger` |
| **Recargar lista** | Trigger customizado: `hx-trigger="{evento} from:body"` |
| **Búsqueda en vivo** | `hx-trigger="keyup changed delay:500ms, search"` |
| **Detección HTMX** | Preferir `request.headers.get('HX-Request')` (estándar Django) |

---

## 7. Convenciones de Naming

### Templates
```
{app}/templates/{app}/
├── {modelo}_list.html          # Listado principal
├── {modelo}_form.html          # Formulario create/edit
├── {modelo}_detail.html        # Vista de detalle (full page)
└── partials/
    ├── {modelo}_list_results.html    # Resultados parciales para HTMX search
    ├── {modelo}_detail_sideover.html # Side-over para HTMX
    ├── {modelo}_form_modal.html      # Modal HTMX
    └── {modelo}_success.html         # Feedback de éxito
```

### URLs
```python
app_name = '{app}'
# path('{verbo}/', views.{modelo}_{accion}, name='{modelo}_{accion}')
# Ejemplo:
path('crear/',              views.dispositivo_create,  name='dispositivo_create')
path('listado/',            views.dispositivo_list,    name='dispositivo_list')
path('detalle/<int:pk>/',   views.dispositivo_detail,  name='dispositivo_detail')
path('editar/<int:pk>/',    views.dispositivo_update,   name='dispositivo_update')
path('eliminar/<int:pk>/',  views.dispositivo_delete,   name='dispositivo_delete')
```

### HX-Trigger Events (Naming Convention)
```
{entidad}ListChanged    → Recarga listas: fabricanteListChanged, modeloListChanged
showNotification        → Toast global
mantenimiento-saved     → Refresh del side-over
modal-close             → Cierre de modal
```

---

## 8. Iconografía

- **Librería**: Google Material Symbols Outlined
- **Clase base**: `material-symbols-outlined`
- **Relleno**: `.icon-filled` para iconos activos en la navegación
- **Tamaños**: `text-sm` (14px), `text-[18px]`, `text-xl` (20px), `text-[22px]`

### Iconos frecuentes
| Contexto | Icono |
|:---|:---|
| Dashboard | `dashboard` |
| Inventario | `inventory_2` |
| Colaboradores | `badge` |
| Fabricantes | `category` |
| Tipos | `devices` |
| CCs | `payments` |
| Estados | `label` |
| Crear | `add` |
| Editar | `edit` |
| Eliminar | `delete` |
| Buscar | `search` |
| QR | `qr_code_2` |
| Mantenimiento | `build` |
| Cerrar | `close` |
| Check | `check_circle` |
| Warning | `warning` |
| Logout | `logout` |

---

## 9. Glass Panel (Panel con Blur)

```css
.glass-panel {
    background: rgba(30, 37, 51, 0.6);
    backdrop-filter: blur(20px);
}
```

---

## 10. Animaciones

| Efecto | Implementación |
|:---|:---|
| Transición HTMX | `.htmx-added { opacity: 0 }` → `.htmx-settling { opacity: 1; transition: 0.3s }` |
| Modal entrance | Alpine `x-transition:enter` con `scale-95 → scale-100` |
| Side-over slide | `translateX(100%) → translateX(0)` |
| Hover en icon nav | `group-hover:scale-110 transition-transform` |
| Toast | `translate-y-4 → translate-y-0` + auto-dismiss 3s |

---

*Documento vivo. Actualizar al incorporar nuevos componentes.*
