from django.db import migrations


def crear_estados_iniciales(apps, schema_editor):
    """Carga los estados base del inventario con colores por defecto (HU-04)."""
    EstadoDispositivo = apps.get_model('core', 'EstadoDispositivo')
    
    estados = [
        {'nombre': 'Disponible',          'color': '#60a5fa'},  # info/azul
        {'nombre': 'Asignado',            'color': '#34d399'},  # success/verde
        {'nombre': 'En Reparación',       'color': '#ED8B00'},  # jmie-orange
        {'nombre': 'Fuera de Inventario', 'color': '#ef4444'},  # error/rojo
    ]
    
    for estado in estados:
        EstadoDispositivo.objects.get_or_create(
            nombre=estado['nombre'],
            defaults={'color': estado['color']}
        )


def revertir_estados(apps, schema_editor):
    """No eliminamos datos en rollback para proteger integridad referencial."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_ajustes_catalogos'),
    ]

    operations = [
        migrations.RunPython(crear_estados_iniciales, revertir_estados),
    ]
