from django.urls import path
from . import views

app_name = 'viviendas'

urlpatterns = [
    path('', views.lista_viviendas, name='lista'),
    path('crear/', views.crear_vivienda, name='crear'),
    path('<int:pk>/', views.detalle_vivienda, name='detalle'),
    path('<int:pk>/editar/', views.editar_vivienda, name='editar'),
    path('<int:pk>/desactivar/', views.desactivar_vivienda, name='desactivar'),
    path('<int:pk>/qr/descargar/', views.descargar_qr, name='descargar_qr'),
    path('<int:pk>/qr/imprimir/', views.imprimir_qr, name='imprimir_qr'),
]
