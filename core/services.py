import csv
import io
from django.db import transaction
from .models import TipoDispositivo, Fabricante, Modelo


def get_csv_value(row, *keys):
    """Busca el primer valor no vacío entre las claves candidatas."""
    for key in keys:
        val = row.get(key, '').strip()
        if val:
            return val
    return None


def get_or_create_tipo(nombre):
    """Obtiene o crea un TipoDispositivo, asegurando que tenga sigla."""
    tipo, created = TipoDispositivo.objects.get_or_create(nombre=nombre)
    if created or not tipo.sigla:
        base = ''.join(c for c in nombre.upper() if c.isalnum())[:5]
        if not base:
            base = "EQUIP"
        sigla = base
        counter = 1
        while TipoDispositivo.objects.filter(sigla=sigla).exclude(pk=tipo.pk).exists():
            sigla = f"{base[:4]}{counter}"
            counter += 1
        tipo.sigla = sigla
        tipo.save(update_fields=['sigla'])
    return tipo, created


def importar_catalogos_desde_csv(file_obj, dry_run=False):
    """
    Importa fabricantes, tipos y modelos desde un archivo CSV.
    
    Args:
        file_obj: File-like object (UploadedFile o file handle)
        dry_run: Si True, no guarda cambios
        
    Returns:
        dict: {
            'total': int,
            'creados_fab': int,
            'creados_tipo': int,
            'creados_modelo': int,
            'actualizados_modelo': int,
            'errores': int,
            'saltados': int,
            'logs': list[str],
        }
    """
    logs = []
    total = 0
    creados_fab = 0
    creados_tipo = 0
    creados_modelo = 0
    actualizados_modelo = 0
    errores = 0
    saltados = 0

    # Para dry_run usamos savepoint para poder hacer rollback
    if dry_run:
        from django.db import connection
        connection.set_autocommit(False)

    try:
        reader = csv.DictReader(io.TextIOWrapper(file_obj, encoding='utf-8'))

        for row in reader:
            total += 1
            row_num = total + 1

            fabricante_nombre = get_csv_value(
                row, 'fabricante', 'fabricante_nombre', 'marca', 'brand'
            )
            modelo_nombre = get_csv_value(
                row, 'modelo', 'modelo_nombre', 'model', 'nombre'
            )
            tipo_nombre = get_csv_value(
                row, 'tipo', 'tipo_dispositivo', 'tipo_equipo', 'category'
            )

            if not fabricante_nombre or not modelo_nombre:
                logs.append(f"Fila {row_num}: falta fabricante o modelo, saltando.")
                saltados += 1
                continue

            try:
                with transaction.atomic():
                    fabricante, fab_created = Fabricante.objects.get_or_create(
                        nombre=fabricante_nombre
                    )
                    if fab_created:
                        creados_fab += 1
                        logs.append(f"  Fabricante '{fabricante_nombre}' creado.")

                    tipo = None
                    tipo_created = False
                    if tipo_nombre:
                        tipo, tipo_created = get_or_create_tipo(tipo_nombre)
                        if tipo_created:
                            creados_tipo += 1
                            logs.append(f"  Tipo '{tipo_nombre}' creado con sigla: {tipo.sigla}")

                    if dry_run:
                        logs.append(
                            f"[DRY-RUN] Fila {row_num}: fab={fabricante_nombre} | "
                            f"modelo={modelo_nombre} | tipo={tipo_nombre or 'N/A'}"
                        )
                        raise transaction.Rollback  # Fuerza rollback de esta fila

                    modelo_defaults = {}
                    if tipo:
                        modelo_defaults['tipo_dispositivo'] = tipo

                    modelo, mod_created = Modelo.objects.get_or_create(
                        nombre=modelo_nombre,
                        fabricante=fabricante,
                        defaults=modelo_defaults,
                    )

                    if not mod_created and tipo and modelo.tipo_dispositivo_id is None:
                        modelo.tipo_dispositivo = tipo
                        modelo.save(update_fields=['tipo_dispositivo'])
                        actualizados_modelo += 1
                    elif not mod_created and tipo and modelo.tipo_dispositivo != tipo:
                        modelo.tipo_dispositivo = tipo
                        modelo.save(update_fields=['tipo_dispositivo'])
                        actualizados_modelo += 1

                    if mod_created:
                        creados_modelo += 1

            except transaction.Rollback:
                pass  # Dry-run, intencional
            except Exception as e:
                errores += 1
                logs.append(f"Fila {row_num} ({fabricante_nombre} {modelo_nombre}): {e}")

    finally:
        if dry_run:
            from django.db import connection
            connection.rollback()
            connection.set_autocommit(True)

    return {
        'total': total,
        'creados_fab': creados_fab,
        'creados_tipo': creados_tipo,
        'creados_modelo': creados_modelo,
        'actualizados_modelo': actualizados_modelo,
        'errores': errores,
        'saltados': saltados,
        'logs': logs,
    }
