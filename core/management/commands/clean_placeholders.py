"""
Limpia registros placeholder generados por factories de prueba
(Tipo N, Estado N, Fabricante N, Modelo N, Centro Costo N, etc.)
que contaminaron la base de datos de desarrollo.

Uso:
    python manage.py clean_placeholders                  # solo placeholders sin dependencias
    python manage.py clean_placeholders --force           # elimina TODO (dispositivos + placeholders)
    python manage.py clean_placeholders --dry-run         # solo lista
    python manage.py clean_placeholders --force --dry-run # muestra que haria --force
"""
import re
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    TipoDispositivo, EstadoDispositivo, Fabricante,
    Modelo, CentroCosto, Departamento,
)
from dispositivos.models import Dispositivo, HistorialAsignacion, BitacoraMantenimiento
from actas.models import Acta


# Patrones de nombre que identifican placeholders de factories
# Orden de eliminacion: de hojas a raices (sin dependientes primero)
# Modelo depende de TipoDispositivo y Fabricante -> va primero
FACTORY_PATTERNS = {
    Modelo: re.compile(r"^Modelo\s+\d+$"),
    TipoDispositivo: re.compile(r"^Tipo\s+\d+$"),
    Fabricante: re.compile(r"^Fabricante\s+\d+$"),
    EstadoDispositivo: re.compile(r"^Estado\s+\d+$"),
    CentroCosto: re.compile(r"^(Centro\s+Costo\s+\d+|CC-\d{4})$"),
    Departamento: re.compile(r"^Departamento\s+\d+$"),
}

# Patron de dispositivos de prueba generados por DispositivoFactory
DEVICE_FACTORY_PATTERN = re.compile(r"^SN-\d{8}$")

