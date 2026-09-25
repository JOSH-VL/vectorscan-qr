from django.contrib import admin
from .models import Vivienda, ViviendaHistorico


@admin.register(Vivienda)
class ViviendaAdmin(admin.ModelAdmin):
    list_display = ('codigo_qr', 'direccion', 'responsable_familia', 'zona', 'estado', 'fecha_registro')
    list_filter = ('estado', 'zona')
    search_fields = ('codigo_qr', 'direccion', 'responsable_familia')
    readonly_fields = ('codigo_qr', 'imagen_qr', 'fecha_registro')


@admin.register(ViviendaHistorico)
class ViviendaHistoricoAdmin(admin.ModelAdmin):
    list_display = ('codigo_qr', 'direccion', 'tipo_operacion', 'fecha_cambio', 'usuario_cambio')
    list_filter = ('tipo_operacion',)
    readonly_fields = ('vivienda_original', 'codigo_qr', 'direccion', 'responsable_familia', 'num_habitantes', 'zona', 'estado', 'fecha_cambio', 'usuario_cambio', 'tipo_operacion')
