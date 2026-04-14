# Plan de Refactorización: "Fat Views" en Dispositivos

## 1. Objetivo
Refactorizar la vista `dispositivo_create` en la aplicación `dispositivos` (`dispositivos/views.py`) para extraer la lógica de negocio (resolución de tipos de dispositivo y selección de formularios) hacia una capa de servicios o fábrica (Service Layer / Factory Pattern).

## 2. Problema Actual
Actualmente, la vista `dispositivo_create` contiene múltiples condicionales `if/elif` que dependen de los nombres en cadena ("Notebook", "Smartphone", "Monitor") del modelo `TipoDispositivo`. Esto genera los siguientes problemas:
- **Acoplamiento Fuerte:** La vista HTTP "sabe" demasiado sobre la base de datos y la jerarquía de modelos.
- **Dificultad de Mantenimiento:** Si se agrega un nuevo tipo de dispositivo (ej. "Tablet"), hay que modificar el archivo de vistas, rompiendo el Principio Abierto/Cerrado (Open/Closed Principle).
- **Falta de Reusabilidad:** Esta lógica de creación no puede ser reutilizada fácilmente desde otras partes del código (ej. comandos de management, API, importaciones masivas).

## 3. Solución Propuesta
Crear un archivo `dispositivos/services.py` (similar a la convención usada en `actas`) que exponga una clase `DispositivoService` o `DispositivoFactory`. Esta clase se encargará de:
1. Recibir los datos de la petición (POST data y FILES).
2. Determinar el tipo de dispositivo que se está creando.
3. Instanciar el formulario correcto (polimorfismo de formularios).
4. Guardar la instancia.

La vista `dispositivo_create` se reducirá a manejar el ciclo de vida HTTP (recibir el request, llamar al servicio, y retornar una redirección o renderizar errores).

## 4. Pasos de Implementación

### Paso 1: Crear `dispositivos/services.py`
```python
from django.core.exceptions import ObjectDoesNotExist
from .forms import DispositivoForm, NotebookForm, SmartphoneForm, MonitorForm
from core.models import TipoDispositivo

class DispositivoFactory:
    """Fábrica para resolver el formulario adecuado según el tipo de dispositivo."""
    
    FORM_MAP = {
        'Notebook': NotebookForm,
        'Smartphone': SmartphoneForm,
        'Monitor': MonitorForm,
    }

    @classmethod
    def get_form_class(cls, tipo_id=None):
        if not tipo_id:
            return DispositivoForm
            
        try:
            tipo = TipoDispositivo.objects.get(pk=tipo_id)
            return cls.FORM_MAP.get(tipo.nombre, DispositivoForm)
        except TipoDispositivo.DoesNotExist:
            return DispositivoForm

    @classmethod
    def create_form_instance(cls, post_data=None, files_data=None, tipo_id=None):
        """Retorna una instancia del formulario correcto inicializado."""
        FormClass = cls.get_form_class(tipo_id)
        if post_data is not None:
            return FormClass(post_data, files_data)
        return FormClass()
```

### Paso 2: Refactorizar `dispositivos/views.py`
Actualizaremos la vista para consumir la fábrica en lugar de tener la lógica incrustada:

```python
from .services import DispositivoFactory

@login_required
@permission_required('dispositivos.add_dispositivo', raise_exception=True)
def dispositivo_create(request):
    """Vista para crear un nuevo dispositivo general o específico."""
    tech_forms = {
        'notebook': NotebookTechForm(request.POST if request.method == 'POST' else None),
        'smartphone': SmartphoneTechForm(request.POST if request.method == 'POST' else None),
        'monitor': MonitorTechForm(request.POST if request.method == 'POST' else None),
    }

    if request.method == 'POST':
        tipo_id = request.POST.get('tipo')
        form = DispositivoFactory.create_form_instance(request.POST, request.FILES, tipo_id)

        if form.is_valid():
            form.save()
            return redirect('dispositivos:dispositivo_list')
    else:
        form = DispositivoFactory.create_form_instance()
    
    return render(request, 'dispositivos/dispositivo_form.html', {
        'form': form,
        'tech_forms': tech_forms,
        'titulo': 'Registrar Nuevo Equipo'
    })
```

### Paso 3: Pruebas y Validación
- Asegurarse de que la creación de un `Notebook`, `Smartphone` y un `Dispositivo` genérico desde la interfaz siga funcionando correctamente y asigne los atributos de la clase hija a nivel de base de datos.
- (Opcional) Mover también la lógica de inicialización de `tech_forms` (diccionario con formularios técnicos) al servicio en el futuro si se desea abstraer completamente.

## 5. Rollback
Si se detecta un fallo, el rollback consistiría simplemente en revertir los cambios en `dispositivos/views.py` usando Git (`git checkout -- dispositivos/views.py`) y borrar o ignorar el archivo `services.py`.
