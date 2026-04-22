# Plan de Corrección Post-Auditoría — Inventario JMIE

Corregir todos los bugs, discrepancias de nomenclatura, dependencias fantasma, archivos huérfanos y deuda técnica identificados en la auditoría del codebase.

---

## User Review Required

> [!IMPORTANT]
> **Dependencias a eliminar**: Se van a remover 11 paquetes de `requirements.txt` que no tienen uso real en el código. Si alguno tiene roadmap futuro concreto, indicalo antes de aprobar.

> [!WARNING]
> **`mcp_server` y `rest_framework`**: Se van a quitar de `INSTALLED_APPS` y de urls. Si los necesitas para desarrollo/diagnóstico, dime y los dejo con flag `DEBUG only`.

> [!CAUTION]
> **`constance`**: El prefijo `CLI_PREFIX_ID` está configurado pero nunca se lee. El plan propone **conectarlo** al `Dispositivo.save()` en vez de eliminarlo, porque es una buena idea tener el prefijo configurable. ¿Estás de acuerdo?

---

## Proposed Changes

### Fase 1 — P0: Bugs Críticos y Estabilidad

---

#### [MODIFY] [views.py](file:///c:/Users/sebas/Downloads/Proyectos%20JMIE/inventario-django/dispositivos/views.py)

**Bug L453 — `return` vacío en `dispositivo_update`**

Cuando el formulario de edición falla validación, la vista devuelve `None` (crash 500). Fix: re-renderizar el formulario con errores.

```diff
         else:
-            return
+            return render(request, 'dispositivos/dispositivo_form.html', {
+                'form': form,
+                'tech_forms': tech_forms,
+                'titulo': f'Editar {dispositivo.identificador_interno}'
+            })
```

---

#### [MODIFY] [settings.py](file:///c:/Users/sebas/Downloads/Proyectos%20JMIE/inventario-django/inventario_jmie/settings.py)

**1. Fix `DEBUG` — string vs boolean**

```diff
-DEBUG = os.getenv('DEBUG')
+DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
```

**2. Limpiar `INSTALLED_APPS` — remover apps fantasma**

```diff
 INSTALLED_APPS = [
     ...
     'constance',
     'constance.backends.database',
-    'rest_framework',
-    'mcp_server',
     'django_htmx',
     ...
 ]
```

**3. Fix `ALLOWED_HOSTS`**

```diff
-ALLOWED_HOSTS = ['*']
+ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
```

---

#### [MODIFY] [urls.py](file:///c:/Users/sebas/Downloads/Proyectos%20JMIE/inventario-django/inventario_jmie/urls.py)

**Remover ruta `/mcp/`**

```diff
-from core.views import home, error_403
+from core.views import home

 urlpatterns = [
     path('admin/', admin.site.urls),
-    path('mcp/', include('mcp_server.urls')),
     path('', home, name='home'),
     ...
 ]
```

---

### Fase 2 — P1: Higiene de Dependencias

---

#### [MODIFY] [requirements.txt](file:///c:/Users/sebas/Downloads/Proyectos%20JMIE/inventario-django/requirements.txt)

**Eliminar paquetes sin uso verificable:**

| Paquete | Razón |
|---------|-------|
| `crispy-tailwind` | Forms usan `BaseStyledForm`, crispy nunca se carga |
| `django-crispy-forms` | Idem |
| `django-debug-toolbar` | No está en INSTALLED_APPS ni urls |
| `djangorestframework` | No existen endpoints REST |
| `django-mcp-server` | Herramienta dev, removida de INSTALLED_APPS |
| `mcp` | Dependencia transitiva de django-mcp-server |
| `pyHanko` | Sin código que lo use |
| `pyhanko-certvalidator` | Idem |
| `pdfminer.six` | Sin imports |
| `pdfplumber` | Sin imports |
| `uvicorn` | Solo necesario para ASGI (no se usa) |

Además, agregar comentarios claros para categorizar las secciones (core, PDF/reporting, dev/test).

---

### Fase 3 — P1: Consistencia de Nomenclatura

---

#### [MODIFY] [forms.py](file:///c:/Users/sebas/Downloads/Proyectos%20JMIE/inventario-django/colaboradores/forms.py)

**Migrar `ColaboradorForm` a `BaseStyledForm`**

Actualmente hereda de `forms.ModelForm` y repite CSS en 9 widgets manualmente. Se cambia para heredar de `BaseStyledForm` y quitar el CSS inline redundante.

```diff
-from django import forms
-from .models import Colaborador
+from django import forms
+from .models import Colaborador
+from core.forms import BaseStyledForm

-class ColaboradorForm(forms.ModelForm):
+class ColaboradorForm(BaseStyledForm):
     class Meta:
         model = Colaborador
         fields = [
             'username', 'first_name', 'last_name', 'email',
             'rut', 'cargo', 'departamento', 'centro_costo', 'azure_id'
         ]
-        widgets = {
-            'username': forms.TextInput(attrs={
-                'class': 'w-full bg-surface-container-high ...',
-                ...
-            }),
-            ... (9 widgets con CSS repetido)
-        }
+        widgets = {
+            'username': forms.TextInput(attrs={'placeholder': 'Ej: jdoe'}),
+            'rut': forms.TextInput(attrs={'placeholder': '12.345.678-k'}),
+        }
```

`BaseStyledForm.__init__` se encarga de inyectar las clases CSS automáticamente. Solo se mantienen los `placeholder` necesarios.

