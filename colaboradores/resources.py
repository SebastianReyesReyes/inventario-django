from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Colaborador
from core.models import Departamento, CentroCosto


class ColaboradorResource(resources.ModelResource):
    departamento = fields.Field(
        column_name="Departamento",
        attribute="departamento",
        widget=ForeignKeyWidget(Departamento, "nombre"),
    )
    centro_costo = fields.Field(
        column_name="Centro de Costo",
        attribute="centro_costo",
        widget=ForeignKeyWidget(CentroCosto, "codigo_contable"),
    )
    nombre_completo = fields.Field(
        column_name="Nombre Completo",
        attribute="nombre_completo",
        readonly=True,
    )
    activo = fields.Field(
        column_name="Activo",
        attribute="esta_activo",
    )

    class Meta:
        model = Colaborador
        fields = (
            "nombre_completo",
            "rut",
            "cargo",
            "departamento",
            "centro_costo",
            "email",
            "username",
            "activo",
        )
        export_order = fields
