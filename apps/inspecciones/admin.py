from django.contrib import admin
from .models import Inspeccion, InspeccionHistorico

@admin.register(Inspeccion)
class InspeccionAdmin(admin.ModelAdmin):
    list_display = ('vivienda', 'usuario', 'nivel_riesgo', 'presencia_larvas', 'fecha_inspeccion', 'estado')
    list_filter = ('nivel_riesgo', 'estado', 'presencia_larvas')
    search_fields = ('vivienda__codigo_qr', 'vivienda__direccion')
    readonly_fields = ('nivel_riesgo', 'fecha_inspeccion')

@admin.register(InspeccionHistorico)
class InspeccionHistoricoAdmin(admin.ModelAdmin):
    list_display = ('vivienda_codigo', 'nivel_riesgo', 'tipo_operacion', 'fecha_cambio', 'usuario_cambio')
    list_filter = ('tipo_operacion', 'nivel_riesgo')
