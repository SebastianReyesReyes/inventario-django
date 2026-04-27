from django.db import transaction
from .models import Suministro, MovimientoStock

@transaction.atomic
def registrar_movimiento_stock(
    suministro_id: int,
    tipo_movimiento: str,
    cantidad: int,
    registrado_por_id: int,
    colaborador_destino_id: int = None,
    centro_costo_id: int = None,
    costo_unitario: int = None,
    numero_factura: str = None,
    notas: str = ""
) -> MovimientoStock:
    """
    Registra un movimiento de stock y recalcula el stock actual del suministro.
    Valida atómicamente que el stock no sea negativo en caso de salidas.
    """
    # Select_for_update garantiza que no haya condiciones de carrera al leer/escribir el stock
    suministro = Suministro.objects.select_for_update().get(id=suministro_id)
    
    # Crear el movimiento
    movimiento = MovimientoStock(
        suministro=suministro,
        tipo_movimiento=tipo_movimiento,
        cantidad=cantidad,
        registrado_por_id=registrado_por_id,
        notas=notas
    )
    
    # Asignaciones condicionales basadas en el tipo de movimiento
    if tipo_movimiento == MovimientoStock.TipoMovimiento.ENTRADA:
        movimiento.costo_unitario = costo_unitario
        movimiento.numero_factura = numero_factura
    elif tipo_movimiento == MovimientoStock.TipoMovimiento.SALIDA:
        movimiento.colaborador_destino_id = colaborador_destino_id
        movimiento.centro_costo_id = centro_costo_id
        
    # El método clean() del modelo valida que el stock_actual sea >= cantidad si es salida
    movimiento.clean() 
    movimiento.save()
    
    # Recalcular el stock (ahora que el movimiento está guardado)
    suministro.recalcular_stock()
    
    return movimiento
