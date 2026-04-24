#!/bin/bash
# ============================================================================
# Script de Instalación Automática de Docker + Docker Compose
# Para servidores Ubuntu/Debian (primera vez)
# ============================================================================

set -e

echo "========================================"
echo "Instalador Docker para Inventario JMIE"
echo "========================================"

# Detectar distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    echo "No se pudo detectar el sistema operativo. Este script es para Ubuntu/Debian."
    exit 1
fi

echo ""
echo "Sistema detectado: $OS"
echo ""

# Actualizar paquetes
echo "[1/6] Actualizando lista de paquetes..."
sudo apt-get update -qq

# Instalar dependencias necesarias
echo "[2/6] Instalando dependencias..."
sudo apt-get install -y -qq \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    git

# Agregar repositorio oficial de Docker
echo "[3/6] Agregando repositorio oficial de Docker..."
curl -fsSL https://download.docker.com/linux/$ID/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/$ID $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker Engine
echo "[4/6] Instalando Docker Engine..."
sudo apt-get update -qq
sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Agregar usuario actual al grupo docker (evita usar sudo)
echo "[5/6] Configurando permisos..."
sudo usermod -aG docker $USER

# Verificar instalación
echo "[6/6] Verificando instalación..."
sudo docker --version
sudo docker compose version

echo ""
echo "========================================"
echo "¡Docker instalado correctamente!"
echo "========================================"
echo ""
echo "IMPORTANTE: Cierra la sesión SSH y vuelve a conectarte para que los"
echo "            permisos de grupo se apliquen (o ejecuta: newgrp docker)"
echo ""
echo "Próximo paso: Ejecuta ./ops/deploy/launch.sh para desplegar la aplicación."
