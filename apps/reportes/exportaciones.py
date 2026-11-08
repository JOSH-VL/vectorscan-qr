"""
Exportaciones en layout oficial MSPAS — VectorScan QR (Fase 2, Parte 3)

1. Formulario A-1 (hoja ENC1): una fila por inspección, una hoja por localidad.
2. Consolidado mensual de Vigilancia y Control del Dengue: una fila por
   localidad y clase de trabajo.

Se replican columnas y orden, no el formato visual exacto. Las columnas que el
sistema no captura (pupas, muestras, depósitos tratados) se dejan en blanco a
propósito: no se inventan datos. Ver MAPEO_* para el origen de cada columna.
"""
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from apps.inspecciones.models import DepositoInspeccion

_AZUL = '1E3A5F'
_FONT_TITULO = Font(name='Arial', bold=True, size=13, color=_AZUL)
_FONT_INFO = Font(name='Arial', size=10)
_FONT_HEADER = Font(name='Arial', bold=True, size=9, color='FFFFFF')
_FONT_CELDA = Font(name='Arial', size=10)
_FONT_TOTAL = Font(name='Arial', bold=True, size=10)
_FILL_HEADER = PatternFill(start_color=_AZUL, end_color=_AZUL, fill_type='solid')
_FILL_TOTAL = PatternFill(start_color='E8EEF4', end_color='E8EEF4', fill_type='solid')
_BORDE = Border(*(Side(style='thin'),) * 4)
_CENTRO = Alignment(horizontal='center', vertical='center', wrap_text=True)

MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
         'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']


def nombre_mes(fecha):
    return f'{MESES[fecha.month]} {fecha.year}'


def es_positiva(insp):
    """Mismo criterio que los índices: larvas o algún depósito positivo."""
    return insp.presencia_larvas or insp.depositos_positivos > 0


def personas_orientadas(insp):
    """Habitantes de la vivienda si se dio educación al residente."""
    return insp.vivienda.num_habitantes if insp.educo_residente else 0


def _encabezado(ws, titulo, info, fila_inicio=1):
    ws.cell(row=fila_inicio, column=1, value=titulo).font = _FONT_TITULO
    for i, (etiqueta, valor) in enumerate(info, start=1):
        c = ws.cell(row=fila_inicio + i, column=1, value=f'{etiqueta}: {valor}')
        c.font = _FONT_INFO
    return fila_inicio + len(info) + 2  # fila donde empiezan los encabezados


def _header(ws, fila, col, texto, colspan=1, rowspan=1):
    if colspan > 1 or rowspan > 1:
        ws.merge_cells(start_row=fila, start_column=col,
                       end_row=fila + rowspan - 1, end_column=col + colspan - 1)
    for r in range(fila, fila + rowspan):
        for c in range(col, col + colspan):
            celda = ws.cell(row=r, column=c)
            celda.fill = _FILL_HEADER
            celda.border = _BORDE
    celda = ws.cell(row=fila, column=col, value=texto)
    celda.font = _FONT_HEADER
    celda.alignment = _CENTRO


def _fila(ws, fila, valores, total=False):
    for col, valor in enumerate(valores, start=1):
        c = ws.cell(row=fila, column=col, value=valor)
        c.border = _BORDE
        c.alignment = _CENTRO
        c.font = _FONT_TOTAL if total else _FONT_CELDA
        if total:
            c.fill = _FILL_TOTAL


def _anchos(ws, anchos):
    for col, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(col)].width = ancho


# --------------------------------------------------------------------------- #
# 1. Formulario A-1 (hoja ENC1)
# --------------------------------------------------------------------------- #
MAPEO_A1 = {
    'No. Orden': 'correlativo de la fila',
    'HAB': 'Vivienda.num_habitantes',
    'P/O': 'personas orientadas: habitantes si educo_residente (pendiente confirmar significado)',
    'MZ': 'Vivienda.manzana',
    'CASA': 'Vivienda.numero_casa',
    'Casas insp/pos': '1 por fila / 1 si hay larvas o depósitos positivos',
    'Depósitos por tipo': 'DepositoInspeccion (en blanco si no hay desglose)',
    'Criadero': '1 si criaderos_potenciales',
    'Pupas': 'no se captura (en blanco)',
    'Abate': '1 si aplico_larvicida',
}


