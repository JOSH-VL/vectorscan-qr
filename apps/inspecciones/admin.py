from django.contrib import admin
from .models import (Inspeccion, InspeccionHistorico, DepositoInspeccion,
                     EncuestaEntomologica, ConsolidadoMensual)


@admin.register(EncuestaEntomologica)
class EncuestaEntomologicaAdmin(admin.ModelAdmin):
    list_display = ('localidad', 'fecha', 'clase_trabajo', 'casas_inspeccionadas',
                    'casas_positivas', 'recipientes_inspeccionados', 'recipientes_positivos', 'estado')
    list_filter = ('localidad', 'clase_trabajo', 'estado')
    readonly_fields = ('importado_por', 'fecha_importacion')


@admin.register(ConsolidadoMensual)
class ConsolidadoMensualAdmin(admin.ModelAdmin):
    list_display = ('localidad', 'anio', 'mes', 'clase_trabajo', 'viviendas_inspeccionadas',
                    'viviendas_positivas', 'depositos_inspeccionados', 'depositos_positivos', 'estado')
    list_filter = ('anio', 'mes', 'localidad', 'clase_trabajo', 'estado')
    readonly_fields = ('importado_por', 'fecha_importacion')


class DepositoInspeccionInline(admin.TabularInline):
    model = DepositoInspeccion
    extra = 0


@admin.register(Inspeccion)
class InspeccionAdmin(admin.ModelAdmin):
    inlines = [DepositoInspeccionInline]
    list_display = ('vivienda', 'usuario', 'nivel_riesgo', 'presencia_larvas', 'fecha_inspeccion', 'estado')
    list_filter = ('nivel_riesgo', 'estado', 'presencia_larvas')
    search_fields = ('vivienda__codigo_qr', 'vivienda__direccion')
    readonly_fields = ('nivel_riesgo', 'fecha_inspeccion')

@admin.register(InspeccionHistorico)
class InspeccionHistoricoAdmin(admin.ModelAdmin):
    list_display = ('vivienda_codigo', 'nivel_riesgo', 'tipo_operacion', 'fecha_cambio', 'usuario_cambio')
    list_filter = ('tipo_operacion', 'nivel_riesgo')
