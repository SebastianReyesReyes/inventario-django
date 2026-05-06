from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_principal, name='principal'),
    path('tab-hardware/', views.tab_hardware, name='tab_hardware'),
    path('tab-suministros/', views.tab_suministros, name='tab_suministros'),
    path('tab-estrategico/', views.tab_estrategico, name='tab_estrategico'),
    path('exportar/', views.exportar_dispositivos_excel, name='exportar_excel'),
    path('reportes/', views.reportes_lista, name='reportes'),
]
