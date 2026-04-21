"""
Script para crear usuarios de prueba con roles diferenciados.

Uso:
    python scripts/create_demo_users.py

Este script crea 3 usuarios demo si no existen:
- tecnico@demo.local  (Admin + Tecnico)
- gerente@demo.local  (Auditor)
- costos@demo.local   (Auditor)

Contraseña por defecto: Demo1234!
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_jmie.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth.models import Group, Permission
from colaboradores.models import Colaborador


def sync_group_permissions():
    """Sincroniza los permisos de los grupos con la configuración actual."""
    # Técnicos
    tecnicos, _ = Group.objects.get_or_create(name='Técnicos')
    perms_tecnicos = [
        'add_dispositivo', 'change_dispositivo', 'view_dispositivo',
        'add_bitacoramantenimiento', 'view_bitacoramantenimiento', 'change_bitacoramantenimiento',
        'add_historialasignacion', 'view_historialasignacion',
        'add_entregaaccesorio', 'view_entregaaccesorio',
        'add_acta', 'view_acta',
        'view_colaborador', 'view_centrocosto', 'view_tipodispositivo',
        'view_fabricante', 'view_modelo', 'view_estadodispositivo',
    ]
    tecnicos.permissions.set(Permission.objects.filter(codename__in=perms_tecnicos))
    
    # Auditores
    auditores, _ = Group.objects.get_or_create(name='Auditores')
    auditores.permissions.set(Permission.objects.filter(codename__startswith='view_'))
    
    # Administradores
    admins, _ = Group.objects.get_or_create(name='Administradores')
    admins.permissions.set(Permission.objects.all())


def create_demo_user(email, first_name, last_name, groups_names, is_staff=True):
    """Crea o actualiza un usuario demo."""
    username = email.split('@')[0]
    
    user, created = Colaborador.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'is_staff': is_staff,
            'is_superuser': False,
            'is_active': True,
            'esta_activo': True,
        }
    )
    
    if not created:
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_staff = is_staff
        user.is_active = True
        user.esta_activo = True
        user.save()
        print(f"  [ACTUALIZADO] {email}")
    else:
        print(f"  [CREADO] {email}")
    
    # Set password
    user.set_password('Demo1234!')
    user.save()
    
    # Assign groups
    user.groups.clear()
    for group_name in groups_names:
        try:
            group = Group.objects.get(name=group_name)
            user.groups.add(group)
            print(f"    -> Grupo: {group_name}")
        except Group.DoesNotExist:
            print(f"    [ADVERTENCIA] Grupo '{group_name}' no existe. Ejecuta migraciones/seed.")
    
    # Recalculate permissions from groups
    user.user_permissions.clear()
    for group in user.groups.all():
        for perm in group.permissions.all():
            user.user_permissions.add(perm)
    user.save()
    
    return user


def main():
    print("=" * 60)
    print("SINCRONIZACION DE PERMISOS Y USUARIOS DEMO")
    print("=" * 60)
    print()
    
    # Sincronizar permisos de grupos primero
    print("Sincronizando permisos de grupos...")
    sync_group_permissions()
    print("  [OK] Grupos actualizados")
    print()
    
    # 1. Admin/Tecnico (todo el poder excepto superuser)
    print("1. Tecnico / Administrador (puede crear, editar, eliminar)")
    create_demo_user(
        email='tecnico@demo.local',
        first_name='Tecnico',
        last_name='Demo',
        groups_names=['Administradores', 'Técnicos'],
        is_staff=True,
    )
    print()
    
    # 2. Gerente (Auditor - solo lectura y reportes)
    print("2. Gerente (Auditor - solo lectura, reportes, actas)")
    create_demo_user(
        email='gerente@demo.local',
        first_name='Gerente',
        last_name='Demo',
        groups_names=['Auditores'],
        is_staff=True,
    )
    print()
    
    # 3. Costos (Auditor - solo lectura, reportes, dashboard)
    print("3. Costos (Auditor - lectura, reportes, exportar Excel)")
    create_demo_user(
        email='costos@demo.local',
        first_name='Costos',
        last_name='Demo',
        groups_names=['Auditores'],
        is_staff=True,
    )
    print()
    
    print("=" * 60)
    print("LISTO!")
    print("=" * 60)
    print()
    print("Credenciales de prueba:")
    print("  Tecnico:  tecnico@demo.local / Demo1234!")
    print("  Gerente:  gerente@demo.local / Demo1234!")
    print("  Costos:   costos@demo.local  / Demo1234!")
    print()
    print("Para probar:")
    print("  1. Corre: python manage.py runserver")
    print("  2. Abre:  http://127.0.0.1:8000/login/")
    print("  3. Inicia sesion con cada usuario y verifica permisos")
    print()
    print("IMPORTANTE: Estos usuarios son solo para pruebas locales.")
    print("No usar en produccion sin cambiar contraseñas.")


if __name__ == '__main__':
    main()
