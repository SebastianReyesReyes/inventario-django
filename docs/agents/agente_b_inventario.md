# Agente B — Épica 3: Inventario Físico

## Contexto del Proyecto

Eres un agente de desarrollo especializado trabajando en **Sistema de Inventario JMIE**, una aplicación Django para gestión de activos de TI en una empresa de construcción.

**Stack Tecnológico:**
- Backend: Django 6.x + Python 3.14
- Frontend: HTMX (sin React/Vue) + Alpine.js + Tailwind CSS
- Diseño: "Precision Console" — dark mode corporativo, tonos JMIE (naranja/azul oscuro)
- Base de datos: SQLite (dev) → PostgreSQL (prod)
- App donde trabajas: `dispositivos/` e integraciones modulares.
- **Principio de Desarrollo:** Aplicar DRY (Don't Repeat Yourself) y mantener la estructura de "Mini Apps" modular para facilitar el mantenimiento.

**Arquitectura de Apps Django:**
```
inventario_jmie/   ← settings, urls raíz
core/              ← TipoDispositivo, CentroCosto, Fabricante, Modelo, EstadoDispositivo
colaboradores/     ← Colaborador (AbstractUser)
dispositivos/      ← Dispositivo (modelo padre) + subclases (Notebook, Smartphone, Monitor, etc.)
actas/             ← Actas de entrega PDF
```

**Modelo Base ya Implementado (`dispositivos/models.py`):**
```python
class Dispositivo(models.Model):
    identificador_interno = models.CharField(max_length=30, unique=True)  # JMIE-NTBK-00001
    numero_serie  = models.CharField(max_length=100, unique=True)
    tipo          = models.ForeignKey('core.TipoDispositivo', on_delete=models.PROTECT)
    modelo        = models.ForeignKey('core.Modelo', on_delete=models.PROTECT)
    centro_costo  = models.ForeignKey('core.CentroCosto', on_delete=models.PROTECT)
    estado        = models.ForeignKey('core.EstadoDispositivo', on_delete=models.PROTECT)
    propietario_actual = models.ForeignKey('colaboradores.Colaborador', null=True, blank=True, on_delete=models.SET_NULL)
    fecha_compra  = models.DateField(null=True, blank=True)
    valor_contable = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notas_condicion = models.TextField(blank=True)
    esta_activo   = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Autogenera identificador_interno si es nuevo: JMIE-[SIGLA]-000XX
        ...

# Subclases (herencia multi-tabla):
class Notebook(Dispositivo):
    ram_gb      = models.PositiveIntegerField(null=True)
    almacenamiento_gb = models.PositiveIntegerField(null=True)
    procesador  = models.CharField(max_length=100, blank=True)

class Smartphone(Dispositivo):
    imei        = models.CharField(max_length=20, unique=True)
    numero_linea = models.CharField(max_length=20, blank=True)

class Monitor(Dispositivo):
    pulgadas    = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    resolucion  = models.CharField(max_length=20, blank=True)
```

**Patrones Establecidos en el Proyecto:**
- Namespacing de URLs: `app_name = 'dispositivos'` → `{% url 'dispositivos:dispositivo_list' %}`
- Los modales se abren/cierran con Alpine.js
- Formularios se cargan vía `hx-get`, enviados con `hx-post`
- El side-panel ("slide-over") se activa con `hx-target="#sideover-container"` e `hx-swap="innerHTML"`
- Borrado lógico: `esta_activo = False`, nunca `DELETE` real

---

## Tu Misión: Épica 3 — Inventario Físico

Completar e implementar las funcionalidades avanzadas del inventario de hardware: formularios dinámicos por tipo, búsqueda en vivo, códigos QR y bitácora de mantenimiento.

---

## Historias de Usuario a Implementar

### HU-09 + HU-10: Registro Base, Identificador Único e Información Contable

**Estado actual:** El modelo existe. Las vistas básicas de CREATE/UPDATE ya podrían existir parcialmente.

**Qué mejorar/completar:**

1. **Validación de Fechas:** Agregar `clean()` al modelo `Dispositivo` para rechazar `fecha_compra` futura.
2. **Valor Contable:** Validar que sea siempre positivo.
3. **Unicidad clara:** Si el número de serie o ID interno ya existe, el formulario debe mostrar un error en el campo correspondiente (no un 500).

```python
# En Dispositivo.clean():
def clean(self):
    if self.fecha_compra and self.fecha_compra > date.today():
        raise ValidationError({'fecha_compra': 'La fecha de compra no puede ser futura.'})
    if self.valor_contable and self.valor_contable < 0:
        raise ValidationError({'valor_contable': 'El valor debe ser positivo.'})
```

---

### HU-11: Formularios Dinámicos por Categoría ⭐ (La más compleja)

**Qué construir:** El formulario de creación/edición de dispositivo debe mostrar campos específicos **instantáneamente** al cambiar el selector de Tipo, sin recargar la página.

**Criterios de Aceptación:**
1. Al seleccionar "Notebook" → aparecen campos RAM, Almacenamiento, Procesador.
2. Al seleccionar "Smartphone" → aparecen campos IMEI (obligatorio), Número de Línea.
3. Al seleccionar "Monitor" → aparecen campos Pulgadas, Resolución.
4. Cambiar de tipo oculta los campos del anterior y muestra los nuevos.
5. **Sin viajes de red** al cambiar el selector (Alpine.js puro).

**Directrices Técnicas:**

```html
<!-- Estructura Alpine.js en el template de creación -->
<form x-data="{ tipoEquipo: '{{ form.tipo.value|default:'' }}' }" method="post">
    <!-- Selector principal -->
    <select name="tipo" x-model="tipoEquipo">
        <option value="">Seleccionar tipo...</option>
        <option value="notebook">Notebook</option>
        <option value="smartphone">Smartphone</option>
        <option value="monitor">Monitor</option>
    </select>

    <!-- Campos condicionales -->
    <div x-show="tipoEquipo === 'notebook'" x-transition>
        <!-- Campos: ram_gb, almacenamiento_gb, procesador -->
    </div>

    <div x-show="tipoEquipo === 'smartphone'" x-transition>
        <!-- Campos: imei (required), numero_linea -->
    </div>

    <div x-show="tipoEquipo === 'monitor'" x-transition>
        <!-- Campos: pulgadas, resolucion -->
    </div>
</form>
```

**Validación Condicional en el Backend:**
- El view de POST debe detectar el tipo y validar el form correcto.
- Usar un `DispositivoForm` base + `NotebookForm`, `SmartphoneForm`, `MonitorForm`.
- IMEI es `required=True` solo en `SmartphoneForm`.

---

### HU-12: Registro de Condición Física

**Estado actual:** El campo `notas_condicion` ya existe en el modelo.

**Qué implementar:**
1. El campo debe ser **obligatorio** en el formulario de creación.
2. En el formulario de edición, el campo viene pre-rellenado.
3. Al reasignar un equipo, solicitar actualización de la condición física.

---

### HU-13: Código QR por Equipo

**Qué construir:** Endpoint que retorna una imagen QR con la URL del equipo.

**Criterios de Aceptación:**
1. El QR apunta a la URL pública del equipo: `http://[host]/dispositivos/<id>/`.
2. Desde el slide-over del equipo, hay un botón "Ver QR" que lo muestra en un modal.
3. Hay un botón "Descargar QR" que descarga la imagen PNG.

**Directrices Técnicas:**
```python
# En dispositivos/views.py
import qrcode
import io
from django.http import HttpResponse

def dispositivo_qr(request, pk):
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    url = request.build_absolute_uri(
        reverse('dispositivos:dispositivo_detail', args=[pk])
    )
    qr_img = qrcode.make(url)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    return HttpResponse(buffer.getvalue(), content_type='image/png')
```

- Instalar: `pip install qrcode[pil]` → agregar a `requirements.txt`.
- URL: `path('<int:pk>/qr/', views.dispositivo_qr, name='dispositivo_qr')`.

---

### HU-14: Búsqueda en Vivo (Live Search)

**Qué construir:** Barra de búsqueda que filtra la tabla de inventario mientras el usuario escribe.

**Criterios de Aceptación:**
1. Busca por: Número de Serie, Identificador Interno, Nombre de Modelo, Fabricante.
2. Resultados aparecen sin recargar la página (debounce de 300ms).
3. Si no hay resultados, mostrar estado vacío elegante.

**Directrices Técnicas:**
```html
<!-- En dispositivo_list.html -->
<input type="search"
       name="q"
       placeholder="Buscar por serie, ID, modelo..."
       hx-get="{% url 'dispositivos:dispositivo_list' %}"
       hx-trigger="keyup changed delay:300ms, search"
       hx-target="#tabla-inventario"
       hx-include="this">
```

```python
# En la ListView, aplicar filtros:
def get_queryset(self):
    qs = Dispositivo.objects.filter(esta_activo=True).select_related(
        'tipo', 'modelo__fabricante', 'centro_costo', 'estado', 'propietario_actual'
    )
    q = self.request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(numero_serie__icontains=q) |
            Q(identificador_interno__icontains=q) |
            Q(modelo__nombre__icontains=q) |
            Q(modelo__fabricante__nombre__icontains=q)
        )
    return qs
```

- Si la request es HTMX (`request.htmx`): retornar solo el partial `{% include 'dispositivos/partials/tabla_inventario.html' %}`.

---

### HU-15: Bitácora de Mantenimiento

**Qué construir:** Modelo + vistas para registrar eventos de mantenimiento.

**Modelo nuevo en `dispositivos/models.py`:**
```python
class RegistroMantenimiento(models.Model):
    dispositivo       = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='mantenimientos')
    fecha             = models.DateTimeField(auto_now_add=True)
    falla_reportada   = models.TextField()
    reparacion_realizada = models.TextField(blank=True)
    tecnico_responsable  = models.ForeignKey('colaboradores.Colaborador', null=True, on_delete=models.SET_NULL)
    cambio_estado_automatico = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha']
```

**Criterios de Aceptación:**
1. Al crear registro de mantenimiento, el estado del dispositivo cambia automáticamente a "En Reparación".
2. Al registrar "reparación completada", ofrecer opción de cambiar estado a "Disponible".
3. La bitácora es visible desde el slide-over del equipo (tab o sección).

---

## Estilo Visual Requerido

Mantener el design system "Precision Console":

```css
/* Paleta base */
--jmie-orange: #F97316;
--jmie-blue: #3B82F6;
--surface: #111827;
--surface-container: #1F2937;
```

- El slide-over ocupa el 40% derecho de la pantalla en desktop, 100% en mobile.
- Los badges de estado usan el campo `color` de `EstadoDispositivo`.
- Los formularios dinámicos deben tener transiciones suaves con `x-transition` de Alpine.

---

## Entregables Esperados

Al finalizar esta Épica:

- [ ] `dispositivos/forms.py` con `DispositivoForm`, `NotebookForm`, `SmartphoneForm`, `MonitorForm`.
- [ ] Vistas actualizadas con validaciones de fecha/valor contable.
- [ ] Template `dispositivo_form.html` con Alpine.js para formularios dinámicos.
- [ ] Endpoint `dispositivo_qr` + botón en slide-over.
- [ ] Live Search funcionando en `dispositivo_list.html`.
- [ ] Modelo `RegistroMantenimiento` + migración + vistas básicas de creación y listado.
- [ ] `requirements.txt` actualizado con `qrcode[pil]`.

---

## ⚠️ Restricciones Importantes

- **NO** usar JavaScript puro para la búsqueda. Solo HTMX + Alpine.
- **NO** retornar JSON desde las vistas HTMX. Solo fragmentos HTML.
- **Sí** usar `request.htmx` (django-htmx) para detectar requests parciales.
- Todo QuerySet en vistas de lista debe filtrar `esta_activo=True`.
- El modelo `RegistroMantenimiento` es **append-only**: no implementar vistas de edición ni eliminación.
