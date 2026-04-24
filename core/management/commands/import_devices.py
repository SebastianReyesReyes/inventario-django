import csv
import os
import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import TipoDispositivo, EstadoDispositivo, Modelo, CentroCosto, Fabricante
from dispositivos.models import Dispositivo
from colaboradores.models import Colaborador


class Command(BaseCommand):
    help = 'Importa dispositivos desde un archivo CSV.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Ruta al archivo CSV')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecuta sin guardar cambios en la base de datos',
        )

    def _get_value(self, row, *keys):
        """Busca el primer valor no vacío entre las claves candidatas."""
        for key in keys:
            val = row.get(key, '').strip()
            if val:
                return val
        return None

    def _normalize_serie(self, valor):
        """Normaliza el número de serie; genera uno automático si está vacío o es N/A."""
        valor = (valor or '').strip()
        if not valor or valor.upper() in ('N/A', 'PENDIENTE', 'S/N', 'SN'):
            return f"AUTO-{uuid.uuid4().hex[:8].upper()}"
        return valor

    def _get_or_create_tipo(self, nombre):
        """Obtiene o crea un TipoDispositivo, asegurando que tenga sigla para la secuencia de IDs."""
        tipo, created = TipoDispositivo.objects.get_or_create(nombre=nombre)
        if created or not tipo.sigla:
            # Generar sigla automática a partir del nombre (máx 5 caracteres alfanuméricos)
            base = ''.join(c for c in nombre.upper() if c.isalnum())[:5]
            if not base:
                base = "EQUIP"
            sigla = base
            counter = 1
            while TipoDispositivo.objects.filter(sigla=sigla).exclude(pk=tipo.pk).exists():
                sigla = f"{base[:4]}{counter}"
                counter += 1
            tipo.sigla = sigla
            tipo.save(update_fields=['sigla'])
            self.stdout.write(
                self.style.WARNING(f"  Tipo '{nombre}' {'creado' if created else 'actualizado'} con sigla auto-generada: {sigla}")
            )
        return tipo

    def _find_colaborador(self, full_name):
        """Busca un colaborador por nombre completo (first_name / last_name)."""
        if not full_name:
            return None
        full_name = full_name.strip()
        parts = full_name.split(' ', 1)
        if len(parts) == 1:
            return Colaborador.objects.filter(first_name__icontains=parts[0]).first()
        else:
            first, last = parts
            return Colaborador.objects.filter(first_name__icontains=first, last_name__icontains=last).first()

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        dry_run = kwargs.get('dry_run', False)

        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'Archivo no encontrado: {csv_file}'))
            return

        # Centro de costo por defecto
        default_cc, _ = CentroCosto.objects.get_or_create(
            nombre='Central', defaults={'codigo_contable': '0000'}
        )

        total = 0
        creados = 0
        actualizados = 0
        errores = 0
        saltados = 0

        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                total += 1
                row_num = total + 1  # +1 por el header

                # --- Extracción robusta de columnas ---
                tipo_nombre = self._get_value(
                    row, 'tipo', 'Tipo de activo', 'tipo_dispositivo', 'tipo de activo'
                )
                if not tipo_nombre:
                    self.stdout.write(
                        self.style.WARNING(f"Fila {row_num}: sin tipo de dispositivo, saltando.")
                    )
                    saltados += 1
                    continue

                fabricante_nombre = self._get_value(
                    row,
                    'fabricante', 'Fabricante (Pc)', 'Fabricante (Monitor)',
                    'Fabricante (Celular)', 'Fabricante (Almacenamiento)',
                    'Fabricante (Impresora)', 'Fabricante (Periférico)',
                    'Fabricante (Servidor)', 'Fabricante (Modem)',
                ) or "Desconocido"

                modelo_nombre = self._get_value(
                    row,
                    'modelo', 'Modelo (PC)', 'Modelo (Monitor)',
                    'Modelo (Celular)', 'Modelo (Almacenamiento)',
                    'Modelo (Impresora)', 'Modelo (Periférico)',
                    'Modelo (Servidor)', 'Modelo (Modem)',
                ) or "Desconocido"

                estado_nombre = self._get_value(
                    row, 'estado', 'Estado', 'estado_dispositivo'
                ) or 'Desconocido'

                numero_serie = self._normalize_serie(
                    self._get_value(row, 'numero_serie', 'Número de serie', 'serie')
                )

                propietario_nombre = self._get_value(
                    row, 'colaborador', 'Propietario actual', 'propietario', 'asignado_a'
                )

                notas = self._get_value(
                    row, 'notas_condicion', 'Notas de la condición', 'condicion', 'notas'
                ) or ''

                try:
                    with transaction.atomic():
                        tipo = self._get_or_create_tipo(tipo_nombre)
                        estado, _ = EstadoDispositivo.objects.get_or_create(nombre=estado_nombre)
                        fabricante, _ = Fabricante.objects.get_or_create(nombre=fabricante_nombre)
                        # CORRECCIÓN: fabricante DEBE ir en los argumentos de búsqueda
                        # porque Modelo tiene unique_together = ('nombre', 'fabricante')
                        modelo, _ = Modelo.objects.get_or_create(
                            nombre=modelo_nombre, fabricante=fabricante
                        )
                        colaborador = self._find_colaborador(propietario_nombre)

                        if dry_run:
                            self.stdout.write(
                                f"  [DRY-RUN] Fila {row_num}: tipo={tipo_nombre} | "
                                f"modelo={modelo_nombre} | sn={numero_serie} | "
                                f"estado={estado_nombre}"
                            )
                            continue

                        # IMPORTANTE: No pasamos 'identificador_interno' en defaults.
                        # El modelo Dispositivo genera automáticamente la secuencia
                        # JMIE-SIGLA-0001 en su método .save()
                        dispositivo, created = Dispositivo.objects.update_or_create(
                            numero_serie=numero_serie,
                            defaults={
                                'tipo': tipo,
                                'estado': estado,
                                'modelo': modelo,
                                'propietario_actual': colaborador,
                                'centro_costo': default_cc,
                                'notas_condicion': notas,
                            }
                        )

                        if created:
                            creados += 1
                        else:
                            actualizados += 1

                except Exception as e:
                    errores += 1
                    self.stdout.write(
                        self.style.ERROR(f"Fila {row_num} (SN:{numero_serie}): {e}")
                    )

        # --- Resumen final ---
        self.stdout.write(self.style.NOTICE("=" * 50))
        self.stdout.write(self.style.NOTICE("RESUMEN DE IMPORTACIÓN"))
        self.stdout.write(self.style.NOTICE("=" * 50))
        self.stdout.write(f"Total filas leídas:       {total}")
        self.stdout.write(f"Saltadas (sin tipo):      {saltados}")

        if dry_run:
            self.stdout.write(self.style.WARNING("MODO DRY-RUN: no se guardaron cambios."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Dispositivos creados:     {creados}"))
            self.stdout.write(self.style.SUCCESS(f"Dispositivos actualizados:{actualizados}"))

        if errores:
            self.stdout.write(self.style.ERROR(f"Filas con error:          {errores}"))

        self.stdout.write(self.style.NOTICE("=" * 50))
