import os
import django
import sys

# Añadir el directorio raíz al path para que reconozca los módulos
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_jmie.settings')
django.setup()

from core.models import TipoDispositivo
from dispositivos.models import Dispositivo

def run():
    mapping = {
        'Notebook': 'NTBK',
        'Smartphone': 'SMPH',
        'Impresora': 'IMPR',
        'Servidor': 'SRVR',
        'PC': 'CPTR',
        'Tablet': 'TBLT',
        'Monitor': 'MNTR',
        'Cámara': 'CAMR'
    }

    print("Configurando siglas para Tipos de Dispositivo...")
    for tipo in TipoDispositivo.objects.all():
        tipo.sigla = mapping.get(tipo.nombre, tipo.nombre[:4].upper())
        tipo.save()
        print(f" - {tipo.nombre} -> {tipo.sigla}")

    print("\nRegenerando IDs Internos para Dispositivos...")
    # Limpiamos para evitar colisiones
    for d in Dispositivo.objects.all().order_by('pk'):
        d.identificador_interno = f"OLD-{d.pk}"
        d.save()

    for d in Dispositivo.objects.all().order_by('pk'):
        d.identificador_interno = ""
        d.save()
        print(f" - [{d.tipo.sigla}] {d.modelo} -> {d.identificador_interno}")

if __name__ == "__main__":
    run()
