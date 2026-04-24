# Database Codemap

**Last Updated:** 2026-04-24
**Entry Points:** `dispositivos/models.py`, `colaboradores/models.py`, `actas/models.py`, `core/models.py`

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Colaborador (AUTH_USER_MODEL)              │
│  AbstractUser + esta_activo + centro_costo + cargo            │
└──────┬───────────────────────────────┬───────────────────────┘
       │                               │
       │ 1:N                           │ 1:N
       ▼                               ▼
┌──────────────┐              ┌─────────────────────┐
│  Dispositivo │◄──────┐      │ HistorialAsignacion │◄───┐
│  (base)      │       │      │ dispositivo,        │    │
│              │       │      │ colaborador, acta   │    │
└──┬───┬───┬───┘       │      └─────────────────────┘    │
   │   │   │           │                                 │
   │   │   │ 1:N       │ 1:N                             │
   │   │   ▼           │                                 │
   │   │ BitacoraMan-  │      ┌─────────────────────┐    │
   │   │ tenimiento    │      │ EntregaAccesorio    │    │
   │   │               │      │ colaborador, acta   │    │
   │   └───────────────┘      └─────────────────────┘    │
   │                                                    │
   │ 1:1 (herencia manual)                              │
   ▼                                                    │
┌──────────────────────────────────┐                    │
│ Notebook │ Smartphone │ Monitor  │                    │
│ Impresora│ Servidor   │EquipoRed │                    │
└──────────────────────────────────┘                    │
                                                        │
┌──────────────────────────────────────────────────────┐│
│                    Acta                               │
│  folio, tipo_acta, colaborador, firmado,              │
│  metodo_sanitizacion, ministro_de_fe                  │
└──────────────────────────────────────────────────────┘┘
```

## Core Models

| Model | Table | Key Fields | Relationships |
|-------|-------|------------|---------------|
| `Colaborador` | `colaboradores_colaborador` | email, first_name, last_name, esta_activo, cargo | FK→CentroCosto, M2M→groups |
| `Fabricante` | `core_fabricante` | nombre | - |
| `TipoDispositivo` | `core_tipodispositivo` | nombre, sigla | - |
| `EstadoDispositivo` | `core_estadodispositivo` | nombre | - |
| `Modelo` | `core_modelo` | nombre, FK→Fabricante | FK→Fabricante |
| `CentroCosto` | `core_centrocosto` | nombre, codigo_contable | - |

## Dispositivos Models

| Model | Table | Key Fields | Relationships |
|-------|-------|------------|---------------|
| `Dispositivo` | `dispositivos_dispositivo` | identificador_interno (auto), numero_serie, fecha_compra, valor_contable, notas_condicion, foto_equipo | FK→Tipo, FK→Estado, FK→Modelo, FK→Colaborador (propietario_actual), FK→CentroCosto |
| `Notebook` | `dispositivos_notebook` | procesador, ram_gb, almacenamiento, sistema_operativo, mac_address, ip_asignada | OneToOne→Dispositivo (parent_ptr) |
| `Smartphone` | `dispositivos_smartphone` | imei_1, imei_2, numero_telefono | OneToOne→Dispositivo |
| `Impresora` | `dispositivos_impresora` | es_multifuncional, tipo_tinta, mac_address, ip_asignada | OneToOne→Dispositivo |
| `Servidor` | `dispositivos_servidor` | rack_u, configuracion_raid, procesadores_fisicos, criticidad | OneToOne→Dispositivo |
| `EquipoRed` | `dispositivos_equipored` | subtipo, firmware_version, mac_address, ip_gestion | OneToOne→Dispositivo |
| `Monitor` | `dispositivos_monitor` | pulgadas, resolucion | OneToOne→Dispositivo |
| `BitacoraMantenimiento` | `dispositivos_bitacamantenimiento` | fecha, falla_reportada, reparacion_realizada, costo_reparacion, cambio_estado_automatico | FK→Dispositivo, FK→Colaborador (tecnico) |
| `HistorialAsignacion` | `dispositivos_historialasignacion` | fecha_inicio, fecha_fin, condicion_fisica | FK→Dispositivo, FK→Colaborador, FK→Acta |
| `EntregaAccesorio` | `dispositivos_entregaaccesorio` | tipo, cantidad, descripcion, fecha | FK→Colaborador, FK→Acta |

## Actas Models

| Model | Table | Key Fields | Relationships |
|-------|-------|------------|---------------|
| `Acta` | `actas_acta` | folio (correlativo), tipo_acta, fecha, observaciones, firmada, metodo_sanitizacion | FK→Colaborador, FK→Colaborador (ministro_de_fe), FK→Colaborador (creado_por) |

## Custom QuerySets

```python
DispositivoQuerySet:
  .activos()              # Excluye 'Fuera de Inventario'
  .con_detalles()         # select_related(tipo, estado, modelo, fabricante, propietario, cc)
```

## Constraints & Validation

| Model | Constraint | Description |
|-------|------------|-------------|
| `Dispositivo` | `valor_contable_positivo` | CheckConstraint: valor_contable >= 0 |
| `Dispositivo` | `clean()` | fecha_compra no futura, valor_contable positivo |
| `Dispositivo` | `identificador_interno` | Unique, auto-generado con formato `PREFIX-SIGLA-NNNN` |
| `Smartphone` | `imei_1` | Unique |
| `Dispositivo` | `numero_serie` | Unique |

## ID Generation Logic

```python
# Dispositivo.save()
prefix = config.CLI_PREFIX_ID  # Default: 'JMIE'
sigla = tipo.sigla or 'EQUIP'
# Busca último dispositivo con misma sigla, incrementa secuencia
# Formato: JMIE-SIGLA-00001
```

## Indexes

Los modelos usan `db_index=True` en campos frecuentemente filtrados y `Meta.indexes` para índices compuestos donde aplica.

## Related Areas

- [Backend Codemap](backend.md) - Vistas y servicios que usan estos modelos
- [Integrations Codemap](integrations.md) - Cómo los modelos interactúan con servicios externos
