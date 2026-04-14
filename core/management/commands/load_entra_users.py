import csv
import os
from django.core.management.base import BaseCommand
from colaboradores.models import Colaborador
from core.models import Departamento

class Command(BaseCommand):
    help = 'Loads users from Entra ID CSV export.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file}'))
            return

        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            created_count = 0
            updated_count = 0
            
            for row in reader:
                user_principal_name = row.get('User principal name')
                if not user_principal_name:
                    continue
                
                email = user_principal_name.strip()
                username = email  # using email as username
                first_name = row.get('First name', '').strip()
                last_name = row.get('Last name', '').strip()
                azure_id = row.get('Object Id', '').strip()
                title = row.get('Title', '').strip()
                department_name = row.get('Department', '').strip()
                
                # Fetch or create department
                departamento = None
                if department_name:
                    departamento, _ = Departamento.objects.get_or_create(nombre=department_name)
                    
                colaborador, created = Colaborador.objects.update_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'azure_id': azure_id if azure_id else None,
                        'cargo': title,
                        'departamento': departamento,
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully synced {created_count + updated_count} users ({created_count} created, {updated_count} updated)'))
