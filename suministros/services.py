from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Suministro, MovimientoStock

def get_pack_siblings(suministro: Suministro):
    """
    Retorna otros suministros que tienen EXACTAMENTE el mismo conjunto
    de modelos compatibles (fingerprint). Útil para kits de toners.
    """
    modelos_ids = list(suministro.modelos_compatibles.values_list('id', flat=True).order_by('id'))
    if not modelos_ids:
        return Suministro.objects.none()
    
    # Buscamos otros que compartan la misma cantidad de modelos y todos los IDs
    # (Enfoque manual para evitar queries complejas de ManyToMany en SQLite)
    siblings = Suministro.objects.activos().exclude(id=suministro.id).prefetch_related('modelos_compatibles')
    
    match_ids = []
    for s in siblings:
        s_modelos_ids = list(s.modelos_compatibles.values_list('id', flat=True).order_by('id'))
        if s_modelos_ids == modelos_ids:
            match_ids.append(s.id)
            
    return Suministro.objects.filter(id__in=match_ids).select_related('categoria', 'fabricante')

@transaction.atomic
def registrar_movimiento_stock(
    suministro_id: int,
    tipo_movimiento: str,
    cantidad: int,
    registrado_por_id: int,
    colaborador_destino_id: int = None,
    centro_costo_id: int = None,
    dispositivo_destino_id: int = None,
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
        movimiento.dispositivo_destino_id = dispositivo_destino_id
        
    # El método clean() del modelo valida que el stock_actual sea >= cantidad si es salida
    movimiento.clean() 

    # Lógica de alerta de consumo inusual (Gonzalo's requirement)
    if tipo_movimiento == MovimientoStock.TipoMovimiento.SALIDA and suministro.duracion_estimada_dias:
        # Buscamos la última salida del mismo suministro para el mismo destino
        ultimo_mov = MovimientoStock.objects.filter(
            suministro=suministro,
            tipo_movimiento=MovimientoStock.TipoMovimiento.SALIDA,
            colaborador_destino_id=colaborador_destino_id,
            dispositivo_destino_id=dispositivo_destino_id
        ).order_by('-fecha').first()

        if ultimo_mov:
            dias_pasados = (timezone.now() - ultimo_mov.fecha).days
            if dias_pasados < suministro.duracion_estimada_dias:
                advertencia = f"⚠️ ALERTA: Consumo inusual. Duración estimada: {suministro.duracion_estimada_dias} días. Han pasado solo {dias_pasados} días desde la última entrega."
                if movimiento.notas:
                    movimiento.notas = f"{advertencia}\n{movimiento.notas}"
                else:
                    movimiento.notas = advertencia

    movimiento.save()
    
    # Recalcular el stock (ahora que el movimiento está guardado)
    suministro.recalcular_stock()
    
    return movimiento

@transaction.atomic
def registrar_movimiento_pack(
    movimientos_data: list,
    tipo_movimiento: str,
    registrado_por_id: int,
    colaborador_destino_id: int = None,
    centro_costo_id: int = None,
    dispositivo_destino_id: int = None,
    numero_factura: str = None,
    notas_comunes: str = ""
):
    """
    Registra múltiples movimientos de stock (pack) de forma atómica.
    movimientos_data: list of dicts {'suministro_id': int, 'cantidad': int, 'costo_unitario': int (opt)}
    """
    movimientos_registrados = []
    for item in movimientos_data:
        if item['cantidad'] <= 0:
            continue
            
        mov = registrar_movimiento_stock(
            suministro_id=item['suministro_id'],
            tipo_movimiento=tipo_movimiento,
            cantidad=item['cantidad'],
            registrado_por_id=registrado_por_id,
            colaborador_destino_id=colaborador_destino_id,
            centro_costo_id=centro_costo_id,
            dispositivo_destino_id=dispositivo_destino_id,
            costo_unitario=item.get('costo_unitario'),
            numero_factura=numero_factura,
            notas=notas_comunes
        )
        movimientos_registrados.append(mov)
    
    return movimientos_registrados