def libro_formulario_a1(inspecciones_por_zona, mes, clases):
    """
    `inspecciones_por_zona`: dict {zona: [Inspeccion, ...]} ordenadas por fecha,
    con vivienda y depositos precargados. Crea una hoja por zona.
    """
    wb = Workbook()
    wb.remove(wb.active)
    tipos = DepositoInspeccion.TIPOS

    if not inspecciones_por_zona:
        inspecciones_por_zona = {'Sin datos': []}

    for zona, inspecciones in inspecciones_por_zona.items():
        ws = wb.create_sheet(title=zona.replace('Barrio ', '')[:31] or 'Sin zona')
        fila = _encabezado(ws, 'FORMULARIO A-1 — Encuesta entomológica (Aedes aegypti)', [
            ('Localidad', zona),
            ('Mes', nombre_mes(mes)),
            ('Clase de trabajo', ', '.join(clases)),
            ('Fuente', 'VectorScan QR — Centro de Salud de San Felipe, Retalhuleu'),
        ])

        # Encabezado en dos filas: grupos arriba, insp/pos abajo.
        col = 1
        for texto in ['No. Orden', 'HAB', 'P/O', 'MZ', 'CASA']:
            _header(ws, fila, col, texto, rowspan=2)
            col += 1
        _header(ws, fila, col, 'Casas', colspan=2)
        _header(ws, fila + 1, col, 'Insp.')
        _header(ws, fila + 1, col + 1, 'Pos.')
        col += 2
        for _, etiqueta in tipos:
            _header(ws, fila, col, etiqueta, colspan=2)
            _header(ws, fila + 1, col, 'Insp.')
            _header(ws, fila + 1, col + 1, 'Pos.')
            col += 2
        for texto in ['Criadero', 'Pupas', 'Abate']:
            _header(ws, fila, col, texto, rowspan=2)
            col += 1
        total_cols = col - 1

        fila += 2
        primera = fila
        for n, insp in enumerate(inspecciones, start=1):
            desglose = {d.tipo: d for d in insp.depositos.all()}
            valores = [
                n,
                insp.vivienda.num_habitantes,
                personas_orientadas(insp),
                insp.vivienda.manzana or None,
                insp.vivienda.numero_casa or None,
                1,
                1 if es_positiva(insp) else 0,
            ]
            for tipo, _ in tipos:
                d = desglose.get(tipo)
                valores += [d.inspeccionados, d.positivos] if d else [None, None]
            valores += [
                1 if insp.criaderos_potenciales else 0,
                None,  # pupas: no se captura
                1 if insp.aplico_larvicida else 0,
            ]
            _fila(ws, fila, valores)
            fila += 1

        # Totales (sumas de columnas numéricas, salvo No. Orden, MZ y CASA).
        if inspecciones:
            totales = ['TOTAL']
            for c in range(2, total_cols + 1):
                letra = get_column_letter(c)
                if c in (4, 5):
                    totales.append(None)
                else:
                    totales.append(f'=SUM({letra}{primera}:{letra}{fila - 1})')
            _fila(ws, fila, totales, total=True)

        _anchos(ws, [8, 6, 6, 7, 7] + [7] * (total_cols - 5))
        ws.freeze_panes = ws.cell(row=primera, column=2)

    _hoja_notas(wb, 'Notas A-1', MAPEO_A1)
    return wb


# --------------------------------------------------------------------------- #
# 2. Consolidado mensual de Vigilancia y Control del Dengue
# --------------------------------------------------------------------------- #
MAPEO_CONSOLIDADO = {
    'Localidad': 'Vivienda.zona',
    'Personas orientadas': 'suma de habitantes de viviendas con educo_residente',
    'Viviendas insp.': 'viviendas distintas (última inspección del mes por clase)',
    'Viviendas pos.': 'con larvas o depósitos positivos',
    'Abatizadas': 'aplico_larvicida',
    'Deschatarrizadas': 'elimino_criaderos',
    'Fumigadas': 'viviendas con clase de trabajo FUM',
    'Depósitos insp./pos.': 'suma de num_depositos / depositos_positivos',
    'Depósitos tratados': 'no se captura (en blanco)',
    'Muestras': 'no se captura; laboratorio A-5 fuera de alcance (en blanco)',
    'Clase': 'Inspeccion.clase_trabajo',
}


