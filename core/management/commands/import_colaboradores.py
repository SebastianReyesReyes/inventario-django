import csv
import secrets
import string
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from colaboradores.models import Colaborador
from core.models import Departamento


class Command(BaseCommand):
    help = "Importa colaboradores desde un CSV (nombre, correo, cargo, departamento)."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Ruta al archivo CSV (relativa a la raíz del proyecto o absoluta).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la importación sin escribir en la base de datos.",
        )
        parser.add_argument(
            "--password",
            type=str,
            default=None,
            help="Contraseña fija para todos los colaboradores importados.",
        )
        parser.add_argument(
            "--no-password",
            action="store_true",
            help="Importar sin contraseña utilizable (no podrán iniciar sesión hasta que un admin les asigne una).",
        )
        parser.add_argument(
            "--skip-header",
            action="store_true",
            default=True,
            help="El CSV tiene encabezado (por defecto True).",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        # Si la ruta es relativa, resolverla desde BASE_DIR del proyecto
        if not csv_path.is_absolute():
            csv_path = Path(settings.BASE_DIR) / csv_path
        if not csv_path.exists():
            raise CommandError(f"Archivo no encontrado: {csv_path}")

        self.stdout.write(self.style.NOTICE(f"→ Leyendo {csv_path}..."))

        # Cache de departamentos para lookup case-insensitive
        self.departamentos = {
            d.nombre.strip().lower(): d
            for d in Departamento.objects.all()
        }

        rows = self._read_csv(csv_path)
        self.stdout.write(f"  Filas leídas: {len(rows)}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("⚠️  MODO SIMULACIÓN (dry-run) — no se guardarán cambios."))

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        with transaction.atomic():
            for i, row in enumerate(rows, start=2):
                try:
                    result = self._procesar_fila(row, options)
                    if result == "created":
                        created_count += 1
                    elif result == "updated":
                        updated_count += 1
                    else:
                        skipped_count += 1
                except Exception as exc:
                    errors.append(f"Fila {i}: {exc}")
                    if not options["dry_run"]:
                        raise  # En modo real, falla rápido

            if options["dry_run"]:
                self.stdout.write(self.style.WARNING("  Transacción revertida (dry-run)."))
                raise CommandError("Dry-run finalizado. Usa sin --dry-run para aplicar.")

        self.stdout.write(self.style.SUCCESS(
            f"✓ Importación completada: {created_count} creado(s), "
            f"{updated_count} actualizado(s), {skipped_count} omitido(s)."
        ))
        if errors:
            self.stdout.write(self.style.ERROR(f"  Errores: {len(errors)}"))
            for e in errors[:10]:
                self.stdout.write(f"    - {e}")

    def _read_csv(self, csv_path: Path) -> list:
        rows = []
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                # Normalizar nombres de columnas (quitar espacios, lowercase)
                row = {k.strip().lower(): (v or "").strip() for k, v in raw.items()}
                rows.append(row)
        return rows

    def _procesar_fila(self, row: dict, options: dict) -> str:
        nombre_completo = row.get("nombre", "").strip()
        correo = row.get("correo", "").strip()
        cargo = row.get("cargo", "").strip() or None
        departamento_raw = row.get("departamento", "").strip()

        if not nombre_completo or not correo:
            return "skipped"  # Fila vacía o incompleta

        # Separar nombre y apellido (heurística simple)
        partes = nombre_completo.split()
        first_name = partes[0] if partes else nombre_completo
        last_name = " ".join(partes[1:]) if len(partes) > 1 else ""

        # Username: parte antes del @ del correo
        username_base = correo.split("@")[0]
        username = self._generar_username_unico(username_base)

        # Buscar departamento (case-insensitive, tolera tildes si coinciden)
        departamento = None
        if departamento_raw:
            departamento = self.departamentos.get(departamento_raw.lower())
            if not departamento and options["dry_run"]:
                self.stdout.write(
                    self.style.WARNING(
                        f"    Departamento no encontrado: '{departamento_raw}' para {nombre_completo}"
                    )
                )

        # Verificar si ya existe por email
        try:
            colaborador = Colaborador.objects.get(email__iexact=correo)
            # Actualizar si cambió algo
            changed = False
            if colaborador.first_name != first_name:
                colaborador.first_name = first_name
                changed = True
            if colaborador.last_name != last_name:
                colaborador.last_name = last_name
                changed = True
            if cargo and colaborador.cargo != cargo:
                colaborador.cargo = cargo
                changed = True
            if departamento and colaborador.departamento_id != departamento.pk:
                colaborador.departamento = departamento
                changed = True

            if changed and not options["dry_run"]:
                colaborador.save()
            return "updated" if changed else "skipped"

        except Colaborador.DoesNotExist:
            # Crear nuevo
            colaborador = Colaborador(
                username=username,
                email=correo,
                first_name=first_name,
                last_name=last_name,
                cargo=cargo,
                departamento=departamento,
                is_staff=False,
                is_superuser=False,
                esta_activo=True,
            )
            if not options["dry_run"]:
                if options["password"]:
                    colaborador.set_password(options["password"])
                    pwd_msg = f" — pass: {options['password']}"
                else:
                    # Por defecto: sin contraseña utilizable (no pueden loguearse)
                    colaborador.set_unusable_password()
                    pwd_msg = " — sin acceso (password no utilizable)"
                colaborador.save()
                self.stdout.write(
                    f"  + {nombre_completo} ({username}){pwd_msg}"
                )
            else:
                auth_status = "con password" if options["password"] else "sin password (no login)"
                self.stdout.write(
                    f"  [DRY-RUN] Crearía: {nombre_completo} ({username}) [{auth_status}]"
                )
            return "created"

    def _generar_username_unico(self, base: str) -> str:
        """Genera un username único a partir de la base del correo."""
        base = slugify(base).replace("-", "_")[:30]
        username = base
        counter = 1
        while Colaborador.objects.filter(username=username).exists():
            suffix = f"_{counter}"
            username = f"{base[:30 - len(suffix)]}{suffix}"
            counter += 1
        return username

    @staticmethod
    def _generar_password(length: int = 10) -> str:
        """Genera una contraseña temporal legible."""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))
