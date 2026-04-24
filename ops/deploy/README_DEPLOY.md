# Guía de Despliegue con Docker (Piloto UAT)

> **Ambiente objetivo:** Servidor local con Docker + Docker Compose instalado (Ubuntu/Debian).
> **Base de datos:** SQLite (persistida en volumen del host).
> **Stack:** Django + Gunicorn + Nginx (contenedores).

---

## Requisitos Previos

- Docker Engine 24.0+
- Docker Compose 2.20+
- Git (para clonar el repositorio)
- Un archivo `.env` válido en la raíz del proyecto (ver `.env.example`)

---

## Estructura de Directorios en el Servidor

```bash
/var/www/inventario-django/          # Código del proyecto
├── data/                             # DATOS PERSISTENTES (no borrar)
│   ├── db.sqlite3                    # Base de datos
│   ├── media/                        # Archivos subidos
│   └── inventario.log                # Logs de seguridad
├── docker-compose.yml
├── Dockerfile
└── ops/
    └── docker/
        ├── nginx.conf                # Configuración de Nginx
        └── entrypoint.sh             # Inicio de Django
```

---

## Pasos de Despliegue

### 1. Clonar el proyecto

```bash
cd /var/www
git clone <url-del-repo> inventario-django
cd inventario-django
```

### 2. Crear el archivo de entorno

```bash
cp .env.example .env
nano .env
```

**Variables mínimas obligatorias:**
```env
SECRET_KEY=tu-clave-segura-de-50-caracteres-o-mas
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100,tu-dominio.local
```

> **IMPORTANTE:** Reemplaza `192.168.1.100` por la IP real de tu servidor local. Si no defines `ALLOWED_HOSTS` correctamente, Django rechazará las peticiones.

### 3. Crear directorio de datos persistentes

```bash
mkdir -p data/media
```

> **Nota:** No necesitas crear `db.sqlite3` manualmente. Django la creará automáticamente en `data/db.sqlite3` al ejecutar las migraciones por primera vez.

### 4. Construir e iniciar los contenedores

```bash
# Primera vez: construir imágenes y levantar
docker compose up -d --build

# Verificar que estén corriendo
docker compose ps

# Ver logs en tiempo real
docker compose logs -f web
docker compose logs -f nginx
```

### 5. Crear el superusuario (primera vez)

```bash
docker compose exec web python manage.py createsuperuser
```

### 6. Acceder al sistema

Abre tu navegador en:
```
http://<ip-del-servidor>
```

O si estás en la misma máquina:
```
http://localhost
```

---

## Comandos de Mantenimiento Útiles

### Aplicar migraciones manualmente
```bash
docker compose exec web python manage.py migrate
```

### Recolectar estáticos manualmente
```bash
docker compose exec web python manage.py collectstatic --noinput
```

### Ejecutar tests
```bash
docker compose exec web pytest -m "not e2e"
```

### Importar datos desde CSV/Excel
```bash
# Verificar primero
docker compose exec web python manage.py import_devices /app/data/export_sharepoint.csv --dry-run

# Ejecutar importación
docker compose exec web python manage.py import_devices /app/data/export_sharepoint.csv
```

> **Nota:** Coloca tus archivos CSV/Excel en la carpeta `data/` del host para que estén accesibles dentro del contenedor en `/app/data/`.

### Ver shell de Django
```bash
docker compose exec web python manage.py shell
```

### Backup manual de la base de datos
```bash
# El backup se guarda en el directorio donde ejecutes el comando
docker compose exec web cat /app/db.sqlite3 > backup_$(date +%Y%m%d_%H%M).sqlite3
```

### Restaurar backup
```bash
# Detener contenedores
docker compose down

# Restaurar archivo
cp backup_20240115_1430.sqlite3 data/db.sqlite3

# Levantar contenedores
docker compose up -d
```

---

## Configuración del Backup Automático (en el HOST)

El contenedor deja la base de datos y los archivos media en el directorio `data/` del host. Puedes programar un backup simple con cron en el servidor:

```bash
sudo crontab -e
```

Agregar:
```cron
# Backup de Inventario JMIE cada 12 horas
0 */12 * * * /bin/bash -c 'cd /var/www/inventario-django && tar -czf /var/backups/inventario/inventario_$(date +\%Y-\%m-\%d_\%H-\%M).tar.gz data/db.sqlite3 data/media/' 2>/dev/null
```

Crear directorio de backups:
```bash
sudo mkdir -p /var/backups/inventario
```

### Permisos de directorios (importante)

El contenedor corre con un usuario no-root (`django`, UID 999). Asegúrate de que el directorio `data/` tenga permisos de escritura:

```bash
# Opción A: Cambiar propietario al UID del contenedor
sudo chown -R 999:999 data/

# Opción B: O dar permisos de escritura amplio (menos seguro)
chmod -R 777 data/
```

---

## Actualización de Código

Cuando haya nuevos cambios en el repositorio:

```bash
cd /var/www/inventario-django
git pull origin main

# Reconstruir contenedores (necesario si cambian dependencias)
docker compose up -d --build

# Si solo cambió código Python, a veces basta con reiniciar
docker compose restart web
```

---

## Solución de Problemas

### Error 400 Bad Request
- Verifica que la IP o dominio esté incluido en `ALLOWED_HOSTS` en el archivo `.env`.
- Reinicia los contenedores: `docker compose restart`

### Error 502 Bad Gateway
- Gunicorn no está listo. Revisa logs: `docker compose logs web`
- Verifica que no haya errores de migración: `docker compose exec web python manage.py migrate`

### Archivos media no se ven
- Verifica que el directorio `data/media/` exista en el host.
- Revisa permisos: `ls -la data/`

### Puertos ocupados
Si el puerto 80 está ocupado, edita `docker-compose.yml` y cambia:
```yaml
ports:
  - "8080:80"  # Usar puerto 8080 en lugar de 80
```

---

## Notas de Seguridad para el Piloto

1. **SQLite**: Para el piloto es perfecto. Si posteriormente necesitas escalar a PostgreSQL, avísame.
2. **Sin HTTPS**: En una red local corporativa esto es aceptable para un piloto. Si necesitas SSL interno, podemos agregar un contenedor de Traefik o configurar certificados autofirmados.
3. **Logs**: Revisa `data/inventario.log` en el host para investigar errores.
4. **Permisos**: El contenedor corre con usuario `django` (no root). Asegúrate de que el directorio `data/` tenga permisos de escritura para el UID del contenedor (por defecto 999).
