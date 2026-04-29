# Poblado de Datos Iniciales y Reset de Base de Datos

Este documento describe los **management commands** disponibles para poblar el sistema con datos base (catálogos, colaboradores) y para resetear la base de datos desde cero.

---

## Flujo Recomendado para un Entorno Nuevo

```powershell
# 1. Resetear la base de datos (elimina SQLite + migraciones locales + regenera)
python manage.py reset_db --force

# 2. Poblar catálogos base (tipos, estados, centros de costo, fabricantes, modelos, admin)
python manage.py seed_db

# 3. Importar colaboradores desde CSV (sin acceso al sistema por defecto)
python manage.py import_colaboradores listado_personas_jmie.csv

# 4. Levantar el servidor
python manage.py runserver
```

---

## `reset_db` — Resetear Base de Datos SQLite

**Ubicación:** `core/management/commands/reset_db.py`

Elimina el archivo SQLite, limpia migraciones locales, regenera `makemigrations` y aplica `migrate`. **Solo compatible con SQLite**.

### Uso

```powershell
# Modo interactivo (pide confirmación)
python manage.py reset_db

# Forzar sin confirmación
python manage.py reset_db --force

# Reset + crear superusuario al finalizar
python manage.py reset_db --force --superuser
```

### Qué hace paso a paso

1. Elimina el archivo `db.sqlite3` (o el definido en `DB_PATH` / `DATABASE_URL`).
2. Elimina archivos de migración locales (`000*.py`) de las apps del proyecto (`core`, `colaboradores`, `dispositivos`, `actas`, `dashboard`, `suministros`).
3. Ejecuta `makemigrations` para regenerar las migraciones desde cero.
4. Ejecuta `migrate` para aplicarlas.
5. *(Opcional)* Corre `createsuperuser`.

### ⚠️ Precauciones

- **No usar en producción** si la base de datos es PostgreSQL/MySQL (el comando falla intencionalmente).
- **No borra** la carpeta `media/` ni archivos subidos.
- **No elimina migraciones de terceros** (Django, paquetes instalados) gracias a una heurística que detecta apps dentro del `BASE_DIR`.

---

## `seed_db` — Sembrar Catálogos Base

**Ubicación:** `core/management/commands/seed_db.py`

Puebla los catálogos esenciales para que el sistema sea usable desde el minuto 0. Es **idempotente**: puedes correrlo varias veces, solo crea lo que falta.

### Uso

```powershell
# Poblar todo (incluye usuario admin de prueba)
python manage.py seed_db

# Saltar la creación del usuario admin
python manage.py seed_db --skip-admin
```

### Qué puebla

