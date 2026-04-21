from django.db import models
from django.contrib.auth.models import AbstractUser
from core.models import Departamento, CentroCosto

class Colaborador(AbstractUser):
    rut = models.CharField(max_length=15, unique=True, null=True, blank=True)
    cargo = models.CharField(max_length=100, null=True, blank=True)
    departamento = models.ForeignKey(Departamento, on_delete=models.SET_NULL, null=True, blank=True)
    centro_costo = models.ForeignKey(CentroCosto, on_delete=models.SET_NULL, null=True, blank=True)
    azure_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    # Campo para identificar si el registro es "activo" operativamente
    # (independiente de is_active de Django para permisos)
    esta_activo = models.BooleanField(default=True)

    def delete(self, *args, **kwargs):
        """Baja lógica: No borramos físicamente el registro para proteger el historial."""
        self.esta_activo = False
        self.is_active = False # Quitamos acceso al sistema
        self.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @property
    def nombre_completo(self):
        """Retorna el nombre completo concatenado."""
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username

    def __str__(self):
        return self.nombre_completo

    class Meta:
        verbose_name = "Colaborador"
        verbose_name_plural = "Colaboradores"
