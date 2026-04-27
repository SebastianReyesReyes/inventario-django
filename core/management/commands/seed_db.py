from django.core.management.base import BaseCommand
from django.db import transaction
from constance import config

from core.models import CentroCosto, EstadoDispositivo, TipoDispositivo, Fabricante, Modelo, Departamento
from colaboradores.models import Colaborador


class Command(BaseCommand):
    help = (
        "Puebla los catálogos base del sistema: departamentos, tipos de dispositivo, "
        "estados, centros de costo, fabricantes, modelos, usuario admin de prueba y "
        "configuración inicial de Constance."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-admin",
            action="store_true",
            help="No crear/actualizar el usuario admin de prueba.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("→ Sembrando catálogos base..."))

        with transaction.atomic():
            created_deps = self._seed_departamentos()
            created_tipos = self._seed_tipos()
            created_estados = self._seed_estados()
            created_cc = self._seed_centros_costo()
            created_fab, created_mod = self._seed_fabricantes_y_modelos()
            self._seed_constance()

            if not options["skip_admin"]:
                self._seed_admin_user()

        total = created_deps + created_tipos + created_estados + created_cc + created_fab + created_mod
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Catálogos sembrados: {total} registro(s) nuevo(s).\n"
                f"  Departamentos: {created_deps}\n"
                f"  Tipos: {created_tipos}\n"
                f"  Estados: {created_estados}\n"
                f"  CC: {created_cc}\n"
                f"  Fabricantes: {created_fab}\n"
                f"  Modelos: {created_mod}"
            )
        )

    # ───────────────────────────────────────────────
    # 1. Departamentos
    # ───────────────────────────────────────────────
    def _seed_departamentos(self) -> int:
        nombres = [
            "Adquisiciones",
            "Recursos Humanos",
            "Oficina",
            "Gerencia",
            "Administración",
            "TI",
            "Prevención de riesgos",
            "Control de Gestión",
        ]
        created = 0
        for nombre in nombres:
            _, was_created = Departamento.objects.get_or_create(nombre=nombre)
            if was_created:
                created += 1
        self.stdout.write(f"  Departamentos: {created} nuevo(s)")
        return created

    # ───────────────────────────────────────────────
    # 2. Tipos de dispositivo
    # ───────────────────────────────────────────────
    def _seed_tipos(self) -> int:
        tipos = [
            ("Notebook", "NOTE"),
            ("Monitor", "MONI"),
            ("Smartphone", "SMAR"),
            ("Tablet", "TABL"),
            ("Impresora", "IMPR"),
            ("Almacenamiento", "ALMA"),
            ("Periferico", "PERI"),
            ("Router/modems", "ROUT"),
            ("ESCANER", "ESCA"),
            ("Otro", "OTRO"),
        ]
        created = 0
        for nombre, sigla in tipos:
            _, was_created = TipoDispositivo.objects.update_or_create(
                nombre=nombre,
                defaults={"sigla": sigla, "descripcion": ""},
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Tipos de dispositivo: {created} nuevo(s)")
        return created

    # ───────────────────────────────────────────────
    # 3. Estados
    # ───────────────────────────────────────────────
    def _seed_estados(self) -> int:
        estados = [
            ("Disponible", "#10B981"),
            ("En reparación", "#F59E0B"),
            ("En uso", "#3B82F6"),
            ("Inactivo", "#6B7280"),
            ("Dado de baja", "#EF4444"),
        ]
        created = 0
        for nombre, color in estados:
            _, was_created = EstadoDispositivo.objects.update_or_create(
                nombre=nombre,
                defaults={"color": color},
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Estados de dispositivo: {created} nuevo(s)")
        return created

    # ───────────────────────────────────────────────
    # 4. Centros de costo
    # ───────────────────────────────────────────────
    def _seed_centros_costo(self) -> int:
        centros = [
            ("114", "Oficina Central"),
            ("218", "Hospital Chillán"),
            ("2308", "Edificio Eco Florida"),
            ("2309", "Hospital Parral"),
            ("2401", "Edificio Los Militares"),
            ("2403", "Hospital Provincia Cordillera"),
            ("2501", "Hospital Sótero del Río"),
            ("2502", "Data Center Colina"),
            ("2503", "Centro de Distribución Lo Aguirre (Walmart)"),
            ("2504", "Hospital Río Bueno"),
            ("2506", "Data Center HB"),
            ("2507", "Scala Data Santa Teresa"),
            ("2601", "Modular"),
            ("2602", "Strip Center"),
        ]
        created = 0
        for codigo, nombre in centros:
            _, was_created = CentroCosto.objects.update_or_create(
                codigo_contable=codigo,
                defaults={"nombre": nombre, "activa": True},
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Centros de costo: {created} nuevo(s)")
        return created

    # ───────────────────────────────────────────────
    # 5. Fabricantes y Modelos (desde CSV de activos)
    # ───────────────────────────────────────────────
    def _seed_fabricantes_y_modelos(self) -> tuple:
        # Normaliza tipo del CSV → nombre del TipoDispositivo existente
        tipo_map = {
            "notebook": "Notebook",
            "monitor": "Monitor",
            "smartphone": "Smartphone",
            "impresora": "Impresora",
            "almacenamiento": "Almacenamiento",
            "periferico": "Periferico",
            "router": "Router/modems",
            "otro": "Otro",
            "escaner": "ESCANER",
        }

        # Datos extraídos del CSV resumen_activos.csv
        # Cada tupla: (fabricante_raw, modelo_raw, tipo_raw)
        raw_rows = [
            ("Dell", "Latitude 5490", "Notebook"),
            ("LG", "24mr400-bb", "Monitor"),
            ("Vivo", "Y03", "Smartphone"),
            ("Acer", "", "Notebook"),
            ("POCO", "C85", "Smartphone"),
            ("Canon", "GX7010", "Impresora"),
            ("Epson", "L3250", "Impresora"),
            ("Hp", "", "Notebook"),
            ("Lenovo", "T490", "Notebook"),
            ("Dell", "Latitude 5410", "Notebook"),
            ("Lenovo", "idea pad 5 14ahp9", "Notebook"),
            ("Lenovo", "ThinkBook 14G8 IRL", "Notebook"),
            ("Asus", "x1605s", "Notebook"),
            ("Acer", "X515J", "Notebook"),
            ("Asus", "x515j", "Notebook"),
            ("Asus", "vy249", "Monitor"),
            ("Kolke", "kolke 24 pulgadas", "Monitor"),
            ("Samsung", "C24F390FHL", "Monitor"),
            ("Hikvision", "ds-d5027f2-1p2", "Monitor"),
            ("AOC", "E2270SWHN", "Monitor"),
            ("Western digital", "wdbuzg0010bbk-eb", "Almacenamiento"),
            ("Seagate", "", "Almacenamiento"),
            ("Hiksemi", "", "Almacenamiento"),
            ("Samsung", "SM-A175F/DS", "Smartphone"),
            ("Hikvision", "DS-D5024F2-1V2", "Monitor"),
            ("Brother", "MFC-T930DW", "Impresora"),
            ("Acer", "N19C3", "Notebook"),
            ("Epson", "C641D", "Impresora"),
            ("Logitech", "COMFORT MK345", "Periferico"),
            ("Kensington", "M01468-M", "Periferico"),
            ("Kensington", "M01369-K", "Periferico"),
            ("Hp", "HSA-A005K", "Periferico"),
            ("Hp", "9VJ40AA", "Monitor"),
            ("Logitech", "M170", "Periferico"),
            ("Apple", "A2338", "Notebook"),
            ("Motorola", "Moto g24 power", "Smartphone"),
            ("Kensington", "M01440-K", "Periferico"),
            ("Kensington", "M01440-M", "Periferico"),
            ("klipxtreme", "KPM-300", "Periferico"),
            ("Samsung", "LS22D300GALXZS", "Monitor"),
            ("Hp", "255R G10", "Notebook"),
            ("Asus", "TUF A15", "Notebook"),
            ("Lenovo", "LOQ 15ARP9", "Notebook"),
            ("Canon", "GX7010", "Impresora"),
            ("HUAWEI", "B320-523", "Router"),
            ("Hp", "Victus 15-fbo0115la", "Notebook"),
            ("hp", "Victus 15-fbo0115la", "Notebook"),
            ("Brother", "DCP-T720DW", "Impresora"),
            ("Brother", "DCP-L3551CDW", "Impresora"),
            ("LG", "24MK430H", "Monitor"),
            ("LG", "22M38H-B", "Monitor"),
            ("Samsung", "S22A336NHL", "Monitor"),
            ("Hp", "15-DY5000LA", "Notebook"),
            ("Lenovo", "THINKPAD", "Notebook"),
            ("Oppo", "CPH2579", "Smartphone"),
            ("Lenovo", "81WB", "Notebook"),
            ("Lenovo", "P51", "Notebook"),
            ("Brother", "DCP T220", "Impresora"),
            ("Brother", "DCP T310", "Impresora"),
            ("Brother", "DCP T520W", "Impresora"),
            ("Lenovo", "Ideapad Gaming 3 81Y4", "Notebook"),
            ("LENOVO", "TAB M11", "Smartphone"),
            ("Epson", "WF-C5890", "Impresora"),
            ("Dell", "Latitude 5420", "Notebook"),
            ("HUAWEI", "BLU CASTLE CPE 4G", "Router"),
            ("Dell", "Latitude P137G", "Notebook"),
            ("Huawei", "B320-523", "Router"),
            ("Oppo", "Y03", "Smartphone"),
            ("Asus", "X515J", "Notebook"),
            ("Kolke", "KES-461", "Monitor"),
            ("Samsung", "SM-X730", "Smartphone"),
            ("Asus", "VIVOBOOK", "Notebook"),
            ("Oppo", "A38", "Smartphone"),
            ("HP", "DESINGJET T250", "Impresora"),
            ("Starlink", "Starlink V4", "Router"),
            ("Huawei", "b535-636", "Router"),
            ("HP", "DESIGN JET", "Impresora"),
            ("Huawei", "H153-581", "Router"),
            ("Dell", "T470", "Notebook"),
            ("Oppo", "CPH2483", "Smartphone"),
            ("Apple", "IPHONE 16E", "Smartphone"),
            ("M4N0CX03Y713140", "X413JA-211.VBWB", "Notebook"),
            ("Honor", "GFY-LX3", "Smartphone"),
            ("HP", "OFFICE JET PRO 7740", "Impresora"),
            ("Canon", "G4110", "Impresora"),
            ("Otro", "BLU CASTLE CPE 4G", "Router"),
            ("Dell", "Latitude e6520", "Notebook"),
            ("Lenovo", "THINKPAD 11E YOGA GEN 6", "Notebook"),
            ("klipxtreme", "KDA-500", "Periferico"),
            ("Epson", "L3250", "Impresora"),
            ("Dell", "PRECISION 7530", "Notebook"),
            ("Hp", "M22F", "Monitor"),
            ("AOC", "E2270SW", "Monitor"),
            ("Lenovo", "ThinkBook 14G8 IRL", "Notebook"),
            ("Lenovo", "LOQ 15IAX9", "Notebook"),
            ("Lenovo", "LOQ 15ARP9", "Notebook"),
            ("Samsung", "SM-A175F/DS", "Smartphone"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Brother", "MFC-T4500DW", "Impresora"),
            ("Dell", "PRECISION 7550", "Notebook"),
            ("Brother", "DCP-T720DW", "Impresora"),
            ("Brother", "MFC-T4500DW", "Impresora"),
            ("Brother", "MFC-T930DW", "Impresora"),
            ("Samsung", "LS22D300GALXZS", "Monitor"),
            ("Asus", "x515j", "Notebook"),
            ("Asus", "TUF A15", "Notebook"),
            ("Samsung", "LS22D300GALXZS", "Monitor"),
            ("Asus", "X515J", "Notebook"),
            ("Samsung", "SM-A175F/DS", "Smartphone"),
            ("Lenovo", "LOQ 15IAX9", "Notebook"),
            ("Samsung", "SM-A175F/DS", "Smartphone"),
            ("Lenovo", "T470", "Notebook"),
            ("Asus", "X515J", "Notebook"),
            ("Kolke", "KES-461", "Monitor"),
            ("Asus", "E1404G", "Notebook"),
            ("Canon", "GX7010", "Impresora"),
            ("Vivo", "V2332", "Smartphone"),
            ("Samsung", "", "Smartphone"),
            ("Lenovo", "LOQ 15ARP9", "Notebook"),
            ("POCO", "C85", "Smartphone"),
            ("Lenovo", "LOQ 15IAX9", "Notebook"),
            ("Lenovo", "LOQ 15IAX9", "Notebook"),
            ("Hp", "255R G10", "Notebook"),
            ("Brother", "MFC-T4500DW", "Impresora"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Hikvision", "DS-D5027F2-1P2", "Monitor"),
            ("Dell", "Latitude 7530", "Notebook"),
            ("Dell", "Latitude 5420", "Notebook"),
            ("Dell", "Latitude 5420", "Notebook"),
            ("Lenovo", "ThinkBook 14G8 IRL", "Notebook"),
            ("LENOVO", "TAB M11", "Smartphone"),
            ("Samsung", "S24R35AFHLXZS", "Monitor"),
            ("STARLINK", "Starlink V4", "Router"),
            ("LENOVO", "TAB M11", "Smartphone"),
            ("LENOVO", "TAB M11", "Smartphone"),
            ("LENOVO", "TAB M11", "Smartphone"),
            ("LENOVO", "TAB M11", "Smartphone"),
            ("Asus", "TUF A15", "Notebook"),
            ("HP", "DESINGJET T250", "Impresora"),
            ("LG", "22MN430H", "Monitor"),
            ("Kolke", "KES-461", "Monitor"),
            ("HUAWEI", "B320-23", "Router"),
            ("Dell", "Latitude 5420", "Notebook"),
            ("Epson", "WF-C5890", "Impresora"),
            ("Hp", "255R G10", "Notebook"),
            ("LG", "22MN430H", "Monitor"),
            ("Epson", "WF-C5890", "Impresora"),
            ("Oppo", "CPH2483", "Smartphone"),
            ("POCO", "C85", "Smartphone"),
            ("Asus", "TUF A15", "Notebook"),
            ("Epson", "WF-C5890", "Impresora"),
            ("STARLINK", "Starlink V4", "Router"),
            ("Lenovo", "Idea pad 5 14alc05", "Notebook"),
            ("Lenovo", "T470", "Notebook"),
            ("Lenovo", "Idea pad 5 14ahp9", "Notebook"),
        ]

        # Normalizar fabricantes: lower() → nombre canónico (title case)
        fabricante_canon = {}
        for fab, mod, tip in raw_rows:
            if not fab:
                continue
            key = fab.strip().lower()
            if key not in fabricante_canon:
                # Mantenemos el primer casing encontrado como canónico,
                # pero forzamos primera letra mayúscula para legibilidad
                fabricante_canon[key] = fab.strip().title()

        created_fab = 0
        for canon in fabricante_canon.values():
            _, was_created = Fabricante.objects.get_or_create(nombre=canon)
            if was_created:
                created_fab += 1

        # Cache de lookups
        tipos_qs = {t.nombre.lower(): t for t in TipoDispositivo.objects.all()}
        fabs_qs = {f.nombre.lower(): f for f in Fabricante.objects.all()}

        # Normalizar modelos (unique por nombre+fabricante)
        modelos_vistos = set()
        created_mod = 0
        for fab_raw, mod_raw, tipo_raw in raw_rows:
            mod = mod_raw.strip()
            if not mod:
                continue

            tipo_key = tipo_raw.strip().lower()
            tipo_nombre = tipo_map.get(tipo_key)
            if not tipo_nombre:
                continue

            tipo_obj = tipos_qs.get(tipo_nombre.lower())
            if not tipo_obj:
                continue

            fab_key = fab_raw.strip().lower()
            fab_nombre = fabricante_canon.get(fab_key, fab_raw.strip().title())
            fab_obj = fabs_qs.get(fab_nombre.lower())
            if not fab_obj:
                continue

            unique_key = (mod.lower(), fab_nombre.lower())
            if unique_key in modelos_vistos:
                continue
            modelos_vistos.add(unique_key)

            _, was_created = Modelo.objects.get_or_create(
                nombre=mod,
                fabricante=fab_obj,
                defaults={"tipo_dispositivo": tipo_obj},
            )
            if was_created:
                created_mod += 1

        self.stdout.write(f"  Fabricantes: {created_fab} nuevo(s)")
        self.stdout.write(f"  Modelos: {created_mod} nuevo(s)")
        return created_fab, created_mod

    # ───────────────────────────────────────────────
    # 6. Constance
    # ───────────────────────────────────────────────
    def _seed_constance(self):
        # Asegura que el prefijo de IDs esté configurado
        config.CLI_PREFIX_ID = "JMIE"
        self.stdout.write("  Constance: CLI_PREFIX_ID = JMIE")

    # ───────────────────────────────────────────────
    # 7. Usuario admin de prueba
    # ───────────────────────────────────────────────
    def _seed_admin_user(self):
        user, created = Colaborador.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@jmie.cl",
                "first_name": "Administrador",
                "last_name": "Sistema",
                "is_staff": True,
                "is_superuser": True,
                "esta_activo": True,
            },
        )
        if created:
            user.set_password("admin123")
            user.save()
            self.stdout.write(self.style.SUCCESS("  Usuario admin creado (admin / admin123)"))
        else:
            # Asegurar privilegios si ya existía
            user.is_staff = True
            user.is_superuser = True
            user.esta_activo = True
            user.save(update_fields=["is_staff", "is_superuser", "esta_activo"])
            self.stdout.write("  Usuario admin ya existía, privilegios actualizados")
