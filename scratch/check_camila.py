import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_jmie.settings')
django.setup()

from dispositivos.models import Dispositivo
from colaboradores.models import Colaborador

camila = Colaborador.objects.get(first_name='Camila', last_name='Camos' if False else 'Campos')
print(f"Colaborador: {camila}")

equipos = Dispositivo.objects.filter(propietario_actual=camila)
print(f"Equipos de Camila: {equipos.count()}")
for e in equipos:
    print(f"- {e.identificador_interno} ({e.modelo})")
