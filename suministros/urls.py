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
]