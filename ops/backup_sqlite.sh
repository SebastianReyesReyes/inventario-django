#!/bin/bash
# =============================================================================
# Script de Respaldo Automático para Inventario JMIE
# =============================================================================
# Este script comprime la base de datos SQLite y la carpeta media en un
# archivo .tar.gz con timestamp, manteniendo solo los últimos 10 backups.
#
# CRON sugerido (cada 12 horas):
# 0 */12 * * * /var/www/inventario-django/ops/backup_sqlite.sh >> /var/log/inventario-backup.log 2>&1
# =============================================================================

set -euo pipefail

# Directorio donde se almacenarán los respaldos
BACKUP_DIR="${BACKUP_DIR:-/var/backups/inventario}"

# Archivos y directorios a respaldar (relativos al directorio de ejecución)
DB_FILE="db.sqlite3"
MEDIA_DIR="media"

# Timestamp para el nombre del archivo
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M")
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.tar.gz"

# Crear directorio de backups si no existe
if [ ! -d "$BACKUP_DIR" ]; then
    echo "[INFO] Creando directorio de respaldos: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
fi

# Verificar que existen los recursos a respaldar
if [ ! -f "$DB_FILE" ]; then
    echo "[ERROR] No se encontró la base de datos: $DB_FILE" >&2
    exit 1
fi

if [ ! -d "$MEDIA_DIR" ]; then
    echo "[ADVERTENCIA] No se encontró el directorio media: $MEDIA_DIR. Continuando solo con db.sqlite3..."
    MEDIA_DIR=""
fi

# Crear el respaldo comprimido
echo "[INFO] Generando respaldo: $BACKUP_FILE"
if [ -n "$MEDIA_DIR" ]; then
    tar -czf "$BACKUP_FILE" "$DB_FILE" "$MEDIA_DIR"
else
    tar -czf "$BACKUP_FILE" "$DB_FILE"
fi

if [ $? -eq 0 ]; then
    echo "[OK] Respaldo creado exitosamente: $BACKUP_FILE"
else
    echo "[ERROR] Falló la creación del respaldo." >&2
    exit 1
fi

# Mantener solo los últimos 10 backups (eliminar los más antiguos)
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 10 ]; then
    echo "[INFO] Limpiando respaldos antiguos (manteniendo últimos 10)..."
    ls -1t "$BACKUP_DIR"/backup_*.tar.gz | tail -n +11 | xargs -r rm -f
    echo "[OK] Limpieza completada."
else
    echo "[INFO] Total de respaldos: $BACKUP_COUNT. No es necesario eliminar."
fi

echo "[OK] Proceso de respaldo finalizado."
