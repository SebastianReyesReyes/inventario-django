from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Fabricantes & Modelos
    path('fabricantes/', views.fabricante_list, name='fabricante_list'),
    path('fabricantes/crear/', views.fabricante_create, name='fabricante_create'),
    path('fabricantes/<int:pk>/editar/', views.fabricante_edit, name='fabricante_update'),
    path('fabricantes/<int:pk>/eliminar/', views.fabricante_delete, name='fabricante_delete'),
    path('fabricantes/<int:pk>/modelos/inline/', views.ajax_modelo_create_inline, name='fabricante_modelo_inline'),
    
    path('modelos/', views.modelo_list, name='modelo_list'),
    path('modelos/crear/', views.modelo_create, name='modelo_create'),
    path('modelos/<int:pk>/editar/', views.modelo_edit, name='modelo_update'),
    path('modelos/<int:pk>/eliminar/', views.modelo_delete, name='modelo_delete'),

    # Tipos
    path('tipos/', views.tipo_list, name='tipodispositivo_list'),
    path('tipos/crear/', views.tipo_create, name='tipodispositivo_create'),
    path('tipos/<int:pk>/editar/', views.tipo_edit, name='tipodispositivo_update'),
    path('tipos/<int:pk>/eliminar/', views.tipo_delete, name='tipodispositivo_delete'),

    # Centros de Costo
    path('cc/', views.cc_list, name='centrocosto_list'),
    path('cc/crear/', views.cc_create, name='centrocosto_create'),
    path('cc/<int:pk>/editar/', views.cc_edit, name='centrocosto_update'),
    path('cc/<int:pk>/toggle/', views.cc_toggle_activa, name='centrocosto_toggle_activa'),

    # Estados
    path('estados/', views.estado_list, name='estadodispositivo_list'),
    path('estados/crear/', views.estado_create, name='estadodispositivo_create'),
    path('estados/<int:pk>/editar/', views.estado_edit, name='estadodispositivo_update'),
    path('estados/<int:pk>/eliminar/', views.estado_delete, name='estadodispositivo_delete'),
    
    # Dashboard API / Drill-down
    path('dashboard/drill-down/', views.dashboard_drill_down, name='dashboard_drill_down'),
]
