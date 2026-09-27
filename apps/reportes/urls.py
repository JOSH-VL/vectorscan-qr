from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.panel_reportes, name='panel'),
    path('inspecciones/', views.reporte_inspecciones, name='inspecciones'),
    path('riesgo/', views.reporte_riesgo, name='riesgo'),
    path('productividad/', views.reporte_productividad, name='productividad'),
    path('exportar/excel/', views.exportar_excel, name='exportar_excel'),
    path('exportar/csv/', views.exportar_csv, name='exportar_csv'),
]
