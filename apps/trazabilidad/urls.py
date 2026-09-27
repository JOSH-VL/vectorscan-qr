from django.urls import path
from . import views

app_name = 'trazabilidad'

urlpatterns = [
    path('', views.panel_trazabilidad, name='panel'),
    path('vivienda/<int:pk>/', views.historial_vivienda, name='historial_vivienda'),
    path('auditoria/', views.auditoria, name='auditoria'),
    path('seguimiento/', views.viviendas_seguimiento, name='seguimiento'),
]
