# 🤖 Agente B — Épica 4: Trazabilidad y Asignaciones (HU-16 → HU-20)

## Tu Rol
Eres un agente de desarrollo senior trabajando en el sistema de inventario IT de **JMIE** (empresa chilena). Tu tarea es implementar completamente la **Épica 4: Trazabilidad** del backlog: asignaciones, reasignaciones, devoluciones, auditoría de movimientos y entrega de accesorios.

---

## 🔧 Herramientas y Recursos — OBLIGATORIO USAR ANTES DE ESCRIBIR CÓDIGO

Lee estas skills en orden antes de comenzar. Están en `.agents/skills/`:

1. **`.agents/skills/django-patterns/SKILL.md`** — Arquitectura Django, ORM, vistas, formularios, transacciones.
2. **`.agents/skills/django-security/SKILL.md`** — Protección de vistas, CSRF, permisos. Toda vista mutacional debe estar protegida.
3. **`.agents/skills/django-verification/SKILL.md`** — Checklist de verificación antes de entregar.
4. **`.agents/skills/htmx/SKILL.md`** — Modales, side-overs, triggers, debounce, disabled-elt.
5. **`docs/STYLE_GUIDE.md`** — **Fuente de verdad** para TODO el CSS/HTML. No inventar clases, no usar colores hardcodeados. Incluye patrones de modal, timeline, badges, etc.

Además:
- **Usar MCP** disponibles para consultar documentación cuando sea necesario.
- **Explorar el proyecto con herramientas de filesystem** antes de crear archivos nuevos.

---

## 📂 Stack Tecnológico (Lo Que Está En Producción)

| Capa | Tecnología |
|:---|:---|
| **Framework** | Django 6.0.2 |
| **Base de datos** | SQLite (desarrollo) |
| **Frontend reactivo** | HTMX 2.x + Alpine.js 3.x |
| **CSS** | Tailwind CSS Play CDN con config inline en `base.html` |
| **Iconos** | Google Material Symbols Outlined |
| **Tipografía** | Montserrat (local) |
| **Auth model** | `colaboradores.Colaborador` (hereda de `AbstractUser`) |
| **HTMX middleware** | `django_htmx` instalado → `request.htmx` disponible |

---

## 📂 Contexto del Proyecto

- **Ruta**: `c:\Users\sebas\Downloads\Proyectos JMIE\inventario-django\`
- **Apps existentes**: `core`, `dispositivos`, `colaboradores`, `actas`
- **Design System**: "Precision Console" — dark mode forzado, colores JMIE. Ver `docs/STYLE_GUIDE.md`.
- **Base template**: `templates/base.html` — sidebar, topbar, containers globales.
- **Modales**: se inyectan en `#modal-container` (z-index 50)
- **Side-overs**: se inyectan en `#side-over-container` (z-index 40)
- **Formularios**: usar `BaseStyledForm` de `core/forms.py` como clase base
- **HTMX**: `request.htmx` disponible (middleware activo)

---

## 🏗️ Arquitectura Mini Apps — Decisión Clave

**Los modelos de trazabilidad van en la app `dispositivos/`** para mantener cohesión (los movimientos son de dispositivos). NO crear una app nueva — eso añadiría complejidad innecesaria.

La entrega de accesorios (`EntregaAccesorio`) también va en `dispositivos/` ya que es parte del inventario real.

> ✅ Principio de Mini Apps: `core` (catálogos), `dispositivos` (inventario + trazabilidad), `colaboradores` (personas), `actas` (documentos).

---

## 📋 Modelos Existentes Relevantes

**Lee primero estos archivos antes de crear modelos:**
- `dispositivos/models.py` — `Dispositivo`, `BitacoraMantenimiento`
- `colaboradores/models.py` — `Colaborador` (es `AUTH_USER_MODEL`)
- `core/models.py` — `EstadoDispositivo`, `CentroCosto`, etc.

Los estados actuales en la BD son (NO cambiar estos nombres):
- `"Disponible"` / `"Reservado"` → equipos asignables
- `"Asignado"` / `"En uso"` → equipos activos con colaborador
- Estados que contienen `"Reparación"` → en mantenimiento

