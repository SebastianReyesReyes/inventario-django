import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_jmie.settings')
django.setup()

from dispositivos.models import Dispositivo

total_dispositivos = Dispositivo.objects.count()
asignados = Dispositivo.objects.filter(propietario_actual__isnull=False).count()

print(f"Total Dispositivos: {total_dispositivos}")
print(f"Dispositivos con propietario (propietario_actual): {asignados}")

if asignados > 0:
    for d in Dispositivo.objects.filter(propietario_actual__isnull=False)[:5]:
        print(f"- {d.identificador_interno} -> {d.propietario_actual}")
