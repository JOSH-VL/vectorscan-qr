from django.urls import path
from . import views
app_name = 'usuarios'
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.lista_usuarios, name='lista'),
    path('crear/', views.crear_usuario, name='crear'),
    path('editar/<int:pk>/', views.editar_usuario, name='editar'),
    path('desactivar/<int:pk>/', views.desactivar_usuario, name='desactivar'),
]