---

## 🗃️ Modelos Nuevos a Crear

### `HistorialAsignacion` — Ledger APPEND-ONLY

```python
class HistorialAsignacion(models.Model):
    dispositivo      = models.ForeignKey('Dispositivo', on_delete=models.PROTECT, related_name='historial')
    colaborador      = models.ForeignKey('colaboradores.Colaborador', on_delete=models.PROTECT, related_name='asignaciones')
    fecha_inicio     = models.DateField(auto_now_add=True)
    fecha_fin        = models.DateField(null=True, blank=True)  # None = asignación vigente
    condicion_fisica = models.TextField()                       # SIEMPRE obligatorio
    registrado_por   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='asignaciones_registradas'
    )
    # FK a Acta para Épica 5 — ya preparada
    acta             = models.ForeignKey('actas.Acta', null=True, blank=True,
                           on_delete=models.SET_NULL, related_name='asignaciones')

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = 'Historial de Asignación'

    def __str__(self):
        return f"{self.dispositivo} → {self.colaborador} ({self.fecha_inicio})"

    # ⛔ NUNCA implementar delete() en vistas de este modelo
```

### `EntregaAccesorio` — Registro simple (solo registro, sin stock)

```python
class EntregaAccesorio(models.Model):
    """
    Registro de entrega de accesorios. Solo histórico — no hay stock que descontar.
    Tipos comunes pre-definidos (datalist), pero es texto libre.
    """
    colaborador    = models.ForeignKey('colaboradores.Colaborador', on_delete=models.PROTECT, related_name='accesorios')
    tipo           = models.CharField(max_length=100)
    cantidad       = models.PositiveIntegerField(default=1)
    descripcion    = models.TextField(blank=True)
    fecha          = models.DateField(auto_now_add=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='entregas_registradas'
    )

    class Meta:
        ordering = ['-fecha']

    TIPOS_COMUNES = [
        'Mouse', 'Teclado', 'Mochila', 'Audífonos', 'Cable HDMI',
        'Cargador', 'Mouse Pad', 'Hub USB', 'Parlantes',
    ]
```

---

## 📋 Historias de Usuario a Implementar

### HU-16: Asignar equipo (Bodega → Colaborador)

- **Activador**: Botón "Asignar" en side-over del dispositivo → abre modal en `#modal-container`
- **Validación**: Solo equipos cuyo estado sea "Disponible" o "Reservado"
- **Al guardar** (con `transaction.atomic()`):
  1. `HistorialAsignacion.objects.create(dispositivo, colaborador, condicion_fisica, registrado_por)`
  2. `dispositivo.estado = EstadoDispositivo.objects.get(nombre='Asignado')` + `dispositivo.save()`
- `condicion_fisica` es campo obligatorio
- `hx-disabled-elt="this"` en el botón submit para prevenir doble envío

---

### HU-17: Reasignar (Colaborador A → Colaborador B)

- **Un solo paso atómico** — sin pasar por bodega
- Con `transaction.atomic()`:
  1. Consultar `asignacion_vigente = dispositivo.historial.filter(fecha_fin__isnull=True).first()`
  2. Cerrar: `asignacion_vigente.fecha_fin = date.today(); asignacion_vigente.save()`
  3. Crear nuevo: `HistorialAsignacion.objects.create(nuevo_colaborador, ...)`
  4. Estado del dispositivo queda "Asignado" / "En uso" — no cambia

---

### HU-18: Devolver a Bodega

- Con `transaction.atomic()`:
  1. Cerrar `HistorialAsignacion` vigente
  2. Radio en modal: "Llega en buen estado" → estado "Disponible" / "Llega dañado" → estado con "Reparación"
  3. `dispositivo.colaborador_actual = None` si existe ese campo

---

### HU-19: Historial de Movimientos

- Timeline en el side-over del dispositivo (nueva sección/pestaña)
- También accesible desde el perfil del colaborador
- `select_related('colaborador', 'registrado_por')` obligatorio
- **Append-only visual**: sin botones de edición o eliminación

