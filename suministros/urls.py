from django.urls import path
from . import views

app_name = 'suministros'

urlpatterns = [
    path('', views.suministro_list, name='suministro_list'),
    path('crear/', views.suministro_create, name='suministro_create'),
    path('editar/<int:pk>/', views.suministro_update, name='suministro_update'),
    path('detalle/<int:pk>/', views.suministro_detail, name='suministro_detail'),
    path('eliminar/<int:pk>/', views.suministro_delete, name='suministro_delete'),
    path('movimiento/nuevo/', views.movimiento_create, name='movimiento_create'),
    path('ajax/modelos-compatibles/', views.ajax_get_modelos_compatibles, name='ajax_get_modelos_compatibles'),
    path('ajax/dispositivos-compatibles/', views.ajax_get_dispositivos_compatibles, name='ajax_get_dispositivos_compatibles'),
    path('ajax/colaborador-centro-costo/', views.ajax_colaborador_centro_costo, name='ajax_colaborador_centro_costo'),
    # Categoría de Suministro (HTMX inline)
    path('categorias/crear/', views.categoriasuministro_create, name='categoriasuministro_create'),
    path('categorias/<int:pk>/editar/', views.categoriasuministro_update, name='categoriasuministro_update'),
    path('ajax/categoria-options/', views.ajax_categoria_options, name='ajax_categoria_options'),
    # Factura como Reina
    path('ingreso-factura/', views.factura_create, name='factura_create'),
    path('ajax/suministro-options/', views.ajax_suministro_options, name='ajax_suministro_options'),
    # Exportaciones Excel
    path('exportar/', views.suministro_export_excel, name='suministro_export_excel'),
    path('<int:pk>/exportar-movimientos/', views.suministro_movimientos_export_excel, name='suministro_movimientos_export_excel'),
]