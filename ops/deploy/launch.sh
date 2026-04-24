#!/bin/bash
# ============================================================================
# Script de Despliegue One-Liner para Inventario JMIE (Docker)
# ============================================================================

set -e

PROJECT_NAME="inventario-jmie"
REPO_URL=""  # TODO: Rellenar con tu URL de Git (ej: https://github.com/tuusuario/inventario-django.git)
DEPLOY_DIR="/var/www/$PROJECT_NAME"

echo "========================================"
echo "Despliegue de Inventario JMIE"
echo "========================================"

# Validar que Docker esté instalado
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker no está instalado."
    echo "Ejecuta primero: bash ops/deploy/install-docker.sh"
    exit 1
fi

# Validar URL del repositorio
if [ -z "$REPO_URL" ]; then
    echo "ERROR: Debes configurar la variable REPO_URL en este script."
    echo "Editalo y cambia: REPO_URL=\"https://github.com/tuusuario/inventario-django.git\""
    exit 1
fi

# 1. Crear directorio de despliegue
echo ""
echo "[1/7] Preparando directorio de despliegue: $DEPLOY_DIR"
sudo mkdir -p /var/www
if [ ! -d "$DEPLOY_DIR/.git" ]; then
    sudo git clone "$REPO_URL" "$DEPLOY_DIR"
else
    echo "      Directorio existe, actualizando código..."
    cd "$DEPLOY_DIR"
    sudo git pull origin main
fi

cd "$DEPLOY_DIR"

# 2. Configurar archivo .env
echo ""
echo "[2/7] Configurando archivo de entorno (.env)"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        sudo cp .env.example .env
        echo "      ✓ Creado .env desde .env.example"
    else
        echo "      ADVERTENCIA: No existe .env.example. Debes crear .env manualmente."
    fi
else
    echo "      ✓ .env ya existe (conservando configuración actual)"
fi

# 3. Crear directorio de datos persistentes
echo ""
echo "[3/7] Creando directorios de datos persistentes"
sudo mkdir -p data/media
sudo mkdir -p /var/backups/inventario

# 4. Ajustar permisos (el contenedor usa UID 999)
echo ""
echo "[4/7] Ajustando permisos para el contenedor"
sudo chown -R 999:999 data/
sudo chmod -R 755 data/

# 5. Construir e iniciar contenedores
echo ""
echo "[5/7] Construyendo e iniciando contenedores Docker..."
sudo docker compose down 2>/dev/null || true
sudo docker compose up -d --build

# 6. Esperar a que el servicio web esté saludable
echo ""
echo "[6/7] Esperando a que la aplicación esté lista..."
sleep 5

MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if sudo docker compose ps | grep -q "healthy"; then
        echo "      ✓ Contenedor web está saludable"
        break
    fi
    echo "      ... esperando ($(($RETRY_COUNT + 1))/$MAX_RETRIES)"
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "      ADVERTENCIA: El healthcheck no reportó 'healthy', pero el contenedor puede estar funcionando."
    echo "      Revisa los logs: sudo docker compose logs -f web"
fi

# 7. Información final
echo ""
echo "========================================"
echo "¡Despliegue completado!"
echo "========================================"
echo ""
echo "Accede a la aplicación:"
echo "  → http://$(hostname -I | awk '{print $1}')"
echo ""
echo "Comandos útiles:"
echo "  Ver logs:        sudo docker compose logs -f web"
echo "  Ver estado:      sudo docker compose ps"
echo "  Reiniciar:       sudo docker compose restart"
echo "  Detener todo:    sudo docker compose down"
echo "  Crear superuser: sudo docker compose exec web python manage.py createsuperuser"
echo ""
echo "Archivos importantes:"
echo "  Base de datos:   $DEPLOY_DIR/data/db.sqlite3"
echo "  Media/uploads:   $DEPLOY_DIR/data/media/"
echo "  Logs:            $DEPLOY_DIR/data/inventario.log"
echo "  Backups:         /var/backups/inventario/"
echo ""
echo "========================================"
