"""
Shared constants and mappings for the dispositivos app.

Extracted from dispositivos/views.py to allow reuse across view modules
and reduce duplication (TECH_FORMS appeared in both create and update views).
"""

from .forms import NotebookTechForm, SmartphoneTechForm, MonitorTechForm

# Mapping of device type slugs to their specialized tech form classes.
# Used in both dispositivo_create and dispositivo_update to instantiate
# the correct tech-specific form for each device type.
TECH_FORMS = {
    'notebook': NotebookTechForm,
    'smartphone': SmartphoneTechForm,
    'monitor': MonitorTechForm,
}

# Mapping of sort query-param values to ORM field paths for dispositivo_list.
SORT_MAP = {
    'id': 'identificador_interno',
    'tipo': 'modelo__tipo_dispositivo__nombre',
    'marca': 'modelo__fabricante__nombre',
    'modelo': 'modelo__nombre',
    'responsable': 'propietario_actual__first_name',
    'estado': 'estado__nombre',
    'cc': 'centro_costo__nombre',
    'acta': 'acta_firmada',
}
