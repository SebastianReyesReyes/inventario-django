# App: Colaboradores

## Propósito
La aplicación `colaboradores` gestiona el modelo de usuario personalizado del sistema. Extiende el sistema de autenticación de Django para incluir información corporativa necesaria para la trazabilidad de la entrega de equipos y suministros.

## Modelo de Datos

### Colaborador
Hereda de `AbstractUser` y añade los siguientes campos:

- **rut**: Identificador único nacional (Chile). Incluye lógica de validación y formateo.
- **cargo**: Puesto de trabajo del colaborador.
- **departamento**: Relación con el modelo `Departamento` (App `core`).
- **centro_costo**: Relación con el modelo `CentroCosto` (App `core`).
- **azure_id**: Identificador para integración con Azure AD (si aplica).
- **esta_activo**: Campo booleano para manejo de baja lógica operativa.

## Funcionalidades Clave

### Baja Lógica (Soft-Delete)
El modelo `Colaborador` sobreescribe el método `delete()` para evitar la eliminación física de los registros. 
- Al "eliminar" un colaborador, se marca `esta_activo = False` y `is_active = False`.
- Esto permite mantener la integridad referencial en las actas y el historial de movimientos de inventario.

### Validación de RUT
Se incluye un formulario `ColaboradorForm` que:
- Valida el dígito verificador del RUT.
- Formatea automáticamente el RUT a un estándar con puntos y guion (ej: `12.345.678-K`).

## Administración
El panel de administración utiliza una clase personalizada `ColaboradorAdmin` que extiende `UserAdmin` para permitir la edición de los campos corporativos manteniendo la seguridad y gestión de contraseñas nativa de Django.

## Integración
Este modelo es central en el sistema, ya que se utiliza como receptor en la generación de **Actas de Entrega** y como responsable en el historial de **Dispositivos**.
