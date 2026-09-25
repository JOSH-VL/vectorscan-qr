"""
Vistas del módulo de Viviendas y QR — VectorScan QR
Sprint 2: CRUD de viviendas, generación y descarga de QR
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.db.models import Q
from .models import Vivienda, ViviendaHistorico


def _registrar_historial(vivienda, usuario, tipo_operacion):
    """Helper para registrar en la tabla histórica."""
    ViviendaHistorico.objects.create(
        vivienda_original=vivienda,
        codigo_qr=vivienda.codigo_qr,
        direccion=vivienda.direccion,
        responsable_familia=vivienda.responsable_familia,
        num_habitantes=vivienda.num_habitantes,
        zona=vivienda.zona,
        estado=vivienda.estado,
        usuario_cambio=usuario,
        tipo_operacion=tipo_operacion,
    )


@login_required
def lista_viviendas(request):
    """Lista de viviendas con búsqueda y filtros."""
    busqueda = request.GET.get('q', '')
    zona_filtro = request.GET.get('zona', '')

    viviendas = Vivienda.objects.filter(estado='Activo').select_related('registrado_por')

    if busqueda:
        viviendas = viviendas.filter(
            Q(codigo_qr__icontains=busqueda) |
            Q(direccion__icontains=busqueda) |
            Q(responsable_familia__icontains=busqueda)
        )

    if zona_filtro:
        viviendas = viviendas.filter(zona=zona_filtro)

    # Obtener zonas únicas para el filtro
    zonas = Vivienda.objects.filter(estado='Activo').values_list(
        'zona', flat=True
    ).distinct().order_by('zona')

    return render(request, 'viviendas/lista.html', {
        'viviendas': viviendas,
        'busqueda': busqueda,
        'zona_filtro': zona_filtro,
        'zonas': zonas,
        'total': viviendas.count(),
    })


@login_required
def crear_vivienda(request):
    """Crear una nueva vivienda y generar su código QR."""
    if request.method == 'POST':
        direccion = request.POST.get('direccion', '').strip()
        responsable = request.POST.get('responsable_familia', '').strip()
        habitantes = request.POST.get('num_habitantes', 0)
        zona = request.POST.get('zona', '').strip()
        referencia = request.POST.get('referencia', '').strip()
        telefono = request.POST.get('telefono', '').strip()

        if not direccion or not responsable:
            messages.error(request, 'La dirección y el responsable son obligatorios.')
        else:
            vivienda = Vivienda.objects.create(
                direccion=direccion,
                responsable_familia=responsable,
                num_habitantes=int(habitantes) if habitantes else 0,
                zona=zona,
                referencia=referencia,
                telefono=telefono,
                registrado_por=request.user,
            )
            _registrar_historial(vivienda, request.user, 'INSERT')
            messages.success(
                request,
                f'Vivienda registrada exitosamente. Código QR: {vivienda.codigo_qr}'
            )
            return redirect('viviendas:detalle', pk=vivienda.pk)

    return render(request, 'viviendas/crear.html')


@login_required
def detalle_vivienda(request, pk):
    """Detalle de una vivienda con su QR y datos completos."""
    vivienda = get_object_or_404(Vivienda, pk=pk)
    historial = vivienda.historial.all()[:10]
    return render(request, 'viviendas/detalle.html', {
        'vivienda': vivienda,
        'historial': historial,
    })


@login_required
def editar_vivienda(request, pk):
    """Editar datos de una vivienda existente."""
    vivienda = get_object_or_404(Vivienda, pk=pk)

    if request.method == 'POST':
        vivienda.direccion = request.POST.get('direccion', '').strip()
        vivienda.responsable_familia = request.POST.get('responsable_familia', '').strip()
        vivienda.num_habitantes = int(request.POST.get('num_habitantes', 0) or 0)
        vivienda.zona = request.POST.get('zona', '').strip()
        vivienda.referencia = request.POST.get('referencia', '').strip()
        vivienda.telefono = request.POST.get('telefono', '').strip()
        vivienda.save()

        _registrar_historial(vivienda, request.user, 'UPDATE')
        messages.success(request, f'Vivienda {vivienda.codigo_qr} actualizada.')
        return redirect('viviendas:detalle', pk=vivienda.pk)

    return render(request, 'viviendas/editar.html', {'vivienda': vivienda})


@login_required
def desactivar_vivienda(request, pk):
    """Desactivar una vivienda (eliminación lógica)."""
    vivienda = get_object_or_404(Vivienda, pk=pk)

    if request.method == 'POST':
        vivienda.estado = 'Inactivo'
        vivienda.save()
        _registrar_historial(vivienda, request.user, 'DELETE_LOGICO')
        messages.warning(request, f'Vivienda {vivienda.codigo_qr} desactivada.')
        return redirect('viviendas:lista')

    return render(request, 'viviendas/confirmar_desactivar.html', {
        'vivienda': vivienda,
    })


@login_required
def descargar_qr(request, pk):
    """Descarga la imagen QR de una vivienda como PNG."""
    vivienda = get_object_or_404(Vivienda, pk=pk)

    if vivienda.imagen_qr:
        response = FileResponse(
            vivienda.imagen_qr.open('rb'),
            content_type='image/png'
        )
        response['Content-Disposition'] = f'attachment; filename="QR_{vivienda.codigo_qr}.png"'
        return response
    else:
        messages.error(request, 'No se encontró la imagen QR. Regenerando...')
        vivienda.regenerar_qr()
        return redirect('viviendas:detalle', pk=pk)


@login_required
def imprimir_qr(request, pk):
    """Vista de impresión del QR con datos de la vivienda."""
    vivienda = get_object_or_404(Vivienda, pk=pk)
    return render(request, 'viviendas/imprimir_qr.html', {
        'vivienda': vivienda,
    })
