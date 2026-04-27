import os
from django.core.management.base import BaseCommand
from core.services import importar_catalogos_desde_csv


class Command(BaseCommand):
    help = 'Importa catálogos base (fabricantes, modelos, tipos) desde un archivo CSV.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Ruta al archivo CSV')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecuta sin guardar cambios en la base de datos',
        )

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        dry_run = kwargs.get('dry_run', False)

        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'Archivo no encontrado: {csv_file}'))
            return

        with open(csv_file, 'rb') as f:
            resultado = importar_catalogos_desde_csv(f, dry_run=dry_run)

        for log in resultado['logs']:
            if log.startswith('[DRY-RUN]'):
                self.stdout.write(f"  {log}")
            elif 'creado' in log.lower():
                self.stdout.write(self.style.WARNING(f"  {log}"))
            elif 'saltando' in log.lower() or 'falta' in log.lower():
                self.stdout.write(self.style.WARNING(f"  {log}"))
            elif 'error' in log.lower():
                self.stdout.write(self.style.ERROR(f"  {log}"))
            else:
                self.stdout.write(f"  {log}")

        self.stdout.write(self.style.NOTICE("=" * 50))
        self.stdout.write(self.style.NOTICE("RESUMEN DE IMPORTACIÓN DE CATÁLOGOS"))
        self.stdout.write(self.style.NOTICE("=" * 50))
        self.stdout.write(f"Total filas leídas:       {resultado['total']}")
        self.stdout.write(f"Saltadas (incompletas):   {resultado['saltados']}")

        if dry_run:
            self.stdout.write(self.style.WARNING("MODO DRY-RUN: no se guardaron cambios."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Fabricantes creados:      {resultado['creados_fab']}"))
            self.stdout.write(self.style.SUCCESS(f"Tipos creados:            {resultado['creados_tipo']}"))
            self.stdout.write(self.style.SUCCESS(f"Modelos creados:          {resultado['creados_modelo']}"))
            self.stdout.write(self.style.SUCCESS(f"Modelos actualizados:     {resultado['actualizados_modelo']}"))

        if resultado['errores']:
            self.stdout.write(self.style.ERROR(f"Filas con error:          {resultado['errores']}"))

        self.stdout.write(self.style.NOTICE("=" * 50))
