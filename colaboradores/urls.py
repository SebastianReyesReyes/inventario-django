from django.urls import path
from . import views

app_name = 'colaboradores'

urlpatterns = [
    path('', views.colaborador_list, name='colaborador_list'),
    path('crear/', views.colaborador_create, name='colaborador_create'),
    path('editar/<int:pk>/', views.colaborador_update, name='colaborador_update'),
    path('detalle/<int:pk>/', views.colaborador_detail, name='colaborador_detail'),
    path('eliminar/<int:pk>/', views.colaborador_delete, name='colaborador_delete'),
    path('exportar/', views.colaborador_exportar_excel, name='colaborador_exportar_excel'),
]
