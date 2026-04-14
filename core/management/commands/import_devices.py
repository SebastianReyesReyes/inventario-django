import csv
import os
import uuid
from datetime import datetime
from django.core.management.base import BaseCommand
from dispositivos.models import Dispositivo, TipoDispositivo, Estado, Modelo, CentroCosto
from colaboradores.models import Colaborador
from core.models import Fabricante
from django.db.models import Prefetch

class Command(BaseCommand):
    help = 'Loads devices from CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file')

    def find_colaborador(self, full_name):
        if not full_name:
            return None
        parts = full_name.strip().split(' ', 1)
        if len(parts) == 1:
            return Colaborador.objects.filter(first_name__icontains=parts[0]).first()
        else:
            first, last = parts
            return Colaborador.objects.filter(first_name__icontains=first, last_name__icontains=last).first()

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file}'))
            return

        default_cc, _ = CentroCosto.objects.get_or_create(nombre='Central', defaults={'codigo_contable': '0000'})
        
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            created_count = 0
            
            for row in reader:
                tipo_nombre = row.get('Tipo de activo', '').strip()
                if not tipo_nombre:
                    continue
                
                estado_nombre = row.get('Estado', '').strip() or 'Desconocido'
                
                # Determine fabricante and modelo dynamically based on tipo
                fab_keys = ['Fabricante (Pc)', 'Fabricante (Monitor)', 'Fabricante (Celular)', 'Fabricante (Almacenamiento)', 'Fabricante (Impresora)', 'Fabricante (Periférico)', 'Fabricante (Servidor)', 'Fabricante (Modem)']
                mod_keys = ['Modelo (PC)', 'Modelo (Monitor)', 'Modelo (Celular)', 'Modelo (Almacenamiento)', 'Modelo (Impresora)', 'Modelo (Periférico)', 'Modelo (Servidor)', 'Modelo (Modem)']
                
                fabricante_nombre = "Desconocido"
                for key in fab_keys:
                    if row.get(key, '').strip():
                        fabricante_nombre = row.get(key).strip()
                        break
                        
                modelo_nombre = "Desconocido"
                for key in mod_keys:
                    if row.get(key, '').strip():
                        modelo_nombre = row.get(key).strip()
                        break
                
                numero_serie = row.get('Número de serie', '').strip()
                if not numero_serie or numero_serie.upper() in ['N/A', 'PENDIENTE']:
                    numero_serie = str(uuid.uuid4())[:8]
                    
                propietario_nombre = row.get('Propietario actual', '').strip()
                colaborador = self.find_colaborador(propietario_nombre)
                
                # Resolving FKs
                tipo, _ = TipoDispositivo.objects.get_or_create(nombre=tipo_nombre)
                estado, _ = Estado.objects.get_or_create(nombre=estado_nombre)
                fabricante, _ = Fabricante.objects.get_or_create(nombre=fabricante_nombre)
                modelo, _ = Modelo.objects.get_or_create(nombre=modelo_nombre, defaults={'fabricante': fabricante})
                
                identificador = f"JMIE-{str(uuid.uuid4().int)[:6]}"
                
                try:
                    Dispositivo.objects.update_or_create(
                        numero_serie=numero_serie,
                        defaults={
                            'identificador_interno': identificador,
                            'tipo': tipo,
                            'estado': estado,
                            'modelo': modelo,
                            'propietario_actual': colaborador,
                            'centro_costo': default_cc,
                            'notas_condicion': row.get('Notas de la condición', '')
                        }
                    )
                    created_count += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Error importando {numero_serie}: {e}"))
                
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {created_count} devices'))
