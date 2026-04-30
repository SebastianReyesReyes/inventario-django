from django.contrib import admin
from .models import CategoriaSuministro, Suministro, MovimientoStock

@admin.register(CategoriaSuministro)
class CategoriaSuministroAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

@admin.register(Suministro)
class SuministroAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'fabricante', 'es_alternativo', 'stock_actual', 'stock_minimo')
    list_filter = ('categoria', 'es_alternativo', 'fabricante')
    search_fields = ('nombre', 'codigo_interno', 'fabricante__nombre')
    filter_horizontal = ('modelos_compatibles',)
    readonly_fields = ('stock_actual',)
    
@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ('suministro', 'tipo_movimiento', 'cantidad', 'fecha', 'registrado_por')
    list_filter = ('tipo_movimiento', 'fecha')
    search_fields = ('suministro__nombre', 'numero_factura', 'notas')
    raw_id_fields = ('suministro', 'colaborador_destino', 'centro_costo', 'registrado_por')
