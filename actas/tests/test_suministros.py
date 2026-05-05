import pytest
from django.core.exceptions import ValidationError
from actas.models import Acta
from actas.services import ActaService
from core.tests.factories import ColaboradorFactory
from suministros.tests.factories import MovimientoStockFactory, SuministroFactory
from suministros.models import MovimientoStock


@pytest.mark.django_db
class TestActaSuministros:
    """Tests para el flujo de actas de entrega de suministros."""

    def test_crear_acta_suministros_con_movimientos(self):
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        movimiento = MovimientoStockFactory(
            tipo_movimiento=MovimientoStock.TipoMovimiento.SALIDA,
            colaborador_destino=colaborador,
        )

        acta = ActaService.crear_acta(
            colaborador=colaborador,
            tipo_acta='ENTREGA_SUMINISTROS',
            movimiento_ids=[movimiento.pk],
            creado_por=creado_por,
        )

        assert acta.tipo_acta == 'ENTREGA_SUMINISTROS'
        assert acta.movimientos_stock.filter(pk=movimiento.pk).exists()
        assert Acta.objects.filter(pk=acta.pk).exists()

    def test_crear_acta_suministros_sin_movimientos_raises_error(self):
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()

        with pytest.raises(ValidationError, match="movimiento"):
            ActaService.crear_acta(
                colaborador=colaborador,
                tipo_acta='ENTREGA_SUMINISTROS',
                movimiento_ids=[],
                creado_por=creado_por,
            )

    def test_movimientos_ya_vinculados_no_aparecen_pendientes(self):
        colaborador = ColaboradorFactory()
        movimiento = MovimientoStockFactory(
            tipo_movimiento=MovimientoStock.TipoMovimiento.SALIDA,
            colaborador_destino=colaborador,
        )
        creado_por = ColaboradorFactory()

        # Crear acta que vincule el movimiento
        ActaService.crear_acta(
            colaborador=colaborador,
            tipo_acta='ENTREGA_SUMINISTROS',
            movimiento_ids=[movimiento.pk],
            creado_por=creado_por,
        )

        # El movimiento ya no debe aparecer como pendiente
        pendientes = ActaService.obtener_movimientos_pendientes(colaborador.pk)
        assert movimiento.pk not in [m.pk for m in pendientes]

    def test_obtener_movimientos_pendientes_solo_salida(self):
        colaborador = ColaboradorFactory()
        salida = MovimientoStockFactory(
            tipo_movimiento=MovimientoStock.TipoMovimiento.SALIDA,
            colaborador_destino=colaborador,
        )
        entrada = MovimientoStockFactory(
            tipo_movimiento=MovimientoStock.TipoMovimiento.ENTRADA,
            colaborador_destino=colaborador,
        )

        pendientes = ActaService.obtener_movimientos_pendientes(colaborador.pk)
        assert salida.pk in [m.pk for m in pendientes]
        assert entrada.pk not in [m.pk for m in pendientes]

    def test_generar_preview_html_suministros(self):
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        movimiento = MovimientoStockFactory(
            tipo_movimiento=MovimientoStock.TipoMovimiento.SALIDA,
            colaborador_destino=colaborador,
        )

        html = ActaService.generar_preview_html_suministros(
            colaborador=colaborador,
            tipo_acta='ENTREGA_SUMINISTROS',
            movimiento_ids=[movimiento.pk],
            creado_por=creado_por,
        )

        assert "Acta de Entrega de Suministros" in html
        assert str(movimiento.cantidad) in html

    def test_generar_preview_html_suministros_sin_movimientos_raises_error(self):
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()

        with pytest.raises(ValidationError, match="movimiento"):
            ActaService.generar_preview_html_suministros(
                colaborador=colaborador,
                tipo_acta='ENTREGA_SUMINISTROS',
                movimiento_ids=[],
                creado_por=creado_por,
            )

    def test_obtener_acta_con_relaciones_incluye_movimientos(self):
        colaborador = ColaboradorFactory()
        creado_por = ColaboradorFactory()
        movimiento = MovimientoStockFactory(
            tipo_movimiento=MovimientoStock.TipoMovimiento.SALIDA,
            colaborador_destino=colaborador,
        )

        acta = ActaService.crear_acta(
            colaborador=colaborador,
            tipo_acta='ENTREGA_SUMINISTROS',
            movimiento_ids=[movimiento.pk],
            creado_por=creado_por,
        )

        acta_recuperada, items = ActaService.obtener_acta_con_relaciones(acta.pk)
        assert acta_recuperada.tipo_acta == 'ENTREGA_SUMINISTROS'
        assert movimiento.pk in [m.pk for m in items]
