"""
Generador de Excel de PRUEBA con datos 100 % FICTICIOS que imitan la estructura
de los formatos MSPAS. Sirve para validar `importar_formatos` sin usar datos
reales. No contiene nombres de personas.

Genera, en la carpeta indicada:
  - prueba_A1_ENC.xlsx                 A-1 con filas válidas, filas con errores
                                       y una hoja de aldea (fuera de alcance)
  - prueba_encuestas_2026.xlsx         Encuestas y verificaciones (hoja 2026)
  - prueba_consolidado_2026.xlsx       Consolidado mensual (SEPTIEMBRE, OCTUBRE, INF)
  - prueba_RECHAZO_ficha.xlsx          Imita una ficha epidemiológica → debe rechazarse
  - prueba_RECHAZO_control.xlsx        Imita el control MHT (nombre neutro) → debe rechazarse
"""
import datetime
import os

from openpyxl import Workbook

TIPOS = ['Pilas', 'Toneles', 'Llantas', 'Floreros', 'Cubetas', 'Árbol y plantas',
         'Pozos y similares', 'Tanques', 'Otros']

FECHA_A1 = datetime.date(2026, 10, 5)


def _hoja_a1(ws, localidad, fecha, clase, filas):
    ws.append(['FORMULARIO A-1 — ENCUESTA ENTOMOLÓGICA (DATOS FICTICIOS DE PRUEBA)'])
    ws.append([f'LOCALIDAD: {localidad}'])
    ws.append(['FECHA:', fecha])
    if clase:
        ws.append(['CLASE:', clase])
    ws.append([])
    grupos = ['No. Orden', 'HAB', 'P/O', 'MZ', 'CASA', 'Casas', None]
    subs = [None] * 5 + ['Insp.', 'Pos.']
    for t in TIPOS:
        grupos += [t, None]
        subs += ['Insp.', 'Pos.']
    grupos += ['Criadero', 'Pupas', 'Abate']
    ws.append(grupos)
    ws.append(subs)
    for f in filas:
        ws.append(f)
    ws.append(['TOTAL'])


def _fila_a1(orden, hab, po, mz, casa, casa_pos, depositos, criadero=0, pupas=0, abate=0):
    """depositos: dict {indice_tipo: (insp, pos)}."""
    fila = [orden, hab, po, mz, casa, 1, casa_pos]
    for i in range(len(TIPOS)):
        fila += list(depositos.get(i, (None, None)))
    return fila + [criadero, pupas, abate]


def generar_a1(ruta):
    wb = Workbook()
    ws = wb.active
    ws.title = 'ENC1'
    _hoja_a1(ws, 'Bo. El Centro', FECHA_A1, 'ENC', [
        # válidas
        _fila_a1(1, 5, 5, '3', '12', 1, {0: (2, 1), 2: (1, 0)}, criadero=1, abate=1),
        _fila_a1(2, 4, 4, '3', '14', 0, {0: (1, 0), 3: (2, 0)}),
        _fila_a1(3, 6, 6, '4', '2', 0, {}),
        _fila_a1(4, 3, 3, '4', '5', 1, {1: (1, 1)}, abate=1),
        # con errores (deben rechazarse sin abortar el lote)
        _fila_a1(5, 4, 4, '5', '7', 1, {0: (1, 3)}),          # positivos > inspeccionados
        _fila_a1(6, 4, 4, '5', None, 0, {0: (1, 0)}),         # falta CASA
        _fila_a1(7, 2, 2, '5', '9', 0, {4: (2, 1)}),          # casa negativa con positivos
        _fila_a1(2, 4, 4, '6', '1', 0, {0: (1, 0)}),          # No. Orden repetido
        _fila_a1(9, -1, 0, '6', '3', 0, {}),                  # HAB negativo
    ])

    ws2 = wb.create_sheet('ENC2')
    _hoja_a1(ws2, 'Barrio La Llovizna', FECHA_A1 + datetime.timedelta(days=1), 'VERIF', [
        _fila_a1(1, 7, 7, '1', '3', 1, {5: (3, 2)}, criadero=2, abate=1),
        _fila_a1(2, 5, 5, '1', '8', 0, {7: (1, 0)}),
    ])

    ws3 = wb.create_sheet('ENC3')
    _hoja_a1(ws3, 'ALDEA EL ROSARIO', FECHA_A1, 'ENC', [   # fuera de alcance
        _fila_a1(1, 4, 4, '1', '1', 0, {0: (1, 0)}),
    ])
    wb.save(ruta)