| Catálogo | Registros | Detalle |
|----------|-----------|---------|
| **Departamentos** | 8 | Adquisiciones, Recursos Humanos, Oficina, Gerencia, Administración, TI, Prevención de riesgos, Control de Gestión |
| **Tipos de dispositivo** | 10 | Notebook (NOTE), Monitor (MONI), Smartphone (SMAR), Tablet (TABL), Impresora (IMPR), Almacenamiento (ALMA), Periferico (PERI), Router/modems (ROUT), ESCANER (ESCA), Otro (OTRO) |
| **Estados** | 5 | Disponible (#10B981), En reparación (#F59E0B), En uso (#3B82F6), Inactivo (#6B7280), Dado de baja (#EF4444) |
| **Centros de costo** | 14 | Los oficiales de JMIE (114, 218, 2308, 2309, 2401, 2403, 2501, 2502, 2503, 2504, 2506, 2507, 2601, 2602) |
| **Fabricantes** | ~40 | Dell, HP, Lenovo, Samsung, Huawei, Brother, Epson, etc. |
| **Modelos** | ~130 | Extraídos del CSV de activos reales de JMIE |
| **Constance** | 1 | `CLI_PREFIX_ID = "JMIE"` |
| **Usuario admin** | 1 | `admin` / `admin123` (superusuario, staff) — salvo que uses `--skip-admin` |

### Notas importantes

- Los modelos se crean **vinculados a su fabricante y tipo** correctamente.
- Duplicados case-insensitive se evitan (ej: `Hp`, `HP`, `hp` → un solo fabricante).
- Filas del CSV sin modelo o fabricante se saltan automáticamente.
- El comando es **atómico**: si algo falla, nada queda a medio poblar.

---

## `import_colaboradores` — Importar Personal desde CSV

**Ubicación:** `core/management/commands/import_colaboradores.py`

Importa colaboradores desde un CSV con columnas: `nombre`, `correo`, `cargo`, `departamento`.

### Formato del CSV

```csv
nombre,correo,cargo,departamento
Sebastian Reyes,s.reyes@jmie.cl,Encargado TI,TI
Andrea Melian,a.melian@jmie.cl,Asistente Prev. de Riesgos,Prevención de Riesgos
Adriana Garcia,a.garcia@jmie.cl,,
```

- **cargo** y **departamento** pueden venir vacíos.
- El departamento se busca **case-insensitive** contra los existentes en la BD.
- Si no se encuentra el departamento, se importa sin él y se avisa en consola.

### Uso

```powershell
# 1. Simular primero (dry-run)
python manage.py import_colaboradores listado_personas_jmie.csv --dry-run

# 2. Importar real (sin contraseña por defecto → no pueden loguearse)
python manage.py import_colaboradores listado_personas_jmie.csv

# 3. Importar con contraseña fija (solo si todos necesitan acceso)
python manage.py import_colaboradores listado_personas_jmie.csv --password Cambiar123

# 4. Ruta absoluta o subcarpeta
python manage.py import_colaboradores data/personal.csv
python manage.py import_colaboradores "C:\Users\sebas\Downloads\listado.csv"
```

### Comportamiento por defecto (sin `--password`)

Todos los colaboradores se crean con **`set_unusable_password()`**. Esto significa:

- **No pueden iniciar sesión** en el sistema.
- Su cuenta existe como registro de personal para asignarles equipos y generar actas.
- Un superusuario debe ir al **Admin de Django** y asignarles una contraseña manualmente para activar su acceso.

### ¿Qué pasa si el correo ya existe?

El comando **actualiza** los campos que hayan cambiado (nombre, apellido, cargo, departamento) sin sobrescribir la contraseña existente. No crea duplicados.

### Salida esperada

```
→ Leyendo C:\Users\...\listado_personas_jmie.csv...
  Filas leídas: 89
  + Sebastian Reyes (s.reyes) — sin acceso (password no utilizable)
  + Andrea Melian (a.melian) — sin acceso (password no utilizable)
  [DRY-RUN] Crearía: Adriana Garcia (a.garcia) [sin password (no login)]
✓ Importación completada: 89 creado(s), 0 actualizado(s), 0 omitido(s).
```

---

## `import_inventario` — Importar Inventario desde CSV

**Ubicación:** `core/management/commands/import_inventario.py`

Importa el inventario completo de dispositivos desde un CSV con columnas: `estado`, `fabricante`, `tipo`, `modelo`, `s/n`, `propietario`, `ubicacion`, `imei1`, `imei2`.

### Formato del CSV

```csv
estado,fabricante,tipo,modelo,s/n,propietario,ubicacion,imei1,imei2
Disponible,Dell,Notebook,Latitude 5490,4gp57s2,,114-Oficina Central,,
En uso,Lenovo,Notebook,ThinkBook 14G8 IRL,PW0H10HN,Andrea Melián,2504-Hospital Rio Bueno,,
En uso,Samsung,Smartphone,SM-A175F/DS,R5GL10YEGQN,Euris Diaz,114-Oficina Central,350901806011859,351461266011856
```

- **fabricante** puede venir vacío → se usa `GENÉRICO`.
- **modelo** puede venir vacío → se crea como `POR DEFINIR`.
- **s/n** puede venir vacío → se genera automáticamente `TEMP-0001`, `TEMP-0002`, etc.
- **propietario** puede venir vacío → el dispositivo queda sin asignar.
- **ubicacion** se parsea para extraer el código de centro de costo (ej: `114-Oficina Central` → `114`).
- **imei1/imei2** se limpian automáticamente (quita `.0`, comas, espacios).

### Uso

```powershell
# 1. Simular primero (dry-run) — altamente recomendado
python manage.py import_inventario inventario_completo.csv --dry-run

# 2. Importar real
python manage.py import_inventario inventario_completo.csv

# 3. Crear colaboradores fantasma para los no encontrados (sin password, no login)
python manage.py import_inventario inventario_completo.csv --create-missing-colaboradores

# 4. Personalizar fabricante/modelo por defecto
python manage.py import_inventario inventario_completo.csv --default-fabricante "SIN MARCA" --default-model-name "DESCONOCIDO"
```

### Matching de Colaboradores

El comando intenta asociar cada dispositivo a un colaborador existente mediante múltiples estrategias:

1. **Match exacto** del nombre completo.
2. **Primera + última palabra** contenidas en el nombre de la BD.
3. **Primera + segunda palabra** (para nombres compuestos como "María José").
4. **Substring completo** en cualquier dirección.

Si ninguna estrategia funciona, el colaborador se reporta en la sección **"Colaboradores no encontrados"** del resumen final.

### Resolución de Tipos (Fallback Inteligente)

Algunos CSVs vienen con el fabricante en la columna `tipo` (ej: `LENOVO` en vez de `Smartphone`). El comando detecta esto e infiere el tipo real del nombre del modelo:

- Si el modelo contiene `tab`, `tablet` → **Smartphone**
- Si contiene `moto`, `iphone` → **Smartphone**
- Si contiene `notebook`, `thinkpad`, `latitude` → **Notebook**
- Si contiene `monitor` → **Monitor**
- Si contiene `impresora`, `designjet` → **Impresora**
- Si contiene `router`, `modem`, `starlink` → **Router/Modems**

### Salida esperada

```
→ 245 filas leídas. Procesando...
  + JMIE-NOTE-0042 | Latitude 5410 (Dell) | S/N:8sclq73
  + JMIE-SMAR-0015 | SM-A175F/DS (Samsung) | S/N:R5GL10YEGQN
    Nuevo fabricante: Kolke
    Nuevo modelo: KES-461 (Kolke / Monitor)
  + JMIE-MONI-0023 | DS-D5027F2-1P2 (Hikvision) | S/N:30168112530
✓ Importación finalizada: 245 creado(s), 0 actualizado(s), 0 omitido(s).
  ⚠️  Colaboradores no encontrados (3):
    • Danitza Concha
    • Bernardita Oyazun
    • Leysy Astete
    Tip: Usa --create-missing-colaboradores para crear estos registros automáticamente.
```

---

## Decisiones de Diseño

### ¿Por qué no usar `RunPython` en migraciones?

Las migraciones de datos (`RunPython`) se pierden si se borran los archivos `000*.py` durante un `reset_db`. Por eso preferimos **management commands** como `seed_db`, `import_colaboradores` e `import_inventario`:

- Son **repetibles** e **idempotentes**.
- No dependen de la existencia de archivos de migración antiguos.
- Se pueden versionar y testear independientemente.

### ¿Por qué `set_unusable_password()` por defecto?

El sistema tiene dos roles distintos para un colaborador:

1. **Registro de personal** (para asignar equipos y actas).
2. **Usuario del sistema** (para loguearse y operar).

La mayoría del personal nunca necesitará acceso al panel de administración. Asignar contraseñas por defecto es un riesgo de seguridad innecesario. Con `set_unusable_password()`, el acceso se otorga **explícitamente** desde el Admin cuando realmente se necesite.

---

## Referencias

- [Modelo Colaborador](../../colaboradores/models.py)
- [Modelos de Catálogo](../../core/models.py)
- [Command `seed_db`](../../core/management/commands/seed_db.py)
- [Command `reset_db`](../../core/management/commands/reset_db.py)
- [Command `import_colaboradores`](../../core/management/commands/import_colaboradores.py)
- [Command `import_inventario`](../../core/management/commands/import_inventario.py)
