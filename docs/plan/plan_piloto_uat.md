# Plan de Piloto UAT (Pruebas de Aceptación de Usuario)

> **Objetivo**: Desplegar el sistema en un entorno controlado para que un grupo reducido de usuarios reales lo utilice con datos reales, validar el flujo operativo de negocio y recolectar feedback temprano antes del pase a producción (V1).

Este plan complementa el **Plan Maestro** aislando únicamente los componentes estrictamente necesarios para salir a la luz de forma segura, postergando la deuda técnica interna.

---

## 1. Prerrequisitos Técnicos (Bloqueantes)
*Basado en la Fase 0 y 1 del Plan Maestro. Requisitos mínimos de software para no corromper datos ni perder visibilidad.*

- [ ] **Asegurar transaccionalidad (`@transaction.atomic`)**: Aplicar en `dispositivo_create` y `dispositivo_update`. Evita que un equipo quede registrado a medias si falla un paso.
- [ ] **Protección de Borrado (IntegrityError)**: Interceptar borrados de registros con dependencias y mostrar un *toast* (ej. "No se puede borrar porque tiene historial") en vez de un Crash 500.
- [ ] **Configurar Logging de Seguridad**: Generar el archivo `inventario.log`. Vital para investigar si un usuario reporta "le di al botón y desapareció".
- [ ] **Validación de Variables Críticas**: Asegurar que si falta `SECRET_KEY` o `ALLOWED_HOSTS`, la app no arranque, en lugar de arrancar vulnerable.
- [ ] **Validador de RUT (Deseable)**: Ya que se emitirán actas en PDF, asegurar que los RUTs ingresados sean válidos comercialmente.

---

## 2. Preparación del Entorno (Infraestructura)

Dado que es un piloto, no se requiere la arquitectura final de alta disponibilidad.

- **Servidor**: Un VPS básico (ej. DigitalOcean, Linode) o despliegue en la intranet local de la empresa.
- **Base de Datos**: Continuar con **SQLite** (funciona perfecto para pilotos de < 15 usuarios concurrentes).
- **Despliegue**: Usar Gunicorn detrás de un Nginx inverso.
- **Respaldo Automático**: Un script Cron simple que copie el archivo `db.sqlite3` y la carpeta `media/` a un directorio seguro (o S3) cada 12 horas. 

---

## 3. Preparación de Datos Reales (Data Seeding)

Para que la prueba sea realista, el sistema no puede estar vacío. Se deben cargar las estructuras organizacionales de la empresa.

- [ ] **Carga de Catálogos Base (Admin/Django Shell)**:
  - Fabricantes y Modelos comunes (Dell, HP, Lenovo, Apple, etc.).
  - Tipos de Dispositivo (Notebook, Smartphone, Monitor).
  - Centros de Costo reales.
  - Estados (Disponible, Asignado, En Reparación, Baja, Perdido).
- [ ] **Carga de Colaboradores Piloto**:
  - Crear los usuarios que participarán en la prueba con sus cargos y departamentos reales.
- [ ] **Migración Inicial de Dispositivos (Opcional)**:
  - Ingresar manualmente (o mediante un script básico) un lote inicial de 10-20 equipos reales para que los usuarios tengan algo que buscar, asignar y reasignar.

---

## 4. Estrategia de Ejecución del Piloto

### 4.1. Selección de Usuarios (Beta Testers)
- **1-2 Perfiles Técnicos / Administradores de IT**: Los que registran compras y configuran equipos.
- **1 Auditor / RRHH**: Perfil que necesita consultar inventario o extraer informes, pero sin permisos para mutar datos.
- **1-2 Usuarios Finales (Opcional)**: Si el sistema contempla que el empleado se loguee a firmar o revisar, incluir a un par de empleados estándar.

### 4.2. Escenarios de Prueba a Validar (UAT)
A los usuarios no se les dice "prueba el sistema", se les pide que completen misiones específicas:

1. **Misión de Ingreso**: Recibir un lote de 3 notebooks nuevos, registrarlos en el sistema y dejarlos "Disponibles".
2. **Misión de Asignación**: Entregar un notebook y un accesorio a un empleado nuevo. **(Validar Acta Legal PDF)**.
3. **Misión de Mantenimiento**: Pasar un smartphone de "Asignado" a "En Reparación", documentar la falla.
4. **Misión de Reasignación/Devolución**: Un empleado se va de la empresa, devolver su equipo y reasignarlo a un empleado temporal.
5. **Misión Auditoría**: Generar el reporte Excel de fin de mes desde el Dashboard.

---

## 5. Recolección de Feedback e Iteración

- **Canal Único de Reportes**: Crear un canal en Slack/Teams o un documento compartido específico ("Piloto Inventario JMIE - Bugs").
- **Clasificación del Feedback**:
  - *Crash/Bloqueo*: Solucionar el mismo día. (Acá brilla el `inventario.log` implementado en el punto 1).
  - *Fricción UX*: Anotar para la V1 (Ej: "Sería bueno que al buscar autocomplete esto").
  - *Falta de feature*: Evaluar contra el backlog (Ej: "Necesitamos escanear código de barras con la cámara web").

---

## 6. Cierre del Piloto y Pase a Producción

Una vez los usuarios completen las misiones y validen que el flujo lógico (Equipos -> Asignación -> Acta) se comporta como en la vida real:

1. Evaluar si la Base de Datos del piloto (`db.sqlite3`) se purga para iniciar en blanco, o si esos datos piloto son reales y se conservan.
2. Iniciar la migración a **PostgreSQL** (Fase 5 del Plan Maestro) aprovechando que ya se comprobó el modelo de negocio.
3. Implementar las mejoras de **Performance** y **Limpieza de Código** (Fase 3 y 4 del Plan Maestro) como parte del proceso de V1 final.
