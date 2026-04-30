from django.db import migrations

def crear_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    
    # Técnicos
    tecnicos, _ = Group.objects.get_or_create(name='Técnicos')
    perms_tecnicos = Permission.objects.filter(codename__in=[
        'add_dispositivo', 'change_dispositivo', 'view_dispositivo',
        'add_bitacoramantenimiento', 'change_bitacoramantenimiento', 'view_bitacoramantenimiento',
        'add_historialasignacion', 'view_historialasignacion',
        'view_colaborador', 'view_centrocosto', 'view_tipodispositivo',
    ])
    tecnicos.permissions.set(perms_tecnicos)
    
    # Administradores — todos los permisos
    admins, _ = Group.objects.get_or_create(name='Administradores')
    admins.permissions.set(Permission.objects.all())
    
    # Auditores — solo view
    auditores, _ = Group.objects.get_or_create(name='Auditores')
    perms_view = Permission.objects.filter(codename__startswith='view_')
    auditores.permissions.set(perms_view)

class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial')]
    operations = [migrations.RunPython(crear_grupos, migrations.RunPython.noop)]