from django.core.management.base import BaseCommand
from core.models import CentroCosto

class Command(BaseCommand):
    help = 'Carga los centros de costo oficiales de JMIE.'

    def handle(self, *args, **kwargs):
        data = [
            "218- Hospital de Chillán",
            "114- Oficina Central",
            "2308- Edificio Eco Florida",
            "2309- Hospital de Parral",
            "2401- Los Militares",
            "2403- Hospital Cordillera",
            "2501- Hospital Sotero del Rio",
            "2502- Datacenter Colina",
            "2503- EPC - Ampliació CD Lo Aguirre",
            "2504- Hospital Río Bueno",
            "2506- Datacenter Huechuraba",
            "2507- Scala Data Santa Teresa",
            "2601- Modular",
            "2602- Strip center",
        ]

        created_count = 0
        for item in data:
            if '-' in item:
                codigo, nombre = item.split('-', 1)
                obj, created = CentroCosto.objects.update_or_create(
                    codigo_contable=codigo.strip(),
                    defaults={'nombre': nombre.strip(), 'activa': True}
                )
                if created:
                    created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Se crearon {created_count} nuevos centros de costo.'))
