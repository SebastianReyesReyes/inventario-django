import pytest
from django.core.exceptions import ValidationError
from suministros.models import CategoriaSuministro, Suministro, MovimientoStock
from suministros.services import registrar_movimiento_stock
from core.tests.factories import ColaboradorFactory

@pytest.mark.django_db
class TestSuministrosServices:

    @pytest.fixture
    def categoria(self):
        return CategoriaSuministro.objects.create(nombre="Tintas", descripcion="Tintas de prueba")

    @pytest.fixture
    def suministro(self, categoria):
        return Suministro.objects.create(
            nombre="Tinta Negra BT5001",
            categoria=categoria,
            codigo_interno="TINTA-01",
            unidad_medida="Botellas",
            stock_minimo=2
        )

    @pytest.fixture
    def colaborador(self):
        return ColaboradorFactory()

    def test_registrar_entrada_aumenta_stock(self, suministro, colaborador):
        assert suministro.stock_actual == 0
        
        movimiento = registrar_movimiento_stock(
            suministro_id=suministro.id,
            tipo_movimiento=MovimientoStock.TipoMovimiento.ENTRADA,
            cantidad=10,
            registrado_por_id=colaborador.id,
            costo_unitario=5000,
            numero_factura="FACT-123",
            notas="Compra inicial"
        )
        
        assert movimiento.cantidad == 10
        assert movimiento.costo_unitario == 5000
        
        suministro.refresh_from_db()
        assert suministro.stock_actual == 10

    def test_registrar_salida_disminuye_stock(self, suministro, colaborador):
        # Primero ingresamos 5
        registrar_movimiento_stock(
            suministro_id=suministro.id,
            tipo_movimiento=MovimientoStock.TipoMovimiento.ENTRADA,
            cantidad=5,
            registrado_por_id=colaborador.id
        )
        
        # Luego sacamos 2
        registrar_movimiento_stock(
            suministro_id=suministro.id,
            tipo_movimiento=MovimientoStock.TipoMovimiento.SALIDA,
            cantidad=2,
            registrado_por_id=colaborador.id,
            colaborador_destino_id=colaborador.id,
            notas="Entrega a usuario"
        )
        
        suministro.refresh_from_db()
        assert suministro.stock_actual == 3

    def test_no_se_puede_sacar_mas_del_stock_actual(self, suministro, colaborador):
        # Ingresamos 2
        registrar_movimiento_stock(
            suministro_id=suministro.id,
            tipo_movimiento=MovimientoStock.TipoMovimiento.ENTRADA,
            cantidad=2,
            registrado_por_id=colaborador.id
        )
        
        # Intentamos sacar 3
        with pytest.raises(ValidationError) as exc_info:
            registrar_movimiento_stock(
                suministro_id=suministro.id,
                tipo_movimiento=MovimientoStock.TipoMovimiento.SALIDA,
                cantidad=3,
                registrado_por_id=colaborador.id
            )
            
        assert "No hay suficiente stock" in str(exc_info.value)
        
        suministro.refresh_from_db()
        assert suministro.stock_actual == 2  # El stock no debe haber cambiado