**Patrón de timeline (STYLE_GUIDE.md):**
```html
<div class="space-y-3 px-4">
    {% for mov in historial %}
    <div class="flex gap-3">
        <div class="flex flex-col items-center">
            <div class="w-2 h-2 rounded-full {% if mov.fecha_fin %}bg-jmie-gray{% else %}bg-jmie-orange{% endif %} mt-1.5 flex-shrink-0"></div>
            {% if not forloop.last %}<div class="w-px flex-1 bg-white/10 mt-1"></div>{% endif %}
        </div>
        <div class="pb-4 flex-1 min-w-0">
            <div class="flex items-center justify-between">
                <p class="text-sm font-bold text-on-background truncate">{{ mov.colaborador.get_full_name }}</p>
                {% if mov.fecha_fin %}
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/10 text-jmie-gray ml-2">Cerrado</span>
                {% else %}
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-success/20 text-success ml-2">Vigente</span>
                {% endif %}
            </div>
            <p class="text-xs text-jmie-gray mt-0.5">{{ mov.fecha_inicio }} → {{ mov.fecha_fin|default:"Actualidad" }}</p>
            <p class="text-xs text-on-surface mt-1 leading-relaxed">{{ mov.condicion_fisica }}</p>
        </div>
    </div>
    {% endfor %}
    {% empty %}
    <p class="text-sm text-jmie-gray text-center py-6">Sin movimientos registrados.</p>
    {% endempty %}
</div>
```

---

### HU-20: Entrega de Accesorios

- Acceso desde el perfil del colaborador `colaborador_detail.html`
- Tipos comunes como `<datalist>` + campo texto libre
- Formulario en modal HTMX
- Campo descripción opcional

---

## 📁 Archivos a Crear/Modificar

```
dispositivos/
├── models.py          ← MODIFICAR: agregar HistorialAsignacion + EntregaAccesorio
├── forms.py           ← MODIFICAR: AsignacionForm, ReasignacionForm, DevolucionForm, AccesorioForm
├── views.py           ← MODIFICAR: vistas de los 5 HUs
├── urls.py            ← MODIFICAR: nuevas rutas
├── migrations/
│   └── 000X_historial_entrega.py  ← CREAR
└── templates/dispositivos/partials/
    ├── asignar_modal.html           ← CREAR (HU-16)
    ├── reasignar_modal.html         ← CREAR (HU-17)
    ├── devolver_modal.html          ← CREAR (HU-18)
    ├── historial_timeline.html      ← CREAR (HU-19)
    └── accesorio_form_modal.html    ← CREAR (HU-20) — se carga desde colaborador_detail
```

---

## ✅ Criterios de Completitud

Cuando termines, verifica con la `django-verification` skill. Además:
- [ ] `python manage.py makemigrations && python manage.py migrate` sin errores
- [ ] Asignar un equipo "Disponible" → estado cambia a "Asignado" ✓
- [ ] No se puede asignar un equipo que no está "Disponible" o "Reservado" (error en form) ✓
- [ ] Reasignar cierra ciclo anterior + abre nuevo ✓
- [ ] Devolver a bodega → estado "Disponible" ✓
- [ ] Historial del equipo visible en el side-over ✓
- [ ] `condicion_fisica` obligatorio en asignar/reasignar/devolver ✓
- [ ] `transaction.atomic()` en todas las vistas mutacionales ✓
- [ ] `hx-disabled-elt="this"` en todos los botones submit ✓
- [ ] Entrega de accesorios funciona desde perfil del colaborador ✓

---

## ⚠️ Reglas Críticas

1. **NUNCA implementar `delete()` en vistas de `HistorialAsignacion`** — ledger append-only
2. **NUNCA inventar tokens de color** — usar solo los del `STYLE_GUIDE.md`
3. `transaction.atomic()` es **OBLIGATORIO** en HU-16, HU-17 y HU-18
4. `select_related` obligatorio en todas las queries con FK
5. Usar `BaseStyledForm` de `core/forms.py` como clase base de todos los formularios
6. Los accesorios son **solo registro** — no hay stock, no hay descuento
7. Dejar FK `acta` en `HistorialAsignacion` como `null=True, blank=True` para Épica 5
8. `hx-disabled-elt="this"` en **todos** los botones de submit