# Patron de colaboradores de prueba generados por ColaboradorFactory
USER_FACTORY_PATTERN = re.compile(r"^user_\d+$")


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo mostrar que se eliminaria, sin aplicar cambios.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Eliminar tambien los dispositivos de prueba que bloquean los placeholders.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        if dry_run:
            self.stdout.write(self.style.NOTICE(">>> MODO DRY-RUN -- no se eliminara nada\n"))

        # --- Fase 1: Si --force, eliminar datos de prueba ---
        if force:
            self._clean_test_devices(dry_run)
            self._clean_test_users(dry_run)

        # --- Fase 2: Eliminar placeholders de catalogo ---
        total_deleted = 0
        total_blocked = 0

        for model_cls, pattern in FACTORY_PATTERNS.items():
            candidates = model_cls.objects.filter(nombre__regex=pattern.pattern)
            if not candidates.exists():
                continue

            self.stdout.write(f"\n--- {model_cls.__name__} ({candidates.count()} candidatos) ---")

            for obj in candidates.order_by("nombre"):
                blocked_by = self._get_blockers(model_cls, obj)

                if blocked_by:
                    total_blocked += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [BLOQUEADO] {obj.nombre} -- {', '.join(blocked_by)}"
                        )
                    )
                else:
                    if not dry_run:
                        obj.delete()
                    total_deleted += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  [OK] {obj.nombre} -- eliminado")
                    )

        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f"DRY-RUN: {total_deleted} se eliminarian, {total_blocked} bloqueados"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Eliminados: {total_deleted}  |  Bloqueados: {total_blocked}"
                )
            )

        if total_blocked > 0:
            self.stdout.write(
                self.style.NOTICE(
                    "\nLos registros bloqueados tienen dispositivos o modelos que los "
                    "referencian. Usa --force para eliminar primero los dispositivos de "
                    "prueba y luego reintentar."
                )
            )

    def _clean_test_devices(self, dry_run):
        """Elimina dispositivos de prueba y sus registros asociados."""
        test_devices = Dispositivo.objects.filter(
            numero_serie__regex=DEVICE_FACTORY_PATTERN.pattern
        )

        if not test_devices.exists():
            self.stdout.write("No se encontraron dispositivos de prueba (SN-NNNNNNNN).")
            return

        self.stdout.write(
            self.style.NOTICE(
                f"\n>>> Dispositivos de prueba encontrados: {test_devices.count()}"
            )
        )

        # Eliminar dependencias primero (actas, historial, mantenimientos)
        if not dry_run:
            with transaction.atomic():
                dispositivo_ids = list(test_devices.values_list("pk", flat=True))

                # Borramos dependencias en orden (de hoja a raiz)
                # 1. Historial de asignaciones (FK a dispositivo, acta ON DELETE SET NULL)
                deleted_hist, _ = HistorialAsignacion.objects.filter(
                    dispositivo_id__in=dispositivo_ids
                ).delete()

                # 2. Actas huerfanas (sin asignaciones asociadas)
                Acta.objects.filter(asignaciones__isnull=True).delete()

                # 3. Mantenimientos
                deleted_mant, _ = BitacoraMantenimiento.objects.filter(
                    dispositivo_id__in=dispositivo_ids
                ).delete()

                # 4. Dispositivos
                deleted_dev, _ = test_devices.delete()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Dispositivos: {deleted_dev}  |  "
                        f"Asignaciones: {deleted_hist}  |  "
                        f"Mantenimientos: {deleted_mant}"
                    )
                )
        else:
            # En dry-run, solo contar
                self.stdout.write(
                    self.style.NOTICE(
                        f"  (dry-run) Se eliminarian {test_devices.count()} dispositivos"
                        f" y sus dependencias asociadas."
                    )
                )

    def _clean_test_users(self, dry_run):
        """Elimina colaboradores de prueba generados por ColaboradorFactory."""
        from colaboradores.models import Colaborador

        test_users = Colaborador.objects.filter(
            username__regex=USER_FACTORY_PATTERN.pattern
        ).exclude(username="admin")

        if not test_users.exists():
            return

        self.stdout.write(
            self.style.NOTICE(
                f"\n>>> Colaboradores de prueba encontrados: {test_users.count()}"
            )
        )

        if not dry_run:
            with transaction.atomic():
                user_ids = list(test_users.values_list("pk", flat=True))

                HistorialAsignacion.objects.filter(
                    colaborador_id__in=user_ids
                ).delete()
                Acta.objects.filter(
                    colaborador_id__in=user_ids
                ).delete()

                deleted = test_users.delete()[0]
                self.stdout.write(
                    self.style.SUCCESS(f"  Colaboradores de prueba eliminados: {deleted}")
                )
        else:
            self.stdout.write(
                self.style.NOTICE(
                    f"  (dry-run) Se eliminarian {test_users.count()} colaboradores"
                )
            )

    def _get_blockers(self, model_cls, obj):
        """Devuelve lista de descripciones de que impide eliminar este objeto."""
        blockers = []

        if model_cls == TipoDispositivo:
            if Dispositivo.objects.filter(modelo__tipo_dispositivo=obj).exists():
                blockers.append("dispositivos con este tipo")
            if Modelo.objects.filter(tipo_dispositivo=obj).exists():
                blockers.append("modelos que lo referencian")

        elif model_cls == EstadoDispositivo:
            if Dispositivo.objects.filter(estado=obj).exists():
                blockers.append("dispositivos con este estado")

        elif model_cls == Fabricante:
            if Modelo.objects.filter(fabricante=obj).exists():
                modelos_count = Modelo.objects.filter(fabricante=obj).count()
                blockers.append(f"{modelos_count} modelo(s)")
            if Dispositivo.objects.filter(modelo__fabricante=obj).exists():
                dispositivos_count = Dispositivo.objects.filter(modelo__fabricante=obj).count()
                blockers.append(f"{dispositivos_count} dispositivo(s) con modelos de este fabricante")

        elif model_cls == Modelo:
            if Dispositivo.objects.filter(modelo=obj).exists():
                dispositivos_count = Dispositivo.objects.filter(modelo=obj).count()
                blockers.append(f"{dispositivos_count} dispositivo(s) de este modelo")

        elif model_cls == CentroCosto:
            if Dispositivo.objects.filter(centro_costo=obj).exists():
                dispositivos_count = Dispositivo.objects.filter(centro_costo=obj).count()
                blockers.append(f"{dispositivos_count} dispositivo(s) en este CC")

        elif model_cls == Departamento:
            from colaboradores.models import Colaborador
            if Colaborador.objects.filter(departamento=obj).exists():
                colaboradores_count = Colaborador.objects.filter(departamento=obj).count()
                blockers.append(f"{colaboradores_count} colaborador(es) en este depto")

        return blockers
