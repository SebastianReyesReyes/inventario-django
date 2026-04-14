# 🤖 Agente A — Épica 7: Seguridad y Control de Accesos (HU-27 + HU-28)

## Tu Rol
Eres un agente de desarrollo senior trabajando en el sistema de inventario IT de **JMIE** (empresa chilena). Tu tarea es implementar completamente la **Épica 7: Seguridad** del backlog.

---

## 🔧 Herramientas y Recursos — OBLIGATORIO USAR ANTES DE ESCRIBIR CÓDIGO

Lee estas skills en orden antes de comenzar. Están en `.agents/skills/`:

1. **`.agents/skills/django-patterns/SKILL.md`** — Arquitectura Django, ORM, vistas, formularios.
2. **`.agents/skills/django-security/SKILL.md`** — Autenticación, permisos, roles, CSRF, headers de seguridad. **Crítica para esta épica.**
3. **`.agents/skills/django-verification/SKILL.md`** — Checklist de verificación antes de entregar.
4. **`.agents/skills/htmx/SKILL.md`** — Formularios y peticiones HTMX.
5. **`docs/STYLE_GUIDE.md`** — **Fuente de verdad** para TODO el CSS/HTML. No inventar clases, no usar colores hardcodeados.

Además:
- **Usar MCP** disponibles para consultar documentación cuando sea necesario.
- **Explorar el proyecto con herramientas de filesystem** antes de crear archivos.

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
| **Auth model** | `colaboradores.Colaborador` (es el `AUTH_USER_MODEL`) |
| **HTMX middleware** | `django_htmx` instalado → `request.htmx` disponible |

---

## 📂 Contexto del Proyecto

- **Ruta**: `c:\Users\sebas\Downloads\Proyectos JMIE\inventario-django\`
- **Apps existentes**: `core`, `dispositivos`, `colaboradores`, `actas`
- **Design System**: "Precision Console" — dark mode forzado, colores JMIE. Ver `docs/STYLE_GUIDE.md`.
- **Base template**: `templates/base.html` — contiene sidebar, topbar, containers HTMX.
- **Modales**: se inyectan en `#modal-container` (z-index 50)
- **Side-overs**: se inyectan en `#side-over-container` (z-index 40)
- **Formularios**: usar `BaseStyledForm` de `core/forms.py` como clase base
- **HTMX**: `request.htmx` está disponible (middleware activo). `request.headers.get('HX-Request')` también funciona.

---

## 🏗️ Arquitectura Mini Apps — Decisión Clave

**La seguridad NO necesita ser una app separada.** El login/logout usa las vistas built-in de Django (`django.contrib.auth.views`) que van en `inventario_jmie/urls.py`. Los grupos y permisos son del sistema de auth de Django.

Sin embargo, **sí debes crear un template independiente** para login (`templates/auth/login.html`) ya que es una pantalla que no usa el sidebar ni el topbar del `base.html`.

> ✅ Resumen: No crear una nueva app. Usar `django.contrib.auth` + `core/migrations/` para la data migration de grupos.

---

## 📋 Historias de Usuario a Implementar

### HU-27: Autenticación (Login / Logout)

**Decisiones ya tomadas:**
- NO hay registro público — el administrador crea usuarios desde `/admin/`
- NO integrar Entra ID (Azure AD) por ahora — dejar comentario `# TODO: Entra ID - futura integración`
- `AUTH_USER_MODEL = 'colaboradores.Colaborador'` — el Colaborador ya ES el usuario de Django

**Implementación:**
```python
# inventario_jmie/urls.py — agregar:
from django.contrib.auth import views as auth_views

urlpatterns += [
    path('login/',  auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

# inventario_jmie/settings.py — agregar:
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
```

**Decorar TODAS las vistas existentes** con `@login_required`:
- `core/views.py` — todas las funciones
- `dispositivos/views.py` — todas las funciones
- `colaboradores/views.py` — todas las funciones

> ⚠️ `Colaborador` ya hereda de `AbstractUser` — revisar `colaboradores/models.py` antes de tocar nada.

