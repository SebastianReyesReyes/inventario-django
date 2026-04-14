from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Dispositivo
from core.models import TipoDispositivo, EstadoDispositivo, CentroCosto, Modelo
from colaboradores.models import Colaborador

class DispositivoResource(resources.ModelResource):
    tipo = fields.Field(
        column_name='Tipo',
        attribute='tipo',
        widget=ForeignKeyWidget(TipoDispositivo, 'nombre')
    )
    estado = fields.Field(
        column_name='Estado',
        attribute='estado',
        widget=ForeignKeyWidget(EstadoDispositivo, 'nombre')
    )
    modelo = fields.Field(
        column_name='Modelo',
        attribute='modelo',
        widget=ForeignKeyWidget(Modelo, 'nombre')
    )
    fabricante = fields.Field(
        column_name='Fabricante',
        attribute='modelo__fabricante__nombre'
    )
    centro_costo = fields.Field(
        column_name='Centro de Costo',
        attribute='centro_costo',
        widget=ForeignKeyWidget(CentroCosto, 'codigo_contable')
    )
    propietario = fields.Field(
        column_name='Propietario Actual',
        attribute='propietario_actual',
        widget=ForeignKeyWidget(Colaborador, 'nombre_completo')
    )

    class Meta:
        model = Dispositivo
        fields = (
            'identificador_interno', 'numero_serie', 'fabricante', 'modelo', 
            'tipo', 'estado', 'centro_costo', 'propietario', 
            'fecha_compra', 'valor_contable'
        )
        export_order = fields
