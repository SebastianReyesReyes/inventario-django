from django.urls import path
from . import views

app_name = 'dispositivos'

urlpatterns = [
    path('crear/', views.dispositivo_create, name='dispositivo_create'),
    path('ajax/get-modelos/', views.ajax_get_modelos, name='ajax_get_modelos'),
    path('ajax/crear-modelo/', views.ajax_crear_modelo, name='ajax_crear_modelo'),
    path('ajax/get-tipo-fields/', views.ajax_get_tech_fields, name='ajax_get_tipo_fields'),
    path('listado/', views.dispositivo_list, name='dispositivo_list'),
    path('detalle/<int:pk>/', views.dispositivo_detail, name='dispositivo_detail'),
    path('detalle/<int:pk>/qr/', views.dispositivo_qr, name='dispositivo_qr'),
    path('detalle/<int:pk>/mantenimiento/', views.mantenimiento_create, name='mantenimiento_create'),
    path('mantenimiento/<int:pk>/editar/', views.mantenimiento_update, name='mantenimiento_update'),
    path('editar/<int:pk>/', views.dispositivo_update, name='dispositivo_update'),
    path('eliminar/<int:pk>/', views.dispositivo_delete, name='dispositivo_delete'),
    
    # Épica 4: Trazabilidad y Asignaciones
    path('detalle/<int:pk>/asignar/', views.dispositivo_asignar, name='dispositivo_asignar'),
    path('detalle/<int:pk>/reasignar/', views.dispositivo_reasignar, name='dispositivo_reasignar'),
    path('detalle/<int:pk>/devolver/', views.dispositivo_devolver, name='dispositivo_devolver'),
    path('detalle/<int:pk>/historial/', views.dispositivo_historial, name='dispositivo_historial'),
    
    # Accesorios
    path('colaborador/<int:pk>/accesorio/entregar/', views.colaborador_entrega_accesorio, name='colaborador_entrega_accesorio'),
    path('colaborador/<int:pk>/accesorios/historial/', views.colaborador_historial_accesorios, name='colaborador_historial_accesorios'),
]
