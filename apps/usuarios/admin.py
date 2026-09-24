from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Rol, Usuario, UsuarioHistorico

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'nombre_completo', 'rol', 'estado', 'fecha_creacion')
    list_filter = ('rol', 'estado')
    search_fields = ('username', 'nombre_completo')
    fieldsets = UserAdmin.fieldsets + (('VectorScan QR', {'fields': ('rol', 'nombre_completo', 'estado')}),)

@admin.register(UsuarioHistorico)
class UsuarioHistoricoAdmin(admin.ModelAdmin):
    list_display = ('username', 'tipo_operacion', 'fecha_cambio', 'usuario_cambio')
    list_filter = ('tipo_operacion',)