---

#### [MODIFY] [views.py](file:///c:/Users/sebas/Downloads/Proyectos%20JMIE/inventario-django/actas/views.py)

**Renombrar `acta_crear` → `acta_create`** para consistencia inglés con los URL names

```diff
-def acta_crear(request):
+def acta_create(request):
```

#### [MODIFY] [urls.py](file:///c:/Users/sebas/Downloads/Proyectos%20JMIE/inventario-django/actas/urls.py)

```diff
-    path('crear/', views.acta_crear, name='acta_create'),
+    path('crear/', views.acta_create, name='acta_create'),
```

---

#### [MODIFY] [models.py](file:///c:/Users/sebas/Downloads/Proyectos%20JMIE/inventario-django/dispositivos/models.py)

**Conectar `CONSTANCE_CONFIG` al `Dispositivo.save()`**

```diff
+from constance import config
+
 def save(self, *args, **kwargs):
     if not self.identificador_interno:
-        prefix = "JMIE"
+        prefix = config.CLI_PREFIX_ID
         sigla = self.tipo.sigla if self.tipo and self.tipo.sigla else "EQUIP"
```

---

### Fase 4 — P1: Dashboard — Fix Queries No Filtradas

---

#### [MODIFY] [services.py](file:///c:/Users/sebas/Downloads/Proyectos%20JMIE/inventario-django/dashboard/services.py)

**L45-52 — Notebooks/Smartphones disponibles ignoran `filtered_qs`**

Actualmente usa `Dispositivo.objects` (ignora filtros del dashboard). Fix:

```diff
-        total_notebooks_disponibles = Dispositivo.objects.filter(
+        total_notebooks_disponibles = filtered_qs.filter(
             tipo__nombre__icontains="Notebook",
             estado__nombre__in=["Disponible", "Reservado"],
         ).count()
-        total_smartphones_disponibles = Dispositivo.objects.filter(
+        total_smartphones_disponibles = filtered_qs.filter(
             tipo__nombre__icontains="Smartphone",
```

---

### Fase 5 — P1: Limpieza de Archivos Huérfanos

---

#### [DELETE] `query_test.py` (raíz)
Script de diagnóstico suelto, no forma parte del proyecto.

#### [DELETE] `pytest_output.txt` (raíz)
Salida de test antigua guardada accidentalmente.

#### [DELETE] `stitch_dashboard_dark.html` (raíz)
Prototipo Stitch no integrado.

#### [DELETE] `stitch_inventario_dark.html` (raíz)
Prototipo Stitch no integrado.

#### [MODIFY] [.gitignore](file:///c:/Users/sebas/Downloads/Proyectos%20JMIE/inventario-django/.gitignore)

Agregar entradas para evitar que vuelvan a entrar:

```diff
 .stitch/
+scratch/
+pytest_output.txt
+stitch_*.html
+query_test.py
+skills-lock.json
```

---

### Fase 6 — P2: Optimización ORM en Views

---

#### [MODIFY] [views.py](file:///c:/Users/sebas/Downloads/Proyectos%20JMIE/inventario-django/dispositivos/views.py)

**Agregar `select_related` al listado de dispositivos**

El `dispositivo_list` consulta dispositivos sin `select_related`, generando N+1 queries al renderizar tipo, modelo, estado y propietario.

```diff
-    dispositivos = Dispositivo.objects.all()
+    dispositivos = Dispositivo.objects.select_related(
+        'tipo', 'modelo', 'modelo__fabricante', 'estado', 'propietario_actual', 'centro_costo'
+    ).all()
```

---

## Resumen de Archivos Tocados

| Fase | Archivo | Acción |
|------|---------|--------|
| 1 | `dispositivos/views.py` | Fix bug L453 |
| 1 | `inventario_jmie/settings.py` | Fix DEBUG, ALLOWED_HOSTS, INSTALLED_APPS |
| 1 | `inventario_jmie/urls.py` | Remover `/mcp/` |
| 2 | `requirements.txt` | Eliminar 11 dependencias fantasma |
| 3 | `colaboradores/forms.py` | Migrar a BaseStyledForm |
| 3 | `actas/views.py` | Renombrar `acta_crear` → `acta_create` |
| 3 | `actas/urls.py` | Actualizar referencia |
| 3 | `dispositivos/models.py` | Conectar constance.config |
| 4 | `dashboard/services.py` | Fix queries no filtradas |
| 5 | Archivos raíz (4) | Eliminar huérfanos |
| 5 | `.gitignore` | Agregar entradas |
| 6 | `dispositivos/views.py` | Agregar select_related |

---

## Verification Plan

### Automated Tests

```bash
# 1. Ejecutar suite completa (debe pasar 126+ tests)
pytest -m "not e2e" --tb=short -q

# 2. Verificar que el fix de DEBUG funciona
python -c "import os; os.environ['DEBUG']='False'; print(os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes'))"

# 3. Verificar que constance se lee correctamente
python manage.py shell -c "from constance import config; print(config.CLI_PREFIX_ID)"

# 4. Verificar imports limpios (no debe haber errores)
python manage.py check --deploy
```

### Manual Verification

- Navegar a la edición de un dispositivo, enviar formulario inválido → debe mostrar errores (no crash 500)
- Verificar que los formularios de Colaborador mantienen el estilo visual con BaseStyledForm
- Confirmar que `requirements.txt` instalación limpia funciona (`pip install -r requirements.txt`)
