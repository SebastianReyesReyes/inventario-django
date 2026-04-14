# Agente C — Épica 7: Seguridad y Control de Accesos (RBAC)

## Contexto del Proyecto

Eres un agente de desarrollo especializado trabajando en **Sistema de Inventario JMIE**, una aplicación Django para gestión de activos de TI en una empresa de construcción.

**Stack Tecnológico:**
- Backend: Django 6.x + Python 3.14
- Frontend: HTMX + Alpine.js + Tailwind CSS
- Diseño: "Precision Console" — dark mode corporativo, tonos JMIE (naranja/azul oscuro)
- Auth: `django.contrib.auth` nativo + modelo `Colaborador` como `AUTH_USER_MODEL`
- **Principio de Desarrollo:** Aplicar DRY (Don't Repeat Yourself) y mantener la estructura de "Mini Apps" modular para facilitar el mantenimiento.
- App principal donde trabajas: Transversal (todas las apps)

**Arquitectura de Apps Django:**
```
inventario_jmie/   ← settings.py, urls raíz
core/              ← TipoDispositivo, CentroCosto, Fabricante, Modelo, EstadoDispositivo
colaboradores/     ← Colaborador (AbstractUser) — AUTH_USER_MODEL
dispositivos/      ← Dispositivo + subclases
actas/             ← Actas de entrega PDF
```

**Modelo de Usuario (`colaboradores/models.py`):**
```python
class Colaborador(AbstractUser):
    rut              = models.CharField(max_length=12, unique=True)
    cargo            = models.CharField(max_length=100, blank=True)
    departamento     = models.ForeignKey('core.Departamento', null=True, on_delete=models.SET_NULL)
    centro_costo     = models.ForeignKey('core.CentroCosto', null=True, on_delete=models.SET_NULL)
    azure_id         = models.CharField(max_length=100, null=True, blank=True, unique=True)
    # is_active heredado de AbstractUser — usado para baja lógica

    @property
    def nombre_completo(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
```

**Settings relevantes ya configurados:**
```python
AUTH_USER_MODEL = 'colaboradores.Colaborador'
ALLOWED_HOSTS = ['*']  # Dev — en prod cambiar
```

---

## Tu Misión: Épica 7 — Seguridad y Control de Accesos

Implementar el sistema completo de **autenticación + autorización granular** basado en Grupos de Django. Esta épica es transversal: afecta TODAS las vistas del sistema.

---

## Historias de Usuario a Implementar

### HU-27: Autenticación (Login / Logout)

**Qué construir:** Pantalla de login corporativa + protección de todas las vistas.

**Criterios de Aceptación:**
1. Sin credenciales válidas, cualquier URL redirige a `/login/`.
2. Login exitoso redirige al dashboard (`/`).
3. El username mostrado en el nav es el `nombre_completo` del colaborador.
4. Botón de logout visible en el nav.

**Directrices Técnicas:**

```python
# En inventario_jmie/urls.py — agregar:
from django.contrib.auth import views as auth_views

urlpatterns += [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
```

```python
# En settings.py — agregar:
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
```

**Template `templates/login.html`:**
- Diseño fullscreen dark con el logo JMIE centrado.
- Formulario con campos Username y Password.
- Botón de submit naranja JMIE.
- Sin registro público (solo Admin puede crear usuarios desde Django Admin o UI).

**Protección de Vistas:**
```python
# Para vistas basadas en funciones:
from django.contrib.auth.decorators import login_required

@login_required
def mi_vista(request):
    ...

# Para vistas basadas en clases:
from django.contrib.auth.mixins import LoginRequiredMixin

class MiListView(LoginRequiredMixin, ListView):
    ...
```

> **CRÍTICO:** Aplicar `@login_required` o `LoginRequiredMixin` a **TODAS** las vistas de todas las apps. No dejar ninguna vista pública excepto `login/` y `logout/`.

---

### HU-28: Roles Granulares (RBAC)

**Qué construir:** Sistema de roles basado en Grupos de Django con la siguiente matriz de permisos:

| Capacidad | Técnico | Administrador | Auditor |
|-----------|---------|---------------|---------|
| Ver inventario, dashboard, historiales | ✅ | ✅ | ✅ |
| Crear/editar equipos | ✅ | ✅ | ❌ |
| Registrar mantenimiento | ✅ | ✅ | ❌ |
| Asignar/reasignar equipos | ❌ | ✅ | ❌ |
| Generar actas/PDF | ❌ | ✅ | ❌ |
| Baja lógica de equipos y personal | ❌ | ✅ (exclusivo) | ❌ |
| Ver botones de acción mutacional | Limitado | ✅ | ❌ (ocultos) |

**Directrices Técnicas:**

#### 1. Configurar los 3 Grupos en una Data Migration

```python
# En colaboradores/migrations/XXXX_create_groups.py
from django.db import migrations

def create_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    # Crear grupos
    admin_group, _ = Group.objects.get_or_create(name='Administradores')
    tech_group, _  = Group.objects.get_or_create(name='Técnicos')
    audit_group, _ = Group.objects.get_or_create(name='Auditoría')

    # Asignar permisos a Administradores: todos los de dispositivos, colaboradores, core, actas
    admin_perms = Permission.objects.filter(
        content_type__app_label__in=['dispositivos', 'colaboradores', 'core', 'actas']
    )
    admin_group.permissions.set(admin_perms)

    # Técnicos: solo add/change de dispositivos, sin delete ni assign/reassign
    tech_perms = Permission.objects.filter(
        content_type__app_label='dispositivos',
        codename__in=['add_dispositivo', 'change_dispositivo', 'add_registromantenimiento']
    )
    tech_group.permissions.set(tech_perms)

    # Auditoría: solo permisos de vista (view_*)
    audit_perms = Permission.objects.filter(codename__startswith='view_')
    audit_group.permissions.set(audit_perms)

class Migration(migrations.Migration):
    dependencies = [('colaboradores', '0001_initial')]
    operations = [migrations.RunPython(create_groups, migrations.RunPython.noop)]
```

#### 2. Proteger Vistas Mutacionales con PermissionRequiredMixin

```python
from django.contrib.auth.mixins import PermissionRequiredMixin

# Vistas que solo Administradores pueden usar:
class DispositivoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'dispositivos.delete_dispositivo'
    raise_exception = True  # Retorna 403 en lugar de redirigir a login

class AsignarDispositivoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'dispositivos.change_dispositivo'
    raise_exception = True

# Para funciones:
from django.contrib.auth.decorators import permission_required

@login_required
@permission_required('actas.add_acta', raise_exception=True)
def generar_acta(request):
    ...
```

#### 3. Ocultar Botones en Templates según Permisos

```html
<!-- En cualquier template — mostrar botones solo si tiene permiso -->

<!-- Botón Editar — Técnicos y Administradores -->
{% if perms.dispositivos.change_dispositivo %}
<button hx-get="{% url 'dispositivos:dispositivo_edit' d.pk %}" ...>
    Editar
</button>
{% endif %}

<!-- Botón Asignar — Solo Administradores -->
{% if perms.dispositivos.change_dispositivo and request.user.groups.filter(name='Administradores').exists %}
<button ...>Asignar</button>
{% endif %}

<!-- Botón Baja — Solo Administradores -->
{% if request.user.groups.filter(name='Administradores').exists %}
<button class="text-red-400" ...>Dar de Baja</button>
{% endif %}
```

> **CRÍTICO para Auditoría:** Los auditores **no deben ver ningún botón de acción**. El template no debe renderizar ni siquiera el HTML oculto de los botones mutacionales.

#### 4. Página de Error 403

```python
# En inventario_jmie/views.py
def error_403(request, exception):
    return render(request, '403.html', status=403)

# En urls.py principal:
handler403 = 'inventario_jmie.views.error_403'
```

Template `templates/403.html`: Pantalla corporativa JMIE con icono de candado, mensaje claro y botón para volver al dashboard.

#### 5. Helper de Contexto para Templates (Opcional pero Recomendado)

```python
# En inventario_jmie/context_processors.py
def user_roles(request):
    if not request.user.is_authenticated:
        return {}
    groups = list(request.user.groups.values_list('name', flat=True))
    return {
        'is_admin': 'Administradores' in groups,
        'is_tecnico': 'Técnicos' in groups,
        'is_auditor': 'Auditoría' in groups,
    }

# En settings.py → TEMPLATES → OPTIONS → context_processors:
# 'inventario_jmie.context_processors.user_roles',
```

Uso en templates: `{% if is_admin %}...{% endif %}` (más legible que el filter de groups).

---

## Configuraciones Adicionales en settings.py

```python
# Seguridad básica para red interna
SESSION_COOKIE_AGE = 28800           # Sesión expira en 8 horas
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_HTTPONLY = True

# Redireccionamiento post-login
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
```

---

## Estilo Visual Requerido

**Pantalla de Login:**
- Fondo: `#0D1117` (casi negro)
- Card centrada con glassmorphism: `background: rgba(31, 41, 55, 0.8); backdrop-filter: blur(12px);`
- Logo JMIE en la parte superior del card
- Campos de formulario con borde `border-white/10`, foco con `border-jmie-orange`
- Botón submit: `background: #F97316` (naranja JMIE)

**Pantalla 403:**
- Mismo fondo que login
- Ícono de candado grande (Material Symbols: `lock`)
- Título: "Acceso Restringido"
- Subtítulo explicativo
- Botón "Volver al Inicio" en naranja

**Nav Bar (ya existente — solo actualizar):**
- Mostrar `{{ request.user.nombre_completo }}` o `{{ request.user.username }}`
- Badge de rol visible: ej. `<span class="badge">Admin</span>` en naranja
- Botón Logout con ícono `logout`

---

## Entregables Esperados

Al finalizar esta Épica:

- [ ] Templates: `login.html` y `403.html` con diseño Precision Console.
- [ ] Data migration para creación de los 3 grupos + permisos.
- [ ] `LoginRequiredMixin` / `@login_required` en **todas** las vistas de todas las apps.
- [ ] `PermissionRequiredMixin` en vistas mutacionales de `dispositivos/` y `actas/`.
- [ ] Context processor `user_roles` registrado en settings.
- [ ] `handler403` configurado.
- [ ] Settings de sesión y CSRF configurados.
- [ ] Templates actualizados para ocultar botones según rol.

---

## ⚠️ Restricciones Importantes

- **NO** crear un sistema de auth propio. Usar 100% `django.contrib.auth` (Grupos + Permisos).
- **NO** usar `is_staff` o `is_superuser` como mecanismo de roles. Usar solo Grupos.
- **NO** dejar vistas sin `LoginRequiredMixin`. Si ves una vista sin él, agrégalo.
- Los auditores deben ver **cero** botones de acción en el DOM. No solo ocultos con CSS.
- Toda acción mutacional (POST, PUT, DELETE) debe validar permisos en el backend **además** de ocultarlos en la UI. La seguridad no puede depender solo del frontend.
