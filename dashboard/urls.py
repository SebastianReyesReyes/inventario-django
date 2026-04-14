from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_principal, name='principal'),
    path('exportar/', views.exportar_dispositivos_excel, name='exportar_excel'),
    path('reportes/', views.reportes_lista, name='reportes'),
]
