from django.db import migrations

def crear_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    
    # 1. Técnicos: Mantenimiento, registro y trazabilidad completa
    tecnicos, _ = Group.objects.get_or_create(name='Técnicos')
    perms_tecnicos_codenames = [
        # Dispositivos
        'add_dispositivo', 'change_dispositivo', 'view_dispositivo',
        'add_bitacoramantenimiento', 'view_bitacoramantenimiento',
        'change_bitacoramantenimiento',
        # Trazabilidad (asignar, reasignar, devolver, accesorios)
        'add_historialasignacion', 'view_historialasignacion',
        'add_entregaaccesorio', 'view_entregaaccesorio',
        # Actas (generar desde dispositivos)
        'add_acta', 'view_acta',
        # Lectura necesaria para formularios
        'view_colaborador', 
        'view_centrocosto', 
        'view_tipodispositivo',
        'view_fabricante',
        'view_modelo',
        'view_estadodispositivo',
    ]
    perms_tecnicos = Permission.objects.filter(codename__in=perms_tecnicos_codenames)
    tecnicos.permissions.set(perms_tecnicos)
    
    # 2. Auditores: "Solo Lectura" en todo el sistema
    auditores, _ = Group.objects.get_or_create(name='Auditores')
    perms_view = Permission.objects.filter(codename__startswith='view_')
    auditores.permissions.set(perms_view)
    
    # 3. Administradores: Control total
    admins, _ = Group.objects.get_or_create(name='Administradores')
    # Les asignamos todos los permisos disponibles
    admins.permissions.set(Permission.objects.all())

def eliminar_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=['Técnicos', 'Auditores', 'Administradores']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_seed_estados'),
        ('auth', '__latest__'),
        ('contenttypes', '__latest__'),
    ]

    operations = [
        migrations.RunPython(crear_grupos, eliminar_grupos),
    ]
