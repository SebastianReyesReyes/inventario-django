import pytest
from django.utils import timezone
from core.tests.factories import (
    DispositivoFactory, ColaboradorFactory, 
    HistorialAsignacionFactory
)
from dispositivos.models import HistorialAsignacion

@pytest.mark.django_db
class TestDispositivoSignals:
    def test_automatic_assignment_on_new_device(self):
        """Validar que al crear un dispositivo con propietario, se genera el historial"""
        colaborador = ColaboradorFactory()
        # El signal usa instance.notas_condicion para la asignación
        dispositivo = DispositivoFactory(propietario_actual=colaborador, notas_condicion="Buen estado inicial")
        
        # El signal debe haber creado una asignación
        asignacion = HistorialAsignacion.objects.get(dispositivo=dispositivo)
        assert asignacion.colaborador == colaborador
        assert asignacion.fecha_fin is None
        assert asignacion.condicion_fisica == "Buen estado inicial"

    def test_automatic_closing_on_owner_change(self):
        """Validar que al cambiar el dueño, se cierra la asignación vieja y se abre la nueva"""
        owner1 = ColaboradorFactory(first_name="Owner 1")
        owner2 = ColaboradorFactory(first_name="Owner 2")
        dispositivo = DispositivoFactory(propietario_actual=owner1)
        
        # Primera asignación abierta
        asig1 = HistorialAsignacion.objects.get(dispositivo=dispositivo, colaborador=owner1, fecha_fin__isnull=True)
        
        # Cambiamos el dueño
        dispositivo.propietario_actual = owner2
        dispositivo.save()
        
        # La primera debe estar cerrada
        asig1.refresh_from_db()
        assert asig1.fecha_fin is not None
        assert asig1.fecha_fin == timezone.now().date()
        
        # Debe existir una segunda abierta para owner2
        asig2 = HistorialAsignacion.objects.get(dispositivo=dispositivo, colaborador=owner2, fecha_fin__isnull=True)
        assert asig2.colaborador == owner2

    def test_close_assignment_on_owner_removal(self):
        """Validar que al quitar el dueño (propietario = None), se cierra la asignación activa"""
        colaborador = ColaboradorFactory()
        dispositivo = DispositivoFactory(propietario_actual=colaborador)
        
        # Asignación abierta
        asig = HistorialAsignacion.objects.get(dispositivo=dispositivo, colaborador=colaborador, fecha_fin__isnull=True)
        
        # Quitamos el dueño
        dispositivo.propietario_actual = None
        dispositivo.save()
        
        # La asignación debe cerrarse
        asig.refresh_from_db()
        assert asig.fecha_fin is not None
        assert asig.fecha_fin == timezone.now().date()

    def test_no_duplicate_assignment_if_already_active(self):
        """Validar que no se crean duplicados si el dueño ya tiene la asignación activa"""
        colaborador = ColaboradorFactory()
        dispositivo = DispositivoFactory(propietario_actual=colaborador)
        
        initial_count = HistorialAsignacion.objects.filter(dispositivo=dispositivo).count()
        assert initial_count == 1
        
        # Guardamos de nuevo sin cambiar nada
        dispositivo.save()
        
        # El conteo debe seguir siendo 1
        assert HistorialAsignacion.objects.filter(dispositivo=dispositivo).count() == 1

    def test_signal_works_with_subclasses(self):
        """Validar que los signals funcionan correctamente con la herencia (Notebook)"""
        from dispositivos.models import Notebook
        colaborador = ColaboradorFactory()
        
        # Creamos una Notebook directamente con campos obligatorios
        notebook = Notebook.objects.create(
            numero_serie="NB-SIGNAL-123",
            propietario_actual=colaborador,
            estado=DispositivoFactory().estado,
            modelo=DispositivoFactory().modelo,
            centro_costo=DispositivoFactory().centro_costo,
            ram_gb=16,
            procesador="Intel i7",
            almacenamiento="512GB SSD",
            sistema_operativo="Windows 11"
        )
        
        # Debe haberse creado el historial para la base del dispositivo
        assert HistorialAsignacion.objects.filter(dispositivo=notebook.dispositivo_ptr, colaborador=colaborador).exists()
