#!/bin/sh
set -e

# Este script se ejecuta cada vez que arranca el contenedor web

echo "========================================"
echo "Iniciando Inventario JMIE (Piloto UAT)"
echo "========================================"

# Crear subdirectorios de datos si no existen
mkdir -p /app/data/media

# Aplicar migraciones de base de datos (SQLite)
echo "[1/3] Aplicando migraciones..."
python manage.py migrate --noinput

# Recolectar archivos estáticos
echo "[2/3] Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

# Crear superusuario si no existe (opcional, descomentar si se necesita)
# echo "[3/3] Verificando superusuario..."
# python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@jmie.cl', 'admin123')"

echo "[3/3] Iniciando servidor Gunicorn..."
echo "========================================"

# Ejecutar Gunicorn
# --bind 0.0.0.0:8000: escucha en todas las interfaces
# --workers 3: 3 workers (ajustar según CPUs del servidor local)
# --access-logfile -: logs de acceso a stdout
# --error-logfile -: logs de error a stdout
# --capture-output: captura stdout/stderr de la app
# --enable-stdio-inheritance: permite que la app herede stdio
# --timeout 60: timeout de 60 segundos
exec gunicorn inventario_jmie.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class sync \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance \
    --timeout 60
