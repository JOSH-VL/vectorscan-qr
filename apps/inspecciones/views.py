"""
Vistas del módulo de Inspecciones — VectorScan QR
Sprint 3: Registro de inspecciones, escaneo QR, historial
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from apps.viviendas.models import Vivienda
from .models import Inspeccion, InspeccionHistorico


def _registrar_historial(inspeccion, usuario, tipo_operacion):
    """Helper para registrar en tabla histórica."""
    InspeccionHistorico.objects.create(
        inspeccion_original=inspeccion,
        vivienda_codigo=inspeccion.vivienda.codigo_qr,
        presencia_larvas=inspeccion.presencia_larvas,
        criaderos_potenciales=inspeccion.criaderos_potenciales,
        nivel_riesgo=inspeccion.nivel_riesgo,
        estado=inspeccion.estado,
        usuario_cambio=usuario,
        tipo_operacion=tipo_operacion,
    )


@login_required
def lista_inspecciones(request):
    """Lista de inspecciones con filtros."""
    busqueda = request.GET.get('q', '')
    riesgo_filtro = request.GET.get('riesgo', '')

    inspecciones = Inspeccion.objects.filter(
        estado='Activo'
    ).select_related('vivienda', 'usuario')

    if busqueda:
        inspecciones = inspecciones.filter(
            Q(vivienda__codigo_qr__icontains=busqueda) |
            Q(vivienda__direccion__icontains=busqueda) |
            Q(vivienda__responsable_familia__icontains=busqueda)
        )

    if riesgo_filtro:
        inspecciones = inspecciones.filter(nivel_riesgo=riesgo_filtro)

    # Estadísticas rápidas
    stats = Inspeccion.objects.filter(estado='Activo').aggregate(
        total=Count('id'),
        alto=Count('id', filter=Q(nivel_riesgo='Alto')),
        medio=Count('id', filter=Q(nivel_riesgo='Medio')),
        bajo=Count('id', filter=Q(nivel_riesgo='Bajo')),
    )

    return render(request, 'inspecciones/lista.html', {
        'inspecciones': inspecciones[:100],
        'busqueda': busqueda,
        'riesgo_filtro': riesgo_filtro,
        'stats': stats,
    })


@login_required
def escanear_qr(request):
    """Pantalla para escanear QR con la cámara del celular."""
    return render(request, 'inspecciones/escanear_qr.html')


@login_required
def nueva_inspeccion(request, vivienda_id=None):
    """Crear nueva inspección para una vivienda."""
    # Si viene por QR code
    qr_code = request.GET.get('qr', '')
    vivienda = None

    if vivienda_id:
        vivienda = get_object_or_404(Vivienda, pk=vivienda_id, estado='Activo')
    elif qr_code:
        vivienda = Vivienda.objects.filter(codigo_qr=qr_code, estado='Activo').first()
        if not vivienda:
            messages.error(request, f'No se encontró vivienda con código QR: {qr_code}')
            return redirect('inspecciones:escanear')

    if not vivienda:
        messages.error(request, 'Debe seleccionar una vivienda para inspeccionar.')
        return redirect('inspecciones:escanear')

    # Últimas inspecciones de esta vivienda
    historial_vivienda = Inspeccion.objects.filter(
        vivienda=vivienda, estado='Activo'
    )[:5]

    if request.method == 'POST':
        presencia_larvas = request.POST.get('presencia_larvas') == 'si'
        criaderos = request.POST.get('criaderos_potenciales') == 'si'

        inspeccion = Inspeccion.objects.create(
            vivienda=vivienda,
            usuario=request.user,
            num_depositos=int(request.POST.get('num_depositos', 0) or 0),
            depositos_positivos=int(request.POST.get('depositos_positivos', 0) or 0),
            presencia_larvas=presencia_larvas,
            criaderos_potenciales=criaderos,
            aplico_larvicida='aplico_larvicida' in request.POST,
            elimino_criaderos='elimino_criaderos' in request.POST,
            programo_fumigacion='programo_fumigacion' in request.POST,
            educo_residente='educo_residente' in request.POST,
            observaciones=request.POST.get('observaciones', '').strip(),
        )

        _registrar_historial(inspeccion, request.user, 'INSERT')

        messages.success(
            request,
            f'Inspección registrada. Vivienda {vivienda.codigo_qr} clasificada como Riesgo {inspeccion.nivel_riesgo}.'
        )
        return redirect('inspecciones:detalle', pk=inspeccion.pk)

    return render(request, 'inspecciones/nueva.html', {
        'vivienda': vivienda,
        'historial_vivienda': historial_vivienda,
    })


@login_required
def detalle_inspeccion(request, pk):
    """Detalle de una inspección."""
    inspeccion = get_object_or_404(
        Inspeccion.objects.select_related('vivienda', 'usuario'),
        pk=pk
    )
    return render(request, 'inspecciones/detalle.html', {
        'inspeccion': inspeccion,
    })


@login_required
def buscar_vivienda(request):
    """Buscar vivienda manualmente (sin QR)."""
    busqueda = request.GET.get('q', '')
    viviendas = []

    if busqueda:
        viviendas = Vivienda.objects.filter(
            estado='Activo'
        ).filter(
            Q(codigo_qr__icontains=busqueda) |
            Q(direccion__icontains=busqueda) |
            Q(responsable_familia__icontains=busqueda)
        )[:20]

    return render(request, 'inspecciones/buscar_vivienda.html', {
        'viviendas': viviendas,
        'busqueda': busqueda,
    })
