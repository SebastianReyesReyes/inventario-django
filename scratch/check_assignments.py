import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_jmie.settings')
django.setup()

from dispositivos.models import HistorialAsignacion
from colaboradores.models import Colaborador

print("Colaboradores:")
for c in Colaborador.objects.all():
    count = HistorialAsignacion.objects.filter(colaborador=c, acta__isnull=True, fecha_fin__isnull=True).count()
    print(f"- {c.nombre_completo} (ID: {c.pk}): {count} asignaciones pendientes")

print("\nAsignaciones totales sin acta:")
print(HistorialAsignacion.objects.filter(acta__isnull=True).count())
