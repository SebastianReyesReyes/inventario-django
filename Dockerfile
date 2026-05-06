# Imagen base oficial de Python
FROM python:3.12-slim-bookworm

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Instalar dependencias del sistema necesarias para compilar paquetes de Python y para SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    pkg-config \
    libcairo2-dev \
    libgirepository1.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para seguridad
RUN groupadd -r django && useradd -r -g django django

# Directorio de trabajo
WORKDIR /app

# Copiar e instalar requirements primero (para cacheo de capas)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Crear directorios necesarios y ajustar permisos
RUN mkdir -p /app/static /app/media /app/data && \
    chown -R django:django /app

# Puerto por defecto de Gunicorn
EXPOSE 8000

# Script de entrada
COPY ops/docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER django

ENTRYPOINT ["/app/entrypoint.sh"]
