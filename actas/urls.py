from django.urls import path
from . import views

app_name = 'actas'

urlpatterns = [
    path('', views.acta_list, name='acta_list'),
    path('preview/', views.acta_preview, name='acta_preview'),
    path('preview/pdf/', views.acta_preview_pdf, name='acta_preview_pdf'),
    path('crear/', views.acta_create, name='acta_create'),
    path('<int:pk>/', views.acta_detail, name='acta_detail'),
    path('<int:pk>/pdf/', views.acta_pdf, name='acta_pdf'),
    path('<int:pk>/firmar/', views.acta_firmar, name='acta_firmar'),
    path('<int:pk>/anular/', views.acta_anular, name='acta_anular'),
    path('asignaciones-pendientes/<int:colaborador_pk>/', views.asignaciones_pendientes, name='acta_asignaciones_pendientes'),
    path('ministros-por-colaborador/<int:colaborador_pk>/', views.ministros_por_colaborador, name='acta_ministros_por_colaborador'),
]
