from django.urls import path
from . import views

app_name = 'inspecciones'

urlpatterns = [
    path('', views.lista_inspecciones, name='lista'),
    path('escanear/', views.escanear_qr, name='escanear'),
    path('buscar/', views.buscar_vivienda, name='buscar'),
    path('nueva/', views.nueva_inspeccion, name='nueva'),
    path('nueva/<int:vivienda_id>/', views.nueva_inspeccion, name='nueva_vivienda'),
    path('<int:pk>/', views.detalle_inspeccion, name='detalle'),
]
