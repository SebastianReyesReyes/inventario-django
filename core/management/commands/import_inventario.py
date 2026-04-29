import csv
import re
import unicodedata
from datetime import date
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import CentroCosto, EstadoDispositivo, Fabricante, Modelo, TipoDispositivo
from colaboradores.models import Colaborador
from dispositivos.models import (
    Dispositivo, EquipoRed, Impresora, Monitor, Notebook, Smartphone,
)


# ---------------------------------------------------------------------------
# Helpers de normalizacion
# ---------------------------------------------------------------------------
def _normalize(text: str) -> str:
    """Quit tildes, espacios extras, pasa a lower."""
    if not text:
        return ""
    text = str(text).strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text


def _clean_imei(raw) -> str:
    """Limpia IMEI: quita decimales .0, espacios, comillas."""
    if raw is None or str(raw).strip() == "":
        return ""
    val = str(raw).strip().replace('"', "").replace("'", "").replace(",", "")
    try:
        # Si viene como 860534079686116.0
        if "." in val:
            val = str(int(float(val)))
    except ValueError:
        pass
    return val


def _extract_cc_code(ubicacion: str) -> str:
    """Extrae el codigo numerico antes del primer guion."""
    if not ubicacion:
        return ""
    match = re.match(r"(\d+)-", ubicacion.strip())
    return match.group(1) if match else ""


