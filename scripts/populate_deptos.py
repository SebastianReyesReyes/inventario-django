import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_jmie.settings')
django.setup()

from core.models import Departamento

departamentos = [
    "TI",
    "Gerencia General",
    "Operaciones",
    "Propuestas",
    "Administración y Finanzas",
    "Adquisiciones",
    "Oficina Técnica / BIM",
    "Prevención de Riesgos",
    "Bodega",
    "Recursos Humanos"
]

for depto_nombre in departamentos:
    obj, created = Departamento.objects.get_or_create(nombre=depto_nombre)
    if created:
        print(f"Creado: {depto_nombre}")
    else:
        print(f"Ya existe: {depto_nombre}")
