from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Suministro, MovimientoStock, CategoriaSuministro
from core.models import Fabricante, CentroCosto
from colaboradores.models import Colaborador
from dispositivos.models import Dispositivo


class SuministroResource(resources.ModelResource):
    categoria = fields.Field(
        column_name='Categoría',
        attribute='categoria',
        widget=ForeignKeyWidget(CategoriaSuministro, 'nombre')
    )
    fabricante = fields.Field(
        column_name='Fabricante',
        attribute='fabricante',
        widget=ForeignKeyWidget(Fabricante, 'nombre')
    )
    stock_critico = fields.Field(
        column_name='Stock Crítico',
        attribute='stock_critico',
    )
    modelos_compatibles = fields.Field(
        column_name='Modelos Compatibles',
        attribute='modelos_compatibles',
    )

    class Meta:
        model = Suministro
        fields = (
            'nombre', 'categoria', 'fabricante', 'codigo_interno',
            'stock_actual', 'stock_minimo', 'unidad_medida',
            'es_alternativo', 'esta_activo', 'stock_critico',
            'modelos_compatibles',
        )
        export_order = fields

    def dehydrate_stock_critico(self, obj):
        return 'Sí' if obj.stock_critico else 'No'

    def dehydrate_modelos_compatibles(self, obj):
        return ', '.join(m.nombre for m in obj.modelos_compatibles.all()) or '—'

    def dehydrate_es_alternativo(self, obj):
        return 'Sí' if obj.es_alternativo else 'No'

    def dehydrate_esta_activo(self, obj):
        return 'Sí' if obj.esta_activo else 'No'


class MovimientoStockResource(resources.ModelResource):
    suministro = fields.Field(
        column_name='Suministro',
        attribute='suministro',
        widget=ForeignKeyWidget(Suministro, 'nombre')
    )
    tipo_movimiento = fields.Field(
        column_name='Tipo de Movimiento',
        attribute='tipo_movimiento',
    )
    colaborador_destino = fields.Field(
        column_name='Colaborador Destino',
        attribute='colaborador_destino',
        widget=ForeignKeyWidget(Colaborador, 'nombre_completo')
    )
    centro_costo = fields.Field(
        column_name='Centro de Costo',
        attribute='centro_costo',
        widget=ForeignKeyWidget(CentroCosto, 'codigo_contable')
    )
    dispositivo_destino = fields.Field(
        column_name='Dispositivo Destino',
        attribute='dispositivo_destino',
        widget=ForeignKeyWidget(Dispositivo, '__str__')
    )
    registrado_por = fields.Field(
        column_name='Registrado Por',
        attribute='registrado_por',
        widget=ForeignKeyWidget(Colaborador, 'nombre_completo')
    )
    total = fields.Field(
        column_name='Valor Total',
        attribute='total',
    )

    class Meta:
        model = MovimientoStock
        fields = (
            'fecha', 'tipo_movimiento', 'suministro', 'cantidad',
            'costo_unitario', 'total', 'numero_factura',
            'colaborador_destino', 'centro_costo', 'dispositivo_destino',
            'registrado_por', 'notas',
        )
        export_order = fields

    def dehydrate_tipo_movimiento(self, obj):
        return obj.get_tipo_movimiento_display()

    def dehydrate_total(self, obj):
        if obj.costo_unitario and obj.cantidad:
            return obj.costo_unitario * obj.cantidad
        return '—'

    def dehydrate_costo_unitario(self, obj):
        if obj.costo_unitario:
            return obj.costo_unitario
        return '—'