**Template `templates/auth/login.html`** — NO extiende `base.html`:
- Pantalla completa sin sidebar ni topbar
- Diseño split: izquierda branding JMIE, derecha formulario
- Fondo `bg-background` (#0a0c14) — dark mode Precision Console
- Logo: `{% static 'img/logoBlanco.png' %}`
- Input usuario + input password con clases del STYLE_GUIDE
- Botón submit: CTA Primario naranja
- Link "Volver al inicio" oculto — usuarios técnicos saben la URL
- Mensaje de error si credenciales incorrectas (usar `form.non_field_errors`)

---

### HU-28: Roles Granulares

**Los 3 grupos a crear (data migration):**

| Grupo Django | Descripción | Permisos |
|:---|:---|:---|
| `Administradores` | Control total | Todos: add, change, view, delete en todas las apps |
| `Técnicos` | Mantenimiento y registro | add/change `Dispositivo`, add `BitacoraMantenimiento`, view todo |
| `Auditores` | Solo lectura | Solo `view_*` en todas las apps. Ningún botón mutacional visible |

**Crear: `core/migrations/0005_seed_grupos_permisos.py`**
```python
from django.db import migrations

def crear_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    
    # Técnicos
    tecnicos, _ = Group.objects.get_or_create(name='Técnicos')
    perms_tecnicos = Permission.objects.filter(codename__in=[
        'add_dispositivo', 'change_dispositivo', 'view_dispositivo',
        'add_bitacomantenimiento', 'view_bitacomantenimiento',
        'view_colaborador', 'view_centrocosto', 'view_tipodispositivo',
    ])
    tecnicos.permissions.set(perms_tecnicos)
    
    # Administradores — todos los permisos
    admins, _ = Group.objects.get_or_create(name='Administradores')
    admins.permissions.set(Permission.objects.all())
    
    # Auditores — solo view
    auditores, _ = Group.objects.get_or_create(name='Auditores')
    perms_view = Permission.objects.filter(codename__startswith='view_')
    auditores.permissions.set(perms_view)

class Migration(migrations.Migration):
    dependencies = [('core', '0004_seed_estados')]
    operations = [migrations.RunPython(crear_grupos, migrations.RunPython.noop)]
```

**En templates — ocultar botones según permiso:**
```html
{% if perms.dispositivos.add_dispositivo %}
    <a href="{% url 'dispositivos:dispositivo_create' %}">Nuevo Equipo</a>
{% endif %}

{% if perms.colaboradores.change_colaborador %}
    <button hx-get="...">Editar</button>
{% endif %}
```

**Vistas mutacionales (POST/PUT/DELETE) — proteger con:**
```python
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('dispositivos.add_dispositivo', raise_exception=True)
def dispositivo_create(request): ...
```

---

## 📁 Archivos a Crear/Modificar

```
inventario_jmie/
├── urls.py          ← MODIFICAR: agregar login/logout
└── settings.py      ← MODIFICAR: LOGIN_URL, LOGIN_REDIRECT_URL, LOGOUT_REDIRECT_URL

templates/auth/
└── login.html       ← CREAR: pantalla propia Precision Console sin base.html

core/migrations/
└── 0005_seed_grupos_permisos.py  ← CREAR: data migration

# MODIFICAR (agregar @login_required + @permission_required donde corresponda):
core/views.py
dispositivos/views.py
colaboradores/views.py
```

---

## ✅ Criterios de Completitud

Cuando termines, verifica con la `django-verification` skill. Además:
- [ ] `python manage.py runserver` sin errores
- [ ] Acceder a `/` sin sesión → redirige a `/login/`
- [ ] Login con un `Colaborador` que tenga `is_staff=True` funciona
- [ ] Logout redirige a `/login/`
- [ ] `login.html` tiene diseño Precision Console dark mode
- [ ] `python manage.py migrate` aplica `0005_seed_grupos_permisos` sin errores
- [ ] Los 3 grupos existen en `/admin/auth/group/`
- [ ] Un `Colaborador` del grupo Auditores no ve botones de creación/edición

---

## ⚠️ Reglas Críticas

1. `Colaborador` es el `AUTH_USER_MODEL` — NO crear un modelo `User` nuevo
2. **NUNCA** inventar tokens de color — usar solo los del `STYLE_GUIDE.md`
3. Botones del Auditor = **ocultos en template** con `{% if perms.app.permiso %}`, no solo deshabilitados
4. El template `login.html` es independiente — NO extiende `base.html`
5. Usar `BaseStyledForm` de `core/forms.py` para el `AuthenticationForm` si lo personalizas
6. No instalar librerías externas para auth — usar `django.contrib.auth` nativo