def _sn_is_valid(sn: str) -> bool:
    """Determina si un S/N es valido o es placeholder."""
    if not sn:
        return False
    sn_clean = sn.strip().upper()
    return sn_clean not in ("", "PENDIENTE", "S/N", "SN", "N/A", "NA")


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------
class Command(BaseCommand):
    help = (
        "Importa inventario real desde CSV (estado, fabricante, tipo, modelo, s/n, "
        "propietario, ubicacion, imei1, imei2). Crea modelos y fabricantes faltantes, "
        "genera S/N temporales cuando sea necesario y reporta errores."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Ruta al CSV.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula sin escribir en la BD.",
        )
        parser.add_argument(
            "--default-fabricante",
            type=str,
            default="GENERICO",
            help="Fabricante asignado a modelos nuevos sin marca clara.",
        )
        parser.add_argument(
            "--default-model-name",
            type=str,
            default="POR DEFINIR",
            help="Nombre del modelo creado cuando el CSV viene vacio.",
        )
        parser.add_argument(
            "--create-missing-colaboradores",
            action="store_true",
            help="Crea automaticamente colaboradores no encontrados (sin password, no login).",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.is_absolute():
            csv_path = Path(settings.BASE_DIR) / csv_path
        if not csv_path.exists():
            raise CommandError(f"Archivo no encontrado: {csv_path}")

        self.dry_run = options["dry_run"]
        self.default_fab_name = options["default_fabricante"]
        self.default_model_name = options["default_model_name"]
        self.create_missing_colaboradores = options["create_missing_colaboradores"]

        # Contadores / acumuladores
        self.created = 0
        self.updated = 0
        self.skipped = 0
        self.errors = []
        self.colaboradores_no_encontrados = set()

        # Precargar lookups
        self._precache()

        # Leer filas
        rows = self._read_rows(csv_path)
        self.stdout.write(self.style.NOTICE(f"-> {len(rows)} filas leidas. Procesando..."))

        if self.dry_run:
            self.stdout.write(self.style.WARNING("[DRY-RUN] Modo simulacion (sin escritura)"))

        for i, row in enumerate(rows, start=2):
            try:
                with transaction.atomic():
                    result = self._process_row(row)
                    if result == "created":
                        self.created += 1
                    elif result == "updated":
                        self.updated += 1
                    else:
                        self.skipped += 1
                    # Si es dry-run, revertir esta transaccion individual
                    if self.dry_run:
                        raise CommandError("dry-run")
            except CommandError as ce:
                if "dry-run" in str(ce):
                    pass  # Esperado en modo simulacion
                else:
                    self.errors.append(f"Fila {i}: {ce}")
            except Exception as exc:
                self.errors.append(f"Fila {i}: {exc}")

        if self.dry_run:
            raise CommandError(
                "Dry-run finalizado. Usa sin --dry-run para aplicar.\n"
                f"  Resumen: {self.created} crearia, {self.updated} actualizaria, "
                f"{self.skipped} omitiria, {len(self.errors)} errores."
            )

        # Reporte final
        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] Importacion finalizada: {self.created} creado(s), "
                f"{self.updated} actualizado(s), {self.skipped} omitido(s)."
            )
        )
        if self.colaboradores_no_encontrados:
            self.stdout.write(
                self.style.WARNING(
                    f"  [!]  Colaboradores no encontrados ({len(self.colaboradores_no_encontrados)}):"
                )
            )
            for nombre in sorted(self.colaboradores_no_encontrados)[:15]:
                self.stdout.write(f"    - {nombre}")
            if len(self.colaboradores_no_encontrados) > 15:
                self.stdout.write(f"    ... y {len(self.colaboradores_no_encontrados) - 15} mas.")
            if not self.create_missing_colaboradores:
                self.stdout.write(
                    "    Tip: Usa --create-missing-colaboradores para crear estos "
                    "registros automaticamente."
                )
        if self.errors:
            self.stdout.write(self.style.ERROR(f"  Errores ({len(self.errors)}):"))
            for e in self.errors[:15]:
                self.stdout.write(f"    - {e}")
            if len(self.errors) > 15:
                self.stdout.write(f"    ... y {len(self.errors) - 15} mas.")

    # -----------------------------------------------------------------------
    # Precache
    # -----------------------------------------------------------------------
    def _precache(self):
        self.tipos = {t.nombre.strip().lower(): t for t in TipoDispositivo.objects.all()}
        self.estados = {e.nombre.strip().lower(): e for e in EstadoDispositivo.objects.all()}
        self.ccs = {cc.codigo_contable.strip(): cc for cc in CentroCosto.objects.all()}
        self.cc_default = self.ccs.get("114")  # Oficina Central como default
        self.fabs = {f.nombre.strip().lower(): f for f in Fabricante.objects.all()}
        self.modelos = {}  # se llena bajo demanda
        self.colaboradores = {}  # nombre_normalizado -> Colaborador
        for c in Colaborador.objects.filter(esta_activo=True):
            key = _normalize(c.nombre_completo)
            self.colaboradores[key] = c
        # Contador para S/N temporales
        self._temp_sn_counter = 0
        self._prefetch_temp_sn()
        # IMEIs ya usados para evitar duplicados
        self._imeis_used = set()
        self._imei_conflicts = 0

    def _prefetch_temp_sn(self):
        """Busca el ultimo S/N temporal para seguir la secuencia."""
        existing = Dispositivo.objects.filter(
            numero_serie__startswith="TEMP-"
        ).values_list("numero_serie", flat=True)
        nums = []
        for s in existing:
            try:
                nums.append(int(s.split("-")[1]))
            except (ValueError, IndexError):
                pass
        self._temp_sn_counter = max(nums) if nums else 0

    def _next_temp_sn(self) -> str:
        self._temp_sn_counter += 1
        return f"TEMP-{self._temp_sn_counter:04d}"

    # -----------------------------------------------------------------------
    # Lectura CSV
    # -----------------------------------------------------------------------
    def _read_rows(self, csv_path: Path) -> list:
        rows = []
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                row = {k.strip().lower(): (v or "").strip() for k, v in raw.items()}
                rows.append(row)
        return rows

    def _resolve_tipo(self, tipo_raw: str, fabricante_raw: str, modelo_raw: str):
        """
        Resuelve el tipo de dispositivo con logica de fallback.
        Algunos CSVs vienen con el fabricante en la columna tipo (ej: 'LENOVO').
        """
        tipo_name = tipo_raw.lower().strip()
        fab_name = fabricante_raw.lower().strip()
        mod_name = modelo_raw.lower().strip()

        # 1. Intentar match directo
        if tipo_name in self.tipos:
            return self.tipos[tipo_name]

        # 2. Si el tipo parece ser un fabricante conocido, inferir del modelo
        if tipo_name in self.fabs or tipo_name in ("lenovo", "hp", "dell", "samsung", "apple", "huawei", "oppo"):
            # Inferir tipo del nombre del modelo
            if "tab" in mod_name or "tablet" in mod_name:
                inferred = "smartphone"
            elif "phone" in mod_name or "smartphone" in mod_name or "moto" in mod_name or "iphone" in mod_name:
                inferred = "smartphone"
            elif "notebook" in mod_name or "laptop" in mod_name or "thinkpad" in mod_name or "latitude" in mod_name:
                inferred = "notebook"
            elif "monitor" in mod_name or "pantalla" in mod_name:
                inferred = "monitor"
            elif "impresora" in mod_name or "printer" in mod_name or "designjet" in mod_name:
                inferred = "impresora"
            elif "router" in mod_name or "modem" in mod_name or "starlink" in mod_name or "cpe" in mod_name:
                inferred = "router/modems"
            else:
                inferred = None

            if inferred and inferred in self.tipos:
                return self.tipos[inferred]

        # 3. Substring matching
        for name, tipo_obj in self.tipos.items():
            if tipo_name in name or name in tipo_name:
                return tipo_obj

        return None

    # -----------------------------------------------------------------------
    # Procesamiento de fila
    # -----------------------------------------------------------------------
    def _process_row(self, row: dict) -> str:
        # --- campos raw ---
        estado_raw = row.get("estado", "").strip()
        fabricante_raw = row.get("fabricante", "").strip()
        tipo_raw = row.get("tipo", "").strip()
        modelo_raw = row.get("modelo", "").strip()
        sn_raw = (row.get("s/n", "") or row.get("sn", "")).strip()
        propietario_raw = row.get("propietario", "").strip()
        ubicacion_raw = row.get("ubicacion", "").strip()
        imei1_raw = row.get("imei1", "").strip()
        imei2_raw = row.get("imei2", "").strip()

        # --- validaciones minimas ---
        if not tipo_raw and not fabricante_raw:
            raise ValueError("Tipo y fabricante vacios - fila sin datos identificables.")

        # --- resolver Tipo (con fallback inteligente) ---
        tipo = self._resolve_tipo(tipo_raw, fabricante_raw, modelo_raw)
        if not tipo:
            raise ValueError(f"Tipo no encontrado: '{tipo_raw}' (fabricante='{fabricante_raw}', modelo='{modelo_raw}')")

        # --- resolver Estado ---
        estado = self.estados.get(estado_raw.lower()) if estado_raw else None
        if estado_raw and not estado:
            raise ValueError(f"Estado no encontrado: '{estado_raw}'")

        # --- resolver Centro de Costo ---
        cc_code = _extract_cc_code(ubicacion_raw)
        cc = self.ccs.get(cc_code) if cc_code else self.cc_default
        if not cc:
            cc = self.cc_default

        # --- resolver Colaborador ---
        colaborador = None
        if propietario_raw:
            col_key = _normalize(propietario_raw)
            colaborador = self.colaboradores.get(col_key)
            if not colaborador:
                colaborador = self._buscar_colaborador_aproximado(propietario_raw)
            if not colaborador and self.create_missing_colaboradores and not self.dry_run:
                colaborador = self._crear_colaborador_fantasma(propietario_raw)
            if not colaborador:
                self.colaboradores_no_encontrados.add(propietario_raw)

        # --- resolver / crear Modelo + Fabricante ---
        modelo, fabricante = self._resolve_modelo_fabricante(modelo_raw, fabricante_raw, tipo)

        # --- limpiar S/N ---
        sn = sn_raw if _sn_is_valid(sn_raw) else self._next_temp_sn()

        # --- limpiar IMEIs ---
        imei1 = _clean_imei(imei1_raw)
        imei2 = _clean_imei(imei2_raw)

        # --- verificar si ya existe por S/N ---
        try:
            dispositivo = Dispositivo.objects.get(numero_serie__iexact=sn)
            # Actualizar campos simples si cambiaron
            changed = False
            if estado and dispositivo.estado_id != estado.pk:
                dispositivo.estado = estado
                changed = True
            if colaborador and dispositivo.propietario_actual_id != colaborador.pk:
                dispositivo.propietario_actual = colaborador
                changed = True
            if cc and dispositivo.centro_costo_id != cc.pk:
                dispositivo.centro_costo = cc
                changed = True

            if changed and not self.dry_run:
                dispositivo.save(update_fields=["estado", "propietario_actual", "centro_costo", "ultima_actualizacion"])
            return "updated" if changed else "skipped"

        except Dispositivo.DoesNotExist:
            pass  # crear nuevo

        # --- Crear dispositivo polimorfico ---
        if self.dry_run:
            self.stdout.write(f"  [DRY-RUN] Crearia {tipo.sigla}: {modelo} S/N:{sn}")
            return "created"

        base_fields = {
            "numero_serie": sn,
            "estado": estado,
            "modelo": modelo,
            "propietario_actual": colaborador,
            "centro_costo": cc,
            "valor_contable": 0,
            "notas_condicion": "",
        }

        # Polimorfismo segun tipo
        tipo_lower = tipo.nombre.lower()
        if tipo_lower == "notebook":
            d = Notebook.objects.create(
                **base_fields,
                procesador="Por definir",
                ram_gb=0,
                almacenamiento="Por definir",
                sistema_operativo="Por definir",
            )
        elif tipo_lower == "smartphone":
            # Manejar IMEIs duplicados
            imei1_final = imei1 or "POR DEFINIR"
            if imei1_final in self._imeis_used:
                imei1_final = f"TEMP-IMEI-{self._imei_conflicts:04d}"
                self._imei_conflicts += 1
                self.stdout.write(f"    [!] IMEI duplicado detectado, usando temporal: {imei1_final}")
            self._imeis_used.add(imei1_final)
            d = Smartphone.objects.create(
                **base_fields,
                imei_1=imei1_final,
                imei_2=imei2 or None,
            )
        elif tipo_lower == "monitor":
            d = Monitor.objects.create(**base_fields)
        elif tipo_lower == "impresora":
            d = Impresora.objects.create(
                **base_fields,
                es_multifuncional=False,
                tipo_tinta="Por definir",
            )
        elif tipo_lower in ("router/modems", "router", "modems"):
            d = EquipoRed.objects.create(
                **base_fields,
                subtipo="Router / Modem",
            )
        else:
            # Dispositivo generico (Almacenamiento, Periferico, ESCANER, Otro...)
            d = Dispositivo.objects.create(**base_fields)

        self.stdout.write(f"  + {d.identificador_interno} | {modelo} | S/N:{sn}")
        return "created"

    # -----------------------------------------------------------------------
    # Busqueda aproximada de colaborador
    # -----------------------------------------------------------------------
    def _buscar_colaborador_aproximado(self, nombre_raw: str):
        """
        Multiples estrategias de matching:
        1. Primera + ultima palabra contenidas en el nombre completo de la BD.
        2. Solo apellido (ultima palabra) si es poco comun.
        3. Primera palabra + segunda palabra (para nombres compuestos).
        """
        partes = nombre_raw.split()
        if not partes:
            return None

        n = _normalize(nombre_raw)

        # Estrategia 1: primera + ultima palabra
        if len(partes) >= 2:
            first = _normalize(partes[0])
            last = _normalize(partes[-1])
            for key, col in self.colaboradores.items():
                if first in key and last in key:
                    return col

        # Estrategia 2: primera + segunda palabra (ej: Maria Jose)
        if len(partes) >= 3:
            first = _normalize(partes[0])
            second = _normalize(partes[1])
            for key, col in self.colaboradores.items():
                if first in key and second in key:
                    return col

        # Estrategia 3: substring completo
        for key, col in self.colaboradores.items():
            if n in key or key in n:
                return col

        return None

    def _crear_colaborador_fantasma(self, nombre_raw: str):
        """Crea un colaborador minimo para no perder la asignacion."""
        partes = nombre_raw.split()
        first = partes[0] if partes else nombre_raw
        last = " ".join(partes[1:]) if len(partes) > 1 else ""
        username_base = _normalize(nombre_raw).replace(" ", "_")[:25]
        username = self._generar_username_unico(username_base)

        col = Colaborador(
            username=username,
            first_name=first,
            last_name=last,
            esta_activo=True,
        )
        col.set_unusable_password()
        col.save()
        # Registrar en cache
        self.colaboradores[_normalize(col.nombre_completo)] = col
        self.stdout.write(
            self.style.NOTICE(f"    Colaborador fantasma creado: {nombre_raw} ({username})")
        )
        return col

    @staticmethod
    def _generar_username_unico(base: str) -> str:
        base = base[:30]
        username = base
        counter = 1
        while Colaborador.objects.filter(username=username).exists():
            suffix = f"_{counter}"
            username = f"{base[:30 - len(suffix)]}{suffix}"
            counter += 1
        return username

    # -----------------------------------------------------------------------
    # Resolver modelo + fabricante
    # -----------------------------------------------------------------------
    def _resolve_modelo_fabricante(self, modelo_raw: str, fabricante_raw: str, tipo: TipoDispositivo):
        """Devuelve (Modelo, Fabricante). Crea ambos si no existen."""
        modelo_name = modelo_raw.strip() if modelo_raw.strip() else self.default_model_name
        fab_name = fabricante_raw.strip() if fabricante_raw.strip() else self.default_fab_name

        # Normalizar nombre de fabricante (title case para legibilidad)
        fab_name = fab_name.title()

        # Intentar match exacto de modelo para este tipo + fabricante
        cache_key = (modelo_name.lower(), fab_name.lower(), tipo.pk)
        if cache_key in self.modelos:
            return self.modelos[cache_key]

        existing = Modelo.objects.filter(
            nombre__iexact=modelo_name,
            tipo_dispositivo=tipo,
        ).select_related("fabricante").first()

        if existing:
            self.modelos[cache_key] = (existing, existing.fabricante)
            return existing, existing.fabricante

        # Fabricante
        fab = self.fabs.get(fab_name.lower())
        if not fab:
            fab = Fabricante.objects.create(nombre=fab_name)
            self.fabs[fab_name.lower()] = fab
            self.stdout.write(self.style.NOTICE(f"    Nuevo fabricante: {fab_name}"))

        # Modelo - con manejo de duplicados por race condition
        try:
            new_model = Modelo.objects.create(
                nombre=modelo_name,
                fabricante=fab,
                tipo_dispositivo=tipo,
            )
            self.stdout.write(self.style.NOTICE(
                f"    Nuevo modelo: {modelo_name} ({fab_name} / {tipo.nombre})"
            ))
        except Exception:
            # Race condition: otro hilo/fila creo el modelo mismo
            new_model = Modelo.objects.filter(
                nombre__iexact=modelo_name,
                fabricante=fab,
                tipo_dispositivo=tipo,
            ).first()
            if not new_model:
                raise
            self.stdout.write(self.style.NOTICE(
                f"    Modelo existente (race): {modelo_name} ({fab_name})"
            ))
        self.modelos[cache_key] = (new_model, fab)
        return new_model, fab
