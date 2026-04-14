from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Fabricantes & Modelos
    path('fabricantes/', views.fabricante_list, name='fabricante_list'),
    path('fabricantes/crear/', views.fabricante_create, name='fabricante_create'),
    path('fabricantes/<int:pk>/editar/', views.fabricante_edit, name='fabricante_edit'),
    path('fabricantes/<int:pk>/eliminar/', views.fabricante_delete, name='fabricante_delete'),
    
    path('modelos/', views.modelo_list, name='modelo_list'),
    path('modelos/crear/', views.modelo_create, name='modelo_create'),
    path('modelos/<int:pk>/editar/', views.modelo_edit, name='modelo_edit'),
    path('modelos/<int:pk>/eliminar/', views.modelo_delete, name='modelo_delete'),

    # Tipos
    path('tipos/', views.tipo_list, name='tipo_list'),
    path('tipos/crear/', views.tipo_create, name='tipo_create'),
    path('tipos/<int:pk>/editar/', views.tipo_edit, name='tipo_edit'),
    path('tipos/<int:pk>/eliminar/', views.tipo_delete, name='tipo_delete'),

    # Centros de Costo
    path('cc/', views.cc_list, name='cc_list'),
    path('cc/crear/', views.cc_create, name='cc_create'),
    path('cc/<int:pk>/editar/', views.cc_edit, name='cc_edit'),
    path('cc/<int:pk>/toggle/', views.cc_toggle_activa, name='cc_toggle_activa'),

    # Estados
    path('estados/', views.estado_list, name='estado_list'),
    path('estados/crear/', views.estado_create, name='estado_create'),
    path('estados/<int:pk>/editar/', views.estado_edit, name='estado_edit'),
    path('estados/<int:pk>/eliminar/', views.estado_delete, name='estado_delete'),
    
    # Dashboard API / Drill-down
    path('dashboard/drill-down/', views.dashboard_drill_down, name='dashboard_drill_down'),
]
