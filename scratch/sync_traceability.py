import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_jmie.settings')
django.setup()

from dispositivos.models import Dispositivo, HistorialAsignacion

def sync_assignments():
    asignas = Dispositivo.objects.filter(propietario_actual__isnull=False)
    created_count = 0
    
    for d in asignas:
        # Solo creamos si no tiene una asignación activa ya registrada
        if not HistorialAsignacion.objects.filter(dispositivo=d, fecha_fin__isnull=True).exists():
            HistorialAsignacion.objects.create(
                dispositivo=d,
                colaborador=d.propietario_actual,
                condicion_fisica=d.notas_condicion or "Condición inicial al momento de la sincronización."
            )
            created_count += 1
            
    return created_count

if __name__ == "__main__":
    count = sync_assignments()
    print(f"Sincronización completada. Se crearon {count} registros de historial.")
