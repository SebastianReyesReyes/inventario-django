from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = 'Crea o actualiza los grupos base de permisos (Tecnicos, Auditores, Administradores)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo',
            action='store_true',
            help='Crea usuarios demo asignados a los grupos',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Sincronizando grupos y permisos...'))

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
            'view_departamento',
            # Permisos para catálogos base (crear/editar)
            'add_centrocosto', 'change_centrocosto',
            'add_tipodispositivo', 'change_tipodispositivo',
            'add_fabricante', 'change_fabricante',
            'add_modelo', 'change_modelo',
            'add_estadodispositivo', 'change_estadodispositivo',
            'add_departamento', 'change_departamento',
        ]
        tecnicos.permissions.set(Permission.objects.filter(codename__in=perms_tecnicos))
        self.stdout.write(f"  {self.style.SUCCESS('[OK]')} Grupo 'Técnicos' - {tecnicos.permissions.count()} permisos")

        # Auditores
        auditores, _ = Group.objects.get_or_create(name='Auditores')
        auditores.permissions.set(Permission.objects.filter(codename__startswith='view_'))
        self.stdout.write(f"  {self.style.SUCCESS('[OK]')} Grupo 'Auditores' - {auditores.permissions.count()} permisos")

        # Administradores
        admins, _ = Group.objects.get_or_create(name='Administradores')
        admins.permissions.set(Permission.objects.all())
        self.stdout.write(f"  {self.style.SUCCESS('[OK]')} Grupo 'Administradores' - {admins.permissions.count()} permisos")

        self.stdout.write(self.style.SUCCESS('\nGrupos sincronizados correctamente.'))

        if options['demo']:
            self._create_demo_users()

    def _create_demo_users(self):
        from colaboradores.models import Colaborador

        self.stdout.write(self.style.MIGRATE_HEADING('\nCreando usuarios demo...'))

        demo_users = [
            {
                'username': 'tecnico',
                'email': 'tecnico@demo.local',
                'first_name': 'Técnico',
                'last_name': 'Demo',
                'groups': ['Administradores', 'Técnicos'],
            },
            {
                'username': 'gerente',
                'email': 'gerente@demo.local',
                'first_name': 'Gerente',
                'last_name': 'Demo',
                'groups': ['Auditores'],
            },
            {
                'username': 'costos',
                'email': 'costos@demo.local',
                'first_name': 'Costos',
                'last_name': 'Demo',
                'groups': ['Auditores'],
            },
        ]

        for data in demo_users:
            user, created = Colaborador.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'is_staff': True,
                    'is_superuser': False,
                    'is_active': True,
                    'esta_activo': True,
                }
            )
            user.set_password('Demo1234!')
            user.save()

            user.groups.clear()
            for group_name in data['groups']:
                group = Group.objects.get(name=group_name)
                user.groups.add(group)

            user.user_permissions.clear()
            for group in user.groups.all():
                for perm in group.permissions.all():
                    user.user_permissions.add(perm)
            user.save()

            action = 'Creado' if created else 'Actualizado'
            self.stdout.write(f"  {self.style.SUCCESS(f'[{action}]')} {data['email']} -> {', '.join(data['groups'])}")

        self.stdout.write(self.style.WARNING('\nCredenciales demo: usuario@demo.local / Demo1234!'))
        self.stdout.write(self.style.WARNING('IMPORTANTE: Solo para pruebas locales.'))
