from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import (
    Dispositivo, HistorialAsignacion,
    Notebook, Smartphone, Impresora, Servidor, EquipoRed, Monitor
)
from django.utils import timezone


def _handle_assignment(instance, **kwargs):
    """
    Crea automáticamente un registro de HistorialAsignacion si el dispositivo
    tiene un propietario_actual al ser creado o actualizado, y no existe una 
    asignación activa para ese par.
    
    Funciona con Dispositivo y todos sus hijos (Notebook, Smartphone, etc.)
    gracias a que accedemos al objeto base Dispositivo via instance.dispositivo_ptr
    o directamente si ya es el padre.
    """
    # Obtenemos la referencia al Dispositivo base
    # En herencia multi-tabla, el hijo tiene un dispositivo_ptr
    base_device = getattr(instance, 'dispositivo_ptr', instance)
    
    if instance.propietario_actual:
        # Verificar si ya existe una asignación activa para este colaborador y equipo
        exists = HistorialAsignacion.objects.filter(
            dispositivo=base_device,
            colaborador=instance.propietario_actual,
            fecha_fin__isnull=True
        ).exists()
        
        if not exists:
            # 1. Si el equipo ya tenía otra asignación abierta con OTRO dueño, cerrarla
            HistorialAsignacion.objects.filter(
                dispositivo=base_device,
                fecha_fin__isnull=True
            ).exclude(colaborador=instance.propietario_actual).update(fecha_fin=timezone.now().date())
            
            # 2. Crear la nueva asignación
            HistorialAsignacion.objects.create(
                dispositivo=base_device,
                colaborador=instance.propietario_actual,
                condicion_fisica=instance.notas_condicion or "Asignado automáticamente vía cambio de propietario."
            )
    else:
        # Si se quitó el propietario_actual, cerramos cualquier asignación abierta
        HistorialAsignacion.objects.filter(
            dispositivo=base_device,
            fecha_fin__isnull=True
        ).update(fecha_fin=timezone.now().date())


# Registramos el signal para el modelo base Y para cada subclase
# Django envía post_save con sender=ClaseReal, no sender=ClasePadre
@receiver(post_save, sender=Dispositivo)
def handle_dispositivo_save(sender, instance, **kwargs):
    _handle_assignment(instance, **kwargs)

@receiver(post_save, sender=Notebook)
def handle_notebook_save(sender, instance, **kwargs):
    _handle_assignment(instance, **kwargs)

@receiver(post_save, sender=Smartphone)
def handle_smartphone_save(sender, instance, **kwargs):
    _handle_assignment(instance, **kwargs)

@receiver(post_save, sender=Impresora)
def handle_impresora_save(sender, instance, **kwargs):
    _handle_assignment(instance, **kwargs)

@receiver(post_save, sender=Servidor)
def handle_servidor_save(sender, instance, **kwargs):
    _handle_assignment(instance, **kwargs)

@receiver(post_save, sender=EquipoRed)
def handle_equipored_save(sender, instance, **kwargs):
    _handle_assignment(instance, **kwargs)

@receiver(post_save, sender=Monitor)
def handle_monitor_save(sender, instance, **kwargs):
    _handle_assignment(instance, **kwargs)
