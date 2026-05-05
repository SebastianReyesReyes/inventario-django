# App Dispositivos

Esta aplicación gestiona el inventario físico de equipos tecnológicos, permitiendo un control detallado sobre sus especificaciones técnicas, estado actual, historial de asignaciones y mantenimientos.

## Características Principales

- **Inventario Polimórfico**: Uso de herencia multi-tabla para manejar diferentes tipos de hardware con campos específicos.
- **Trazabilidad Completa**: Registro automático de cada cambio de manos (asignación, reasignación, devolución).
- **Generación de ID Interno**: Secuenciación automática basada en el tipo de equipo (ej: JMIE-NBK-0001).
- **Códigos QR**: Generación dinámica de códigos QR por equipo para acceso rápido a la ficha técnica.
- **Bitácora de Mantenimiento**: Historial de fallas y reparaciones.

## Estructura de Modelos

### Jerarquía Polimórfica
El modelo base es `Dispositivo`, del cual heredan modelos especializados:
- **Notebook**: Procesador, RAM, Almacenamiento, SO, MAC/IP.
- **Smartphone**: IMEI 1/2, Número de teléfono.
- **Monitor**: Pulgadas, Resolución.
- **Impresora**: Tipo de tinta, multifuncionalidad, MAC/IP.
- **Servidor**: Ubicación en rack, RAID, procesadores físicos, criticidad.
- **EquipoRed**: Subtipo (Switch/AP/etc), Firmware, MAC/IP.

### Modelos de Soporte
- `BitacoraMantenimiento`: Registro de reparaciones y costos.
- `HistorialAsignacion`: Línea de tiempo de quién ha tenido el equipo.
- `EntregaAccesorio`: Control de periféricos (mouse, teclados, mochilas, etc.) entregados a colaboradores.

## Lógica de Negocio (Services)

### DispositivoFactory
Ubicado en `services.py`, resuelve dinámicamente qué formulario usar según el `TipoDispositivo`. Facilita la creación y edición de equipos especializados sin duplicar lógica en las vistas.

### TrazabilidadService
Encapsula las operaciones transaccionales de:
- **Asignar**: Cambia estado a 'Asignado', establece propietario y crea registro en historial.
- **Reasignar**: Cierra asignación anterior y abre una nueva para el nuevo colaborador.
- **Devolver**: Libera el equipo (vuelve a 'Disponible' o 'En Reparación') y cierra el historial.

### DispositivoService
Maneja el registro y actualización de equipos, integrándose con `ActaService` para generar documentos PDF de entrega/devolución de forma opcional y atómica.

## Automatización (Signals)

La aplicación utiliza signals (`post_save`) para asegurar que la trazabilidad nunca se pierda:
- Cualquier cambio en el campo `propietario_actual` de un `Dispositivo` dispara la creación o cierre de registros en `HistorialAsignacion`.
- Esto garantiza que incluso si se edita un equipo desde el Admin de Django, el historial se mantenga íntegro.

## Integraciones

- **QR Codes**: La vista `dispositivo_qr` genera una imagen PNG dinámica con el enlace al detalle del equipo.
- **Actas**: Conexión directa con la app de `actas` para la generación de comprobantes legales de entrega.
