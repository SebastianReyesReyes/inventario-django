from .ajax import ajax_get_modelos, ajax_crear_modelo, ajax_get_tech_fields
from .crud import (
    dispositivo_create,
    dispositivo_list,
    dispositivo_detail,
    dispositivo_update,
    dispositivo_delete,
)
from .trazabilidad import (
    dispositivo_asignar,
    dispositivo_reasignar,
    dispositivo_devolver,
    dispositivo_historial,
)
from .mantenimiento import mantenimiento_create, mantenimiento_update
from .accesorios import colaborador_entrega_accesorio, colaborador_historial_accesorios
from .qr import dispositivo_qr
