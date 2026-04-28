from django.contrib import admin
from .models import (
    Dispositivo, Notebook, Smartphone, Monitor, 
    BitacoraMantenimiento, HistorialAsignacion, EntregaAccesorio
)

@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ('identificador_interno', 'numero_serie', 'get_tipo', 'estado', 'propietario_actual')
    list_filter = ('modelo__tipo_dispositivo', 'estado', 'centro_costo')
    search_fields = ('identificador_interno', 'numero_serie', 'propietario_actual__first_name', 'propietario_actual__last_name')

    def get_tipo(self, obj):
        return obj.modelo.tipo_dispositivo.nombre if obj.modelo and obj.modelo.tipo_dispositivo else "-"
    get_tipo.short_description = "Tipo"
    get_tipo.admin_order_field = 'modelo__tipo_dispositivo'

@admin.register(HistorialAsignacion)
class HistorialAsignacionAdmin(admin.ModelAdmin):
    list_display = ('dispositivo', 'colaborador', 'fecha_inicio', 'fecha_fin')
    list_filter = ('fecha_inicio', 'fecha_fin')
    search_fields = ('dispositivo__identificador_interno', 'colaborador__first_name', 'colaborador__last_name')

@admin.register(EntregaAccesorio)
class EntregaAccesorioAdmin(admin.ModelAdmin):
    list_display = ('colaborador', 'tipo', 'cantidad', 'fecha')
    search_fields = ('colaborador__first_name', 'colaborador__last_name', 'tipo')

admin.site.register(Notebook)
admin.site.register(Smartphone)
admin.site.register(Monitor)
admin.site.register(BitacoraMantenimiento)
