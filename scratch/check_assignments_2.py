import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_jmie.settings')
django.setup()

from dispositivos.models import HistorialAsignacion

total = HistorialAsignacion.objects.count()
con_acta = HistorialAsignacion.objects.filter(acta__isnull=False).count()
sin_acta = HistorialAsignacion.objects.filter(acta__isnull=True).count()

print(f"Total: {total}")
print(f"Con Acta: {con_acta}")
print(f"Sin Acta: {sin_acta}")

if total > 0:
    first = HistorialAsignacion.objects.first()
    print(f"\nEjemplo - ID: {first.pk}, Colaborador: {first.colaborador}, Acta: {first.acta}")
