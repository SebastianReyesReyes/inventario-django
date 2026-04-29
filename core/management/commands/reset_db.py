import os
import shutil
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Elimina la base de datos SQLite, limpia migraciones locales y regenera todo desde cero."

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--force",
            action="store_true",
            help="No pedir confirmación interactiva.",
        )
        parser.add_argument(
            "--superuser",
            action="store_true",
            help="Crea un superusuario al finalizar.",
        )

    def handle(self, *args, **options):
        db_config = settings.DATABASES.get("default", {})
        db_engine = db_config.get("ENGINE", "")
        db_name = db_config.get("NAME", "")

        if "sqlite3" not in db_engine:
            raise CommandError(
                f"Este comando solo es compatible con SQLite. "
                f"Motor detectado: {db_engine}"
            )

        db_path = Path(db_name) if db_name else Path(settings.BASE_DIR) / "db.sqlite3"

        self.stdout.write(self.style.WARNING("⚠️  Esto eliminará TODOS los datos de la base de datos."))
        self.stdout.write(f"   Archivo a eliminar: {db_path.resolve()}")

        if not options["noinput"]:
            confirm = input("¿Estás seguro? Escribe 'sí' para continuar: ")
            if confirm.strip().lower() not in ("sí", "si", "s"):
                self.stdout.write(self.style.ERROR("Operación cancelada."))
                return

        # 1. Eliminar archivo SQLite
        if db_path.exists():
            try:
                db_path.unlink()
                self.stdout.write(self.style.SUCCESS(f"✓ Base de datos eliminada: {db_path}"))
            except OSError as exc:
                raise CommandError(f"No se pudo eliminar la base de datos: {exc}") from exc
        else:
            self.stdout.write(self.style.NOTICE("⚠ No se encontró archivo SQLite (quizás ya fue eliminado)."))

        # 2. Eliminar migraciones locales (000*.py)
        local_apps = [app_config.label for app_config in apps.get_app_configs() if not app_config.path.startswith(str(Path(__file__).resolve().parent.parent.parent.parent / ".venv"))]
        # Otra forma más simple: iterar INSTALLED_APPS y verificar si existe carpeta migrations
        deleted_migrations = 0
        for app_config in apps.get_app_configs():
            migrations_dir = Path(app_config.path) / "migrations"
            if not migrations_dir.exists():
                continue

            # Saltar apps de terceros/Django (heurística: que no estén dentro del proyecto)
            # El proyecto está en el workspace; asumimos que las apps locales están bajo el root.
            try:
                app_relative = migrations_dir.relative_to(settings.BASE_DIR)
            except ValueError:
                # App fuera del BASE_DIR (ej. entorno virtual o paquete instalado)
                continue

            # No tocar migraciones de paquetes internos de Django o third-party
            # Heurística extra: si la ruta contiene site-packages o .venv, saltar
            if ".venv" in str(app_relative) or "site-packages" in str(app_relative):
                continue

            for migration_file in sorted(migrations_dir.glob("[0-9]*.py")):
                if migration_file.name == "__init__.py":
                    continue
                try:
                    migration_file.unlink()
                    deleted_migrations += 1
                except OSError:
                    self.stdout.write(self.style.ERROR(f"  ✗ No se pudo eliminar {migration_file}"))

        self.stdout.write(self.style.SUCCESS(f"✓ Migraciones locales eliminadas: {deleted_migrations} archivo(s)"))

        # 3. makemigrations
        self.stdout.write(self.style.NOTICE("→ Generando nuevas migraciones..."))
        call_command("makemigrations", verbosity=1)

        # 4. migrate
        self.stdout.write(self.style.NOTICE("→ Aplicando migraciones..."))
        call_command("migrate", verbosity=1)

        self.stdout.write(self.style.SUCCESS("✓ Base de datos regenerada exitosamente."))

        # 5. Superusuario opcional
        if options["superuser"]:
            self.stdout.write(self.style.NOTICE("→ Creando superusuario..."))
            call_command("createsuperuser")

        self.stdout.write(self.style.SUCCESS("🚀 Listo. Puedes iniciar el servidor con: python manage.py runserver"))
