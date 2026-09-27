"""
Vistas del módulo de Reportes — VectorScan QR
Sprint 5: Reportes estadísticos y exportación Excel/CSV
"""
import csv
import io
from datetime import datetime, timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Count, Q
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from apps.viviendas.models import Vivienda
from apps.inspecciones.models import Inspeccion
from apps.usuarios.models import Usuario


def _get_filtros(request):
    """Extrae filtros comunes de la solicitud."""
    fecha_desde = request.GET.get('desde', '')
    fecha_hasta = request.GET.get('hasta', '')
    zona = request.GET.get('zona', '')
    riesgo = request.GET.get('riesgo', '')

    filtros = Q(estado='Activo')
    if fecha_desde:
        filtros &= Q(fecha_inspeccion__date__gte=fecha_desde)
    if fecha_hasta:
        filtros &= Q(fecha_inspeccion__date__lte=fecha_hasta)
    if zona:
        filtros &= Q(vivienda__zona=zona)
    if riesgo:
        filtros &= Q(nivel_riesgo=riesgo)

    return filtros, fecha_desde, fecha_hasta, zona, riesgo


def _estilo_excel(wb):
    """Aplica estilos corporativos al workbook."""
    header_font = Font(name='Arial', bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='1E3A5F', end_color='1E3A5F', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    return header_font, header_fill, thin_border


@login_required
def panel_reportes(request):
    """Panel principal de reportes con opciones."""
    hoy = timezone.now()
    hace_30 = hoy - timedelta(days=30)

    zonas = Vivienda.objects.filter(estado='Activo').values_list(
        'zona', flat=True
    ).distinct().order_by('zona')

    stats = {
        'viviendas': Vivienda.objects.filter(estado='Activo').count(),
        'inspecciones': Inspeccion.objects.filter(estado='Activo').count(),
        'insp_mes': Inspeccion.objects.filter(estado='Activo', fecha_inspeccion__gte=hace_30).count(),
        'alto': Inspeccion.objects.filter(estado='Activo', nivel_riesgo='Alto').count(),
        'medio': Inspeccion.objects.filter(estado='Activo', nivel_riesgo='Medio').count(),
        'bajo': Inspeccion.objects.filter(estado='Activo', nivel_riesgo='Bajo').count(),
    }

    return render(request, 'reportes/panel.html', {
        'zonas': zonas,
        'stats': stats,
    })


@login_required
def reporte_inspecciones(request):
    """Reporte detallado de inspecciones con filtros."""
    filtros, desde, hasta, zona, riesgo = _get_filtros(request)
    inspecciones = Inspeccion.objects.filter(filtros).select_related('vivienda', 'usuario')

    zonas = Vivienda.objects.filter(estado='Activo').values_list('zona', flat=True).distinct()

    return render(request, 'reportes/inspecciones.html', {
        'inspecciones': inspecciones[:200],
        'total': inspecciones.count(),
        'desde': desde, 'hasta': hasta, 'zona': zona, 'riesgo': riesgo,
        'zonas': zonas,
    })


@login_required
def reporte_riesgo(request):
    """Reporte de distribución de riesgo por zona."""
    zonas = Vivienda.objects.filter(estado='Activo').values_list('zona', flat=True).distinct().order_by('zona')

    data_zonas = []
    for z in zonas:
        if not z:
            continue
        inspecciones_zona = Inspeccion.objects.filter(
            estado='Activo', vivienda__zona=z
        )
        data_zonas.append({
            'zona': z,
            'total': inspecciones_zona.count(),
            'alto': inspecciones_zona.filter(nivel_riesgo='Alto').count(),
            'medio': inspecciones_zona.filter(nivel_riesgo='Medio').count(),
            'bajo': inspecciones_zona.filter(nivel_riesgo='Bajo').count(),
        })

    return render(request, 'reportes/riesgo.html', {'data_zonas': data_zonas})


@login_required
def reporte_productividad(request):
    """Reporte de productividad por técnico."""
    tecnicos = Usuario.objects.filter(
        estado='Activo', rol__nombre='tecnico'
    ).annotate(
        total_inspecciones=Count('inspecciones_realizadas', filter=Q(inspecciones_realizadas__estado='Activo'))
    ).order_by('-total_inspecciones')

    # Si no hay técnicos con ese rol, mostrar todos los que tengan inspecciones
    if not tecnicos.exists():
        tecnicos = Usuario.objects.filter(
            estado='Activo',
            inspecciones_realizadas__estado='Activo'
        ).annotate(
            total_inspecciones=Count('inspecciones_realizadas')
        ).order_by('-total_inspecciones')

    return render(request, 'reportes/productividad.html', {'tecnicos': tecnicos})


@login_required
def exportar_excel(request):
    """Exportar inspecciones a Excel con formato profesional."""
    filtros, desde, hasta, zona, riesgo = _get_filtros(request)
    inspecciones = Inspeccion.objects.filter(filtros).select_related('vivienda', 'usuario')

    wb = Workbook()
    ws = wb.active
    ws.title = "Inspecciones VectorScan QR"
    header_font, header_fill, thin_border = _estilo_excel(wb)

    # Título
    ws.merge_cells('A1:J1')
    ws['A1'] = 'Reporte de Inspecciones — VectorScan QR'
    ws['A1'].font = Font(name='Arial', bold=True, size=14, color='1E3A5F')
    ws['A2'] = f'Generado: {timezone.now().strftime("%d/%m/%Y %H:%M")}'
    ws['A2'].font = Font(name='Arial', italic=True, size=10, color='666666')
    if desde or hasta:
        ws['A3'] = f'Período: {desde or "inicio"} a {hasta or "hoy"}'
        ws['A3'].font = Font(name='Arial', italic=True, size=10, color='666666')

    # Encabezados
    headers = ['Código QR', 'Dirección', 'Zona', 'Responsable', 'Fecha', 'Técnico',
               'Larvas', 'Criaderos', 'Depósitos', 'Nivel Riesgo']
    row_num = 5
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row_num, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    # Colores de riesgo
    fill_alto = PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid')
    fill_medio = PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid')
    fill_bajo = PatternFill(start_color='DCFCE7', end_color='DCFCE7', fill_type='solid')

    # Datos
    for insp in inspecciones:
        row_num += 1
        ws.cell(row=row_num, column=1, value=insp.vivienda.codigo_qr).border = thin_border
        ws.cell(row=row_num, column=2, value=insp.vivienda.direccion).border = thin_border
        ws.cell(row=row_num, column=3, value=insp.vivienda.zona or 'N/A').border = thin_border
        ws.cell(row=row_num, column=4, value=insp.vivienda.responsable_familia).border = thin_border
        ws.cell(row=row_num, column=5, value=insp.fecha_inspeccion.strftime('%d/%m/%Y %H:%M')).border = thin_border
        ws.cell(row=row_num, column=6, value=insp.usuario.nombre_completo or insp.usuario.username).border = thin_border
        ws.cell(row=row_num, column=7, value='Sí' if insp.presencia_larvas else 'No').border = thin_border
        ws.cell(row=row_num, column=8, value='Sí' if insp.criaderos_potenciales else 'No').border = thin_border
        ws.cell(row=row_num, column=9, value=insp.num_depositos).border = thin_border
        riesgo_cell = ws.cell(row=row_num, column=10, value=insp.nivel_riesgo)
        riesgo_cell.border = thin_border
        riesgo_cell.alignment = Alignment(horizontal='center')
        if insp.nivel_riesgo == 'Alto':
            riesgo_cell.fill = fill_alto
        elif insp.nivel_riesgo == 'Medio':
            riesgo_cell.fill = fill_medio
        else:
            riesgo_cell.fill = fill_bajo

    # Ajustar anchos
    anchos = [18, 35, 10, 25, 18, 25, 8, 10, 12, 14]
    for i, ancho in enumerate(anchos, 1):
        ws.column_dimensions[chr(64 + i)].width = ancho

    # Respuesta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    fecha_archivo = timezone.now().strftime('%Y%m%d')
    response['Content-Disposition'] = f'attachment; filename="VectorScanQR_Inspecciones_{fecha_archivo}.xlsx"'
    wb.save(response)
    return response


@login_required
def exportar_csv(request):
    """Exportar inspecciones a CSV."""
    filtros, desde, hasta, zona, riesgo = _get_filtros(request)
    inspecciones = Inspeccion.objects.filter(filtros).select_related('vivienda', 'usuario')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    fecha_archivo = timezone.now().strftime('%Y%m%d')
    response['Content-Disposition'] = f'attachment; filename="VectorScanQR_Inspecciones_{fecha_archivo}.csv"'
    response.write('\ufeff')  # BOM para Excel

    writer = csv.writer(response)
    writer.writerow(['Código QR', 'Dirección', 'Zona', 'Responsable', 'Fecha',
                     'Técnico', 'Larvas', 'Criaderos', 'Depósitos', 'Nivel Riesgo',
                     'Observaciones'])

    for insp in inspecciones:
        writer.writerow([
            insp.vivienda.codigo_qr,
            insp.vivienda.direccion,
            insp.vivienda.zona or 'N/A',
            insp.vivienda.responsable_familia,
            insp.fecha_inspeccion.strftime('%d/%m/%Y %H:%M'),
            insp.usuario.nombre_completo or insp.usuario.username,
            'Sí' if insp.presencia_larvas else 'No',
            'Sí' if insp.criaderos_potenciales else 'No',
            insp.num_depositos,
            insp.nivel_riesgo,
            insp.observaciones or '',
        ])

    return response
