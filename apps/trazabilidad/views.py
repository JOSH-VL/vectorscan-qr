"""
Vistas del módulo de Trazabilidad — VectorScan QR
Sprint 4: Historial longitudinal, auditoría y evolución de riesgo
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from apps.viviendas.models import Vivienda, ViviendaHistorico
from apps.inspecciones.models import Inspeccion, InspeccionHistorico
from apps.usuarios.models import UsuarioHistorico


@login_required
def panel_trazabilidad(request):
    """Panel general de trazabilidad con métricas del sistema."""
    hoy = timezone.now()
    hace_30_dias = hoy - timedelta(days=30)

    # Métricas generales
    total_viviendas = Vivienda.objects.filter(estado='Activo').count()
    total_inspecciones = Inspeccion.objects.filter(estado='Activo').count()
    inspecciones_mes = Inspeccion.objects.filter(
        estado='Activo', fecha_inspeccion__gte=hace_30_dias
    ).count()

    # Viviendas sin inspección reciente (más de 30 días)
    viviendas_con_inspeccion_reciente = Inspeccion.objects.filter(
        estado='Activo', fecha_inspeccion__gte=hace_30_dias
    ).values_list('vivienda_id', flat=True).distinct()

    viviendas_pendientes = Vivienda.objects.filter(
        estado='Activo'
    ).exclude(id__in=viviendas_con_inspeccion_reciente).count()

    # Viviendas recurrentemente de alto riesgo
    viviendas_criticas = Vivienda.objects.filter(
        estado='Activo',
        inspecciones__nivel_riesgo='Alto',
        inspecciones__estado='Activo'
    ).annotate(
        veces_alto=Count('inspecciones')
    ).filter(veces_alto__gte=2).order_by('-veces_alto')[:10]

    # Actividad reciente combinada
    cambios_viviendas = ViviendaHistorico.objects.select_related(
        'usuario_cambio', 'vivienda_original'
    )[:15]

    return render(request, 'trazabilidad/panel.html', {
        'total_viviendas': total_viviendas,
        'total_inspecciones': total_inspecciones,
        'inspecciones_mes': inspecciones_mes,
        'viviendas_pendientes': viviendas_pendientes,
        'viviendas_criticas': viviendas_criticas,
        'cambios_viviendas': cambios_viviendas,
    })


@login_required
def historial_vivienda(request, pk):
    """Historial longitudinal completo de una vivienda."""
    vivienda = get_object_or_404(Vivienda, pk=pk)

    # Todas las inspecciones ordenadas cronológicamente
    inspecciones = Inspeccion.objects.filter(
        vivienda=vivienda, estado='Activo'
    ).select_related('usuario').order_by('-fecha_inspeccion')

    # Cambios registrados en la vivienda
    cambios = vivienda.historial.select_related('usuario_cambio').all()

    # Estadísticas de la vivienda
    stats = {
        'total': inspecciones.count(),
        'alto': inspecciones.filter(nivel_riesgo='Alto').count(),
        'medio': inspecciones.filter(nivel_riesgo='Medio').count(),
        'bajo': inspecciones.filter(nivel_riesgo='Bajo').count(),
    }

    # Datos para línea de tiempo (últimas 12 inspecciones)
    timeline = list(inspecciones[:12])
    timeline.reverse()

    # Evaluar tendencia
    tendencia = 'estable'
    if len(timeline) >= 2:
        valores = {'Bajo': 1, 'Medio': 2, 'Alto': 3}
        primera_mitad = timeline[:len(timeline)//2]
        segunda_mitad = timeline[len(timeline)//2:]
        prom_inicial = sum(valores.get(i.nivel_riesgo, 0) for i in primera_mitad) / len(primera_mitad)
        prom_final = sum(valores.get(i.nivel_riesgo, 0) for i in segunda_mitad) / len(segunda_mitad)
        if prom_final > prom_inicial + 0.3:
            tendencia = 'empeorando'
        elif prom_final < prom_inicial - 0.3:
            tendencia = 'mejorando'

    return render(request, 'trazabilidad/historial_vivienda.html', {
        'vivienda': vivienda,
        'inspecciones': inspecciones,
        'cambios': cambios,
        'stats': stats,
        'timeline': timeline,
        'tendencia': tendencia,
    })


@login_required
def auditoria(request):
    """Registro de auditoría completo del sistema."""
    modulo = request.GET.get('modulo', 'todos')
    busqueda = request.GET.get('q', '')

    registros = []

    if modulo in ('todos', 'viviendas'):
        for h in ViviendaHistorico.objects.select_related('usuario_cambio')[:200]:
            registros.append({
                'fecha': h.fecha_cambio,
                'modulo': 'Viviendas',
                'icono': 'house-heart',
                'objeto': h.codigo_qr,
                'detalle': h.direccion,
                'operacion': h.get_tipo_operacion_display(),
                'tipo_op': h.tipo_operacion,
                'usuario': h.usuario_cambio,
            })

    if modulo in ('todos', 'inspecciones'):
        for h in InspeccionHistorico.objects.select_related('usuario_cambio')[:200]:
            registros.append({
                'fecha': h.fecha_cambio,
                'modulo': 'Inspecciones',
                'icono': 'clipboard2-pulse',
                'objeto': h.vivienda_codigo,
                'detalle': f'Riesgo {h.nivel_riesgo}',
                'operacion': h.get_tipo_operacion_display(),
                'tipo_op': h.tipo_operacion,
                'usuario': h.usuario_cambio,
            })

    if modulo in ('todos', 'usuarios'):
        for h in UsuarioHistorico.objects.select_related('usuario_cambio')[:200]:
            registros.append({
                'fecha': h.fecha_cambio,
                'modulo': 'Usuarios',
                'icono': 'person-badge',
                'objeto': h.username,
                'detalle': h.nombre_completo or h.rol_nombre,
                'operacion': h.get_tipo_operacion_display(),
                'tipo_op': h.tipo_operacion,
                'usuario': h.usuario_cambio,
            })

    # Filtrar por búsqueda
    if busqueda:
        registros = [
            r for r in registros
            if busqueda.lower() in str(r['objeto']).lower()
            or busqueda.lower() in str(r['detalle']).lower()
        ]

    # Ordenar por fecha descendente
    registros.sort(key=lambda x: x['fecha'], reverse=True)

    return render(request, 'trazabilidad/auditoria.html', {
        'registros': registros[:150],
        'modulo': modulo,
        'busqueda': busqueda,
        'total': len(registros),
    })


@login_required
def viviendas_seguimiento(request):
    """Viviendas que requieren seguimiento prioritario."""
    hoy = timezone.now()
    hace_30_dias = hoy - timedelta(days=30)
    hace_7_dias = hoy - timedelta(days=7)

    # Viviendas con riesgo alto en su última inspección
    viviendas_riesgo_alto = []
    for v in Vivienda.objects.filter(estado='Activo').prefetch_related('inspecciones'):
        ultima = v.inspecciones.filter(estado='Activo').first()
        if ultima and ultima.nivel_riesgo == 'Alto':
            dias_transcurridos = (hoy - ultima.fecha_inspeccion).days
            viviendas_riesgo_alto.append({
                'vivienda': v,
                'ultima_inspeccion': ultima,
                'dias': dias_transcurridos,
                'urgente': dias_transcurridos >= 7,
            })

    # Ordenar: más urgentes primero
    viviendas_riesgo_alto.sort(key=lambda x: x['dias'], reverse=True)

    # Viviendas sin inspección en 30+ días
    con_inspeccion_reciente = Inspeccion.objects.filter(
        estado='Activo', fecha_inspeccion__gte=hace_30_dias
    ).values_list('vivienda_id', flat=True).distinct()

    sin_inspeccion = Vivienda.objects.filter(
        estado='Activo'
    ).exclude(id__in=con_inspeccion_reciente)[:50]

    return render(request, 'trazabilidad/seguimiento.html', {
        'viviendas_riesgo_alto': viviendas_riesgo_alto[:30],
        'sin_inspeccion': sin_inspeccion,
    })
