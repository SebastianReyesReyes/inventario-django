# Mejores Prácticas del Backend (Django)

Este proyecto enfatiza un código limpio y acoplado a las características de la versión contemporánea de Django (v6+). Estas son las normativas de desarrollo.

## Diseño de Vistas (Views)

Preferimos las **vistas basadas en clases (CBV - Class Based Views)** o funciones modulares decoradas. 
Todo desarrollador debe limitar lo que su vista procesa. Una vista Django solo debe enfocarse en:
1. Validar las políticas de Permisos (Quien tiene acceso).
2. Procesar el Request y recuperar datos requeridos (Desde GET o POST vía `Forms`).
3. Retornar el `Template`.

### Manejo de Formularios y Crispy Tailwind
1. **Delegar el pintado HTML en Crispy:** Todos los formularios Django (Ej: `ActaModelForm`) deben configurarse utilizando un helper: `self.helper = FormHelper()`. 
2. **Widgets consistentes:** Deberías asignar atributos específicos que facilitan las interacciones desde los constructores del Form:
    ```python
    self.fields['colaborador'].widget.attrs.update({'x-data': 'autocomplete()'})
    ```

## Modelos y Esquema: Thin Models/Fat Models
El dicho estándar suele ser *Fat Models, Thin Views*. Recomendamos situar las reglas en la "Capa de Servicio" como se vio en la Guía de Patrones, sin embargo, los modelos también necesitan validaciones estrictas:
- **Clean Methods:** Es obligatorio implementar sobre-escritura al método `clean()` de los modelos del ORM para garantizar la Integridad (Ejemplo: *Un mantenimiento que fue rechazado no puede ser cerrado*).

## Señales (Django Signals)
> [!WARNING]
> **Evitar abuso de señales**.
> 
> Usar las señales `post_save` o `pre_save` para lógica de negocio de flujo principal (Como crear el folio de una Acta después de asignar un Hardware) provoca rastreos de código desordenados.
> Reservar uso exclusivo de Signals para *Caché* o *Notificaciones E-Mail*. Para la lógica usa la capa de Servicios.

## Reglas de Control de Errores y Seguridad (Actas / CRUD)
1. **Aislamiento Semántico (Select_related / prefetch_related):** Es inmensamente vital utilizar `.select_related()` o `.prefetch_related()` para colecciones en listados con N+1 *Queries*, comúnmente utilizados en vistas de tabla de Catálogo y dashboard de Inventario.
2. **Protección de Transacciones:** Usa siempre transaccionalidad `with transaction.atomic():` en la creación masiva de asignaciones de objetos que requieran coherencia atómica (Todo o nada).