def generar_encuestas(ruta):
    wb = Workbook()
    ws = wb.active
    ws.title = '2026'
    ws.append(['ENCUESTAS Y VERIFICACIONES DENGUE 2026 (DATOS FICTICIOS DE PRUEBA)'])
    ws.append([])
    ws.append(['FECHA', 'LOCALIDAD', 'CLASE', 'Casas', None, 'Recipientes', None,
               'I.C.', 'I.B.', 'I.R.'])
    ws.append([None, None, None, 'Insp.', 'Pos.', 'Insp.', 'Pos.'])
    ws.append([datetime.date(2026, 9, 14), 'EL CENTRO', 'ENC', 40, 4, 160, 6, 10.0, 15.0, 3.8])
    ws.append([datetime.date(2026, 9, 15), 'LA LLOVIZNA', 'ENC', 30, 9, 120, 14, 30.0, 46.7, 11.7])
    ws.append([datetime.date(2026, 9, 28), 'LA LLOVIZNA', 'VERIF', 30, 5, 118, 7, 16.7, 23.3, 5.9])
    ws.append([datetime.date(2026, 10, 12), 'EL CAMPO', 'ENC', 25, 1, 90, 1, 9.0, 4.0, 1.1])  # I.C. mal en la hoja (es 4.0)
    ws.append([datetime.date(2026, 10, 13), 'CAMILO ALVARADO', 'ENC', 20, 25, 70, 30])           # pos > insp
    ws.append([datetime.date(2026, 10, 14), 'ALDEA LAS FLORES', 'ENC', 15, 2, 50, 2])            # fuera de alcance
    ws.append(['TOTAL'])

    est = wb.create_sheet('EST. SALA')  # derivada: el lector la ignora
    est.append(['Estratificación (derivada, se ignora)'])
    wb.save(ruta)


def _hoja_consolidado(ws, mes, filas):
    ws.append([f'VIGILANCIA Y CONTROL MENSUAL DEL DENGUE 2026 — {mes} (DATOS FICTICIOS)'])
    ws.append([])
    ws.append(['Localidad', 'Personas orientadas', 'Viviendas', None, None, None, None,
               'Depósitos', None, None, 'Muestras', 'Clase'])
    ws.append([None, None, 'Insp.', 'Pos.', 'Abatizadas', 'Deschatarrizadas', 'Fumigadas',
               'Insp.', 'Pos.', 'Tratados'])
    for f in filas:
        ws.append(f)
    ws.append(['TOTAL'])


def generar_consolidado(ruta):
    wb = Workbook()
    ws = wb.active
    ws.title = 'SEPTIEMBRE'
    _hoja_consolidado(ws, 'SEPTIEMBRE', [
        ['El Centro', 160, 40, 4, 6, 10, 0, 160, 6, 30, 2, 'ENC'],
        ['La Llovizna', 120, 30, 9, 12, 8, 0, 120, 14, 25, 3, 'ENC'],
        ['La Llovizna', 0, 0, 0, 0, 0, 30, 0, 0, 0, 0, 'FUM'],
    ])
    ws2 = wb.create_sheet('OCTUBRE')
    _hoja_consolidado(ws2, 'OCTUBRE', [
        ['El Campo', 95, 25, 1, 2, 5, 0, 90, 1, 12, 1, 'ENC'],
        ['El Jardín', 80, 20, 30, 1, 1, 0, 60, 2, 5, 0, 'ENC'],    # pos > insp
        ['Aldea San José', 50, 15, 2, 2, 2, 0, 40, 2, 4, 0, 'ENC'],  # fuera de alcance
        ['El Campo', 10, 3, 0, 0, 0, 0, 9, 0, 0, 0, None],          # sin clase
    ])
    inf = wb.create_sheet('INF')  # resumen: el lector la ignora
    inf.append(['Informe consolidado (se ignora)'])
    wb.save(ruta)


def generar_ficha_epidemiologica(ruta):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Hoja1'
    ws.append(['FICHA EPIDEMIOLÓGICA DE DENGUE (FICTICIA, PARA PROBAR EL RECHAZO)'])
    ws.append(['No.', 'Nombre del paciente', 'Fecha de nacimiento', 'Localidad'])
    ws.append([1, 'PERSONA FICTICIA', datetime.date(1990, 1, 1), 'El Centro'])
    wb.save(ruta)


def generar_control_mht(ruta):
    # Nombre de archivo neutro: el rechazo debe salir del contenido.
    wb = Workbook()
    ws = wb.active
    ws.title = 'Registro'
    ws.append(['CONTROL MHT (FICTICIO, PARA PROBAR EL RECHAZO)'])
    ws.append(['No.', 'Localidad', 'Gota gruesa', 'Resultado'])
    ws.append([1, 'El Centro', 'Sí', 'Negativo'])
    wb.save(ruta)


ARCHIVOS = {
    'prueba_A1_ENC.xlsx': generar_a1,
    'prueba_encuestas_2026.xlsx': generar_encuestas,
    'prueba_consolidado_2026.xlsx': generar_consolidado,
    'prueba_RECHAZO_ficha.xlsx': generar_ficha_epidemiologica,
    'prueba_RECHAZO_control.xlsx': generar_control_mht,
}


def generar_todo(destino):
    os.makedirs(destino, exist_ok=True)
    rutas = {}
    for nombre, generador in ARCHIVOS.items():
        ruta = os.path.join(destino, nombre)
        generador(ruta)
        rutas[nombre] = ruta
    return rutas