def filas_consolidado(inspecciones):
    """
    `inspecciones`: Inspeccion del mes, de la más reciente a la más antigua.
    Una vivienda cuenta una vez por clase de trabajo (su última del mes).
    Retorna filas ordenadas por localidad y clase.
    """
    ultima = {}
    for insp in inspecciones:
        ultima.setdefault((insp.vivienda_id, insp.clase_trabajo), insp)

    grupos = {}
    for insp in ultima.values():
        clave = (insp.vivienda.zona, insp.clase_trabajo)
        g = grupos.setdefault(clave, dict(
            localidad=clave[0], clase=clave[1], personas=0, viv_insp=0, viv_pos=0,
            abatizadas=0, deschatarrizadas=0, fumigadas=0, dep_insp=0, dep_pos=0))
        g['personas'] += personas_orientadas(insp)
        g['viv_insp'] += 1
        g['viv_pos'] += 1 if es_positiva(insp) else 0
        g['abatizadas'] += 1 if insp.aplico_larvicida else 0
        g['deschatarrizadas'] += 1 if insp.elimino_criaderos else 0
        g['fumigadas'] += 1 if insp.clase_trabajo == 'FUM' else 0
        g['dep_insp'] += insp.num_depositos
        g['dep_pos'] += insp.depositos_positivos
    return [grupos[k] for k in sorted(grupos)]


def libro_consolidado(filas, mes):
    wb = Workbook()
    ws = wb.active
    ws.title = MESES[mes.month].upper()
    fila = _encabezado(ws, 'VIGILANCIA Y CONTROL DEL DENGUE — Consolidado mensual', [
        ('Mes', nombre_mes(mes)),
        ('Área', 'Casco urbano de San Felipe, Retalhuleu'),
        ('Fuente', 'VectorScan QR — Centro de Salud de San Felipe, Retalhuleu'),
    ])

    _header(ws, fila, 1, 'Localidad', rowspan=2)
    _header(ws, fila, 2, 'Personas orientadas', rowspan=2)
    _header(ws, fila, 3, 'Viviendas', colspan=5)
    for i, t in enumerate(['Insp.', 'Pos.', 'Abatizadas', 'Deschatarrizadas', 'Fumigadas']):
        _header(ws, fila + 1, 3 + i, t)
    _header(ws, fila, 8, 'Depósitos', colspan=3)
    for i, t in enumerate(['Insp.', 'Pos.', 'Tratados']):
        _header(ws, fila + 1, 8 + i, t)
    _header(ws, fila, 11, 'Muestras', rowspan=2)
    _header(ws, fila, 12, 'Clase', rowspan=2)

    fila += 2
    primera = fila
    for f in filas:
        _fila(ws, fila, [
            f['localidad'], f['personas'], f['viv_insp'], f['viv_pos'],
            f['abatizadas'], f['deschatarrizadas'], f['fumigadas'],
            f['dep_insp'], f['dep_pos'], None, None, f['clase'],
        ])
        ws.cell(row=fila, column=1).alignment = Alignment(horizontal='left', vertical='center')
        fila += 1

    if filas:
        totales = ['TOTAL'] + [
            f'=SUM({get_column_letter(c)}{primera}:{get_column_letter(c)}{fila - 1})'
            if c not in (10, 11) else None
            for c in range(2, 12)
        ] + [None]
        _fila(ws, fila, totales, total=True)

    _anchos(ws, [26, 12, 8, 8, 11, 15, 10, 8, 8, 9, 10, 13])
    ws.freeze_panes = ws.cell(row=primera, column=2)
    _hoja_notas(wb, 'Notas', MAPEO_CONSOLIDADO)
    return wb


def _hoja_notas(wb, titulo, mapeo):
    ws = wb.create_sheet(title=titulo)
    ws['A1'] = 'Origen de cada columna en VectorScan QR'
    ws['A1'].font = _FONT_TITULO
    for i, (col, origen) in enumerate(mapeo.items(), start=3):
        ws.cell(row=i, column=1, value=col).font = _FONT_TOTAL
        ws.cell(row=i, column=2, value=origen).font = _FONT_CELDA
    ws.column_dimensions['A'].width = 24
    ws.column_dimensions['B'].width = 90
