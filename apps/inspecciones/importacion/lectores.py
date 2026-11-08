"""
Lectores de las tres fuentes de vigilancia entomológica. Cada lector recibe un
libro de openpyxl ya revisado (sin datos sensibles) y devuelve una `Lectura`
con registros validados, rechazos, omisiones y avisos. No escriben en la base.

ESTRUCTURA ESPERADA (supuesta a partir del brief; ajustar contra un Excel real
anonimizado antes de importar en producción):

A-1 (hojas ENC1, ENC2, ...):
    cabecera con LOCALIDAD:, FECHA:, CLASE: (opcional) y luego una tabla con
    encabezado en dos filas: No. Orden | HAB | P/O | MZ | CASA | Casas (Insp/Pos)
    | 9 tipos de depósito (Insp/Pos) | Criadero | Pupas | Abate. Termina en TOTAL.

Encuestas y verificaciones (hoja con el año, p. ej. "2026"; "EST. SALA" se
ignora porque es derivada):
    FECHA | LOCALIDAD | CLASE | Casas (Insp/Pos) | Recipientes (Insp/Pos) |
    I.C. | I.B. | I.R.

Consolidado mensual (una hoja por mes; "INF" se ignora porque es resumen):
    Localidad | Personas orientadas | Viviendas (Insp/Pos/Abatizadas/
    Deschatarrizadas/Fumigadas) | Depósitos (Insp/Pos/Tratados) | Muestras | Clase
"""
import re

from .comun import (
    ErrorCelda, Lectura, Rechazo, barrio_canonico, buscar_columna, buscar_fila,
    clase_trabajo, decimal_opcional, entero, es_fila_vacia, fecha, mapa_columnas,
    norm, texto_corto, valor_etiqueta,
)

TIPOS_DEPOSITO = [  # (valor en DepositoInspeccion, prefijo del encabezado)
    ('PILAS', 'PILA'), ('TONELES', 'TONEL'), ('LLANTAS', 'LLANTA'),
    ('FLOREROS', 'FLORERO'), ('CUBETAS', 'CUBETA'), ('ARBOL_PLANTAS', 'ARBOL'),
    ('POZOS', 'POZO'), ('TANQUES', 'TANQUE'), ('OTROS', 'OTRO'),
]

MESES = {
    'ENERO': 1, 'ENE': 1, 'FEBRERO': 2, 'FEB': 2, 'MARZO': 3, 'MAR': 3,
    'ABRIL': 4, 'ABR': 4, 'MAYO': 5, 'MAY': 5, 'JUNIO': 6, 'JUN': 6,
    'JULIO': 7, 'JUL': 7, 'AGOSTO': 8, 'AGO': 8, 'SEPTIEMBRE': 9, 'SETIEMBRE': 9,
    'SEP': 9, 'SEPT': 9, 'OCTUBRE': 10, 'OCT': 10, 'NOVIEMBRE': 11, 'NOV': 11,
    'DICIEMBRE': 12, 'DIC': 12,
}


class ErrorEstructura(Exception):
    """El archivo no tiene la estructura del tipo indicado."""


class ErrorAnio(Exception):
    """El consolidado no indica el año y no se pasó --anio."""


# --------------------------------------------------------------------------- #
# Auxiliares
# --------------------------------------------------------------------------- #
def _filas(hoja):
    return [list(f) for f in hoja.iter_rows(values_only=True)]


def _celda(fila, i):
    return fila[i] if i is not None and i < len(fila) else None


def _es_total(fila):
    return any(norm(v).startswith('TOTAL') for v in fila[:4])


class _Errores:
    """Junta todos los errores de una fila para reportarlos juntos."""

    def __init__(self):
        self.lista = []

    def __call__(self, funcion, *args, **kwargs):
        try:
            return funcion(*args, **kwargs)
        except ErrorCelda as e:
            self.lista.append(str(e))
            return None

    def agregar(self, mensaje):
        self.lista.append(mensaje)


def _columna_par(columnas, prefijo, sub):
    """Columna cuyo encabezado empieza con `prefijo` y termina en `sub...`."""
    for i, clave in columnas.items():
        partes = clave.split()
        if clave.startswith(prefijo) and len(partes) > 1 and partes[-1].startswith(sub):
            return i
    return None


def _encabezado_tabla(filas, hoja, condicion):
    idx = buscar_fila(filas, condicion)
    if idx is None:
        raise ErrorEstructura(f'hoja "{hoja}": no se encontró el encabezado de la tabla')
    sub = filas[idx + 1] if idx + 1 < len(filas) else None
    columnas, usa_sub = mapa_columnas(filas[idx], sub)
    inicio = idx + (2 if usa_sub else 1)
    return idx, columnas, inicio


def _indice(num, den):
    return round(num * 100 / den, 1) if den else None


def detectar_anio(nombre_archivo, libro):
    """Año del consolidado: del nombre del archivo o de los títulos."""
    m = re.search(r'(20\d\d)', nombre_archivo)
    if m:
        return int(m.group(1))
    for hoja in libro.worksheets:
        for fila in hoja.iter_rows(max_row=6, values_only=True):
            for celda in fila:
                if isinstance(celda, str):
                    m = re.search(r'\b(20\d\d)\b', celda)
                    if m:
                        return int(m.group(1))
    return None


# --------------------------------------------------------------------------- #
# 1. Formulario A-1 (hoja ENC1)
# --------------------------------------------------------------------------- #
def leer_a1(libro, clase_por_defecto='ENC'):
    hojas = [h for h in libro.worksheets if re.fullmatch(r'ENC ?\d*', norm(h.title))]
    if not hojas:
        raise ErrorEstructura(
            'no tiene hojas ENC1/ENC2...; no parece un Formulario A-1. '
            'Revisá --tipo.')

    lectura = Lectura()
    vistos = set()  # (localidad, fecha, clase, correlativo) para duplicados
    for hoja in hojas:
        filas = _filas(hoja)
        try:
            idx, columnas, inicio = _encabezado_tabla(
                filas, hoja.title,
                lambda f: any(c in ('NO ORDEN', 'NO DE ORDEN', 'N ORDEN') for c in f)
                and ('MZ' in f or 'CASA' in f))
        except ErrorEstructura as e:
            lectura.rechazos.append(Rechazo(hoja.title, 1, f'hoja completa: {e}'))
            continue

        cabecera = filas[:idx]
        loc_crudo = valor_etiqueta(cabecera, 'LOCALIDAD')
        if loc_crudo is None:
            lectura.rechazos.append(Rechazo(hoja.title, 1, 'hoja completa: falta LOCALIDAD en la cabecera'))
            continue
        localidad = barrio_canonico(loc_crudo)
        if localidad is None:
            lectura.omitidos.append(Rechazo(
                hoja.title, 1, f'hoja completa: localidad "{loc_crudo}" fuera del casco urbano'))
            continue
        try:
            f_insp = fecha(valor_etiqueta(cabecera, 'FECHA'), 'FECHA de la cabecera')
        except ErrorCelda as e:
            lectura.rechazos.append(Rechazo(hoja.title, 1, f'hoja completa: {e}'))
            continue
        clase_crudo = valor_etiqueta(cabecera, 'CLASE')
        clase = clase_trabajo(clase_crudo) if clase_crudo is not None else None
        if clase_crudo is not None and clase is None:
            lectura.rechazos.append(Rechazo(hoja.title, 1, 'hoja completa: CLASE de trabajo no reconocida'))
            continue
        if clase is None:
            clase = clase_por_defecto
            lectura.avisos.append(
                f'Hoja "{hoja.title}": sin CLASE en la cabecera; se usó {clase}.')

        col = {
            'orden': buscar_columna(columnas, exactas=('NO ORDEN', 'NO DE ORDEN', 'N ORDEN')),
            'hab': buscar_columna(columnas, exactas=('HAB', 'HABITANTES')),
            'po': buscar_columna(columnas, exactas=('P O', 'PO')),
            'mz': buscar_columna(columnas, exactas=('MZ', 'MANZANA')),
            'casa': buscar_columna(columnas, exactas=('CASA', 'NO CASA')),
            'casas_insp': _columna_par(columnas, 'CASAS', 'INSP'),
            'casas_pos': _columna_par(columnas, 'CASAS', 'POS'),
            'criadero': buscar_columna(columnas, prefijos=('CRIADERO',)),
            'pupas': buscar_columna(columnas, prefijos=('PUPA',)),
            'abate': buscar_columna(columnas, prefijos=('ABATE',)),
        }
        faltan = [n for n in ('orden', 'mz', 'casa') if col[n] is None]
        if faltan:
            lectura.rechazos.append(Rechazo(
                hoja.title, idx + 1, f'hoja completa: faltan columnas {", ".join(faltan)}'))
            continue
        col_tipos = {
            tipo: (_columna_par(columnas, pref, 'INSP'), _columna_par(columnas, pref, 'POS'))
            for tipo, pref in TIPOS_DEPOSITO
        }
        lectura.hojas_leidas.append(hoja.title)

        for n_fila, fila in enumerate(filas[inicio:], start=inicio + 1):
            if es_fila_vacia(fila):
                continue
            if _es_total(fila):
                break
            err = _Errores()
            correlativo = err(entero, _celda(fila, col['orden']), 'No. Orden', requerido=True)
            if correlativo == 0:
                err.agregar('No. Orden: debe ser mayor que 0')
            manzana = err(texto_corto, _celda(fila, col['mz']), 'MZ', requerido=True)
            casa = err(texto_corto, _celda(fila, col['casa']), 'CASA', requerido=True)
            hab = err(entero, _celda(fila, col['hab']), 'HAB')
            po = err(entero, _celda(fila, col['po']), 'P/O')
            casas_insp = err(entero, _celda(fila, col['casas_insp']), 'Casas insp.')
            casas_pos = err(entero, _celda(fila, col['casas_pos']), 'Casas pos.')
            if casas_insp not in (None, 1):
                err.agregar('Casas insp.: debe ser 1 (una fila por casa)')
            if casas_pos not in (None, 0, 1):
                err.agregar('Casas pos.: debe ser 0 o 1')

            depositos = {}
            for tipo, (ci, cp) in col_tipos.items():
                insp = err(entero, _celda(fila, ci), f'{tipo} insp.')
                pos = err(entero, _celda(fila, cp), f'{tipo} pos.')
                if insp is None and pos is None:
                    continue
                insp, pos = insp or 0, pos or 0
                if pos > insp:
                    err.agregar(f'{tipo}: positivos ({pos}) mayor que inspeccionados ({insp})')
                depositos[tipo] = (insp, pos)
            total_insp = sum(i for i, _ in depositos.values())
            total_pos = sum(p for _, p in depositos.values())
            if total_pos > 0 and casas_pos == 0:
                err.agregar('casa marcada negativa pero con depósitos positivos')
            if casas_pos == 1 and depositos and total_pos == 0:
                err.agregar('casa marcada positiva pero sin depósitos positivos')

            criadero = err(entero, _celda(fila, col['criadero']), 'Criadero')
            pupas = err(entero, _celda(fila, col['pupas']), 'Pupas')
            abate = err(entero, _celda(fila, col['abate']), 'Abate')

            clave = (localidad, f_insp, clase, correlativo)
            if correlativo and clave in vistos:
                err.agregar(f'No. Orden {correlativo} repetido para {localidad} el {f_insp:%d/%m/%Y}')

            if err.lista:
                lectura.rechazos.append(Rechazo(hoja.title, n_fila, '; '.join(err.lista)))
                continue
            vistos.add(clave)
            lectura.registros.append({
                'hoja': hoja.title, 'fila': n_fila,
                'localidad': localidad, 'fecha': f_insp, 'clase': clase,
                'correlativo': correlativo, 'manzana': manzana, 'numero_casa': casa,
                'habitantes': hab, 'personas_orientadas': po,
                'casa_positiva': casas_pos == 1 or total_pos > 0,
                'depositos': depositos,
                'num_depositos': total_insp, 'depositos_positivos': total_pos,
                'criaderos': criadero, 'pupas': pupas, 'abate': abate,
            })
    return lectura


# --------------------------------------------------------------------------- #
# 2. Encuestas y verificaciones
# --------------------------------------------------------------------------- #
def leer_encuestas(libro, clase_por_defecto='ENC'):
    hojas = [h for h in libro.worksheets if re.fullmatch(r'(19|20)\d\d', norm(h.title))]
    if not hojas:
        raise ErrorEstructura(
            'no tiene una hoja con el año (p. ej. "2026"); no parece el archivo de '
            'Encuestas y verificaciones. Revisá --tipo.')

    lectura = Lectura()
    vistos = set()
    for hoja in hojas:
        filas = _filas(hoja)
        try:
            idx, columnas, inicio = _encabezado_tabla(
                filas, hoja.title,
                lambda f: 'LOCALIDAD' in f and any(c.startswith('CASA') for c in f))
        except ErrorEstructura as e:
            lectura.rechazos.append(Rechazo(hoja.title, 1, f'hoja completa: {e}'))
            continue
        col = {
            'fecha': buscar_columna(columnas, prefijos=('FECHA',)),
            'localidad': buscar_columna(columnas, exactas=('LOCALIDAD',)),
            'clase': buscar_columna(columnas, prefijos=('CLASE',)),
            'casas_insp': _columna_par(columnas, 'CASA', 'INSP'),
            'casas_pos': _columna_par(columnas, 'CASA', 'POS'),
            'recip_insp': _columna_par(columnas, 'RECIP', 'INSP') or _columna_par(columnas, 'DEPOSITO', 'INSP'),
            'recip_pos': _columna_par(columnas, 'RECIP', 'POS') or _columna_par(columnas, 'DEPOSITO', 'POS'),
            'ic': buscar_columna(columnas, exactas=('I C', 'IC'), prefijos=('INDICE DE CASA',)),
            'ib': buscar_columna(columnas, exactas=('I B', 'IB'), prefijos=('INDICE DE BRETEAU',)),
            'ir': buscar_columna(columnas, exactas=('I R', 'IR'), prefijos=('INDICE DE RECIPIENTE',)),
        }
        faltan = [n for n in ('fecha', 'localidad', 'casas_insp', 'casas_pos',
                              'recip_insp', 'recip_pos') if col[n] is None]
        if faltan:
            lectura.rechazos.append(Rechazo(
                hoja.title, idx + 1, f'hoja completa: faltan columnas {", ".join(faltan)}'))
            continue
        if col['clase'] is None:
            lectura.avisos.append(
                f'Hoja "{hoja.title}": sin columna CLASE; se usó {clase_por_defecto}.')
        lectura.hojas_leidas.append(hoja.title)

        for n_fila, fila in enumerate(filas[inicio:], start=inicio + 1):
            if es_fila_vacia(fila):
                continue
            if _es_total(fila):
                break
            loc_crudo = _celda(fila, col['localidad'])
            localidad = barrio_canonico(loc_crudo)
            if localidad is None:
                lectura.omitidos.append(Rechazo(
                    hoja.title, n_fila, f'localidad "{loc_crudo}" fuera del casco urbano'))
                continue
            err = _Errores()
            f = err(fecha, _celda(fila, col['fecha']), 'FECHA')
            if col['clase'] is not None:
                clase = clase_trabajo(_celda(fila, col['clase']))
                if clase is None:
                    err.agregar('CLASE: no reconocida')
            else:
                clase = clase_por_defecto
            ci = err(entero, _celda(fila, col['casas_insp']), 'Casas insp.', requerido=True)
            cp = err(entero, _celda(fila, col['casas_pos']), 'Casas pos.', requerido=True)
            ri = err(entero, _celda(fila, col['recip_insp']), 'Recipientes insp.', requerido=True)
            rp = err(entero, _celda(fila, col['recip_pos']), 'Recipientes pos.', requerido=True)
            if None not in (ci, cp) and cp > ci:
                err.agregar(f'casas positivas ({cp}) mayor que inspeccionadas ({ci})')
            if None not in (ri, rp) and rp > ri:
                err.agregar(f'recipientes positivos ({rp}) mayor que inspeccionados ({ri})')
            clave = (localidad, f, clase)
            if f and clase and clave in vistos:
                err.agregar(f'registro repetido para {localidad}, {f:%d/%m/%Y}, {clase}')
            if err.lista:
                lectura.rechazos.append(Rechazo(hoja.title, n_fila, '; '.join(err.lista)))
                continue
            vistos.add(clave)

            # Los índices se recalculan; si la hoja trae otros valores, se avisa.
            calculados = {'ic': _indice(cp, ci), 'ib': _indice(rp, ci), 'ir': _indice(rp, ri)}
            for nombre, valor in calculados.items():
                en_hoja = decimal_opcional(_celda(fila, col[nombre]))
                if en_hoja is not None and valor is not None and abs(en_hoja - valor) > 0.15:
                    lectura.avisos.append(
                        f'Hoja "{hoja.title}" fila {n_fila}: {nombre.upper()} en la hoja '
                        f'{en_hoja} ≠ calculado {valor}; se guarda el calculado.')
            lectura.registros.append({
                'hoja': hoja.title, 'fila': n_fila, 'localidad': localidad,
                'fecha': f, 'clase': clase, 'casas_insp': ci, 'casas_pos': cp,
                'recip_insp': ri, 'recip_pos': rp, **calculados,
            })
    return lectura


# --------------------------------------------------------------------------- #
# 3. Consolidado mensual de Vigilancia y Control del Dengue
# --------------------------------------------------------------------------- #
def leer_consolidado(libro, anio):
    hojas = [(h, MESES[norm(h.title)]) for h in libro.worksheets if norm(h.title) in MESES]
    if not hojas:
        raise ErrorEstructura(
            'no tiene hojas por mes (ENERO, FEBRERO...); no parece el Consolidado '
            'mensual. Revisá --tipo.')
    if anio is None:
        raise ErrorAnio('No se pudo deducir el año del consolidado; indicá --anio.')

    lectura = Lectura()
    vistos = set()
    for hoja, mes in hojas:
        filas = _filas(hoja)
        try:
            idx, columnas, inicio = _encabezado_tabla(
                filas, hoja.title,
                lambda f: 'LOCALIDAD' in f and any(c.startswith(('VIVIENDA', 'PERSONAS')) for c in f))
        except ErrorEstructura as e:
            lectura.rechazos.append(Rechazo(hoja.title, 1, f'hoja completa: {e}'))
            continue
        col = {
            'localidad': buscar_columna(columnas, exactas=('LOCALIDAD',)),
            'personas': buscar_columna(columnas, prefijos=('PERSONAS',)),
            'viv_insp': _columna_par(columnas, 'VIVIENDA', 'INSP'),
            'viv_pos': _columna_par(columnas, 'VIVIENDA', 'POS'),
            'abatizadas': _columna_par(columnas, 'VIVIENDA', 'ABAT'),
            'deschatarrizadas': _columna_par(columnas, 'VIVIENDA', 'DESCHAT'),
            'fumigadas': _columna_par(columnas, 'VIVIENDA', 'FUMIG'),
            'dep_insp': _columna_par(columnas, 'DEPOSITO', 'INSP'),
            'dep_pos': _columna_par(columnas, 'DEPOSITO', 'POS'),
            'dep_tratados': _columna_par(columnas, 'DEPOSITO', 'TRAT'),
            'muestras': buscar_columna(columnas, prefijos=('MUESTRA',)),
            'clase': buscar_columna(columnas, prefijos=('CLASE',)),
        }
        faltan = [n for n in ('localidad', 'viv_insp', 'clase') if col[n] is None]
        if faltan:
            lectura.rechazos.append(Rechazo(
                hoja.title, idx + 1, f'hoja completa: faltan columnas {", ".join(faltan)}'))
            continue
        lectura.hojas_leidas.append(hoja.title)

        for n_fila, fila in enumerate(filas[inicio:], start=inicio + 1):
            if es_fila_vacia(fila):
                continue
            if _es_total(fila):
                break
            loc_crudo = _celda(fila, col['localidad'])
            localidad = barrio_canonico(loc_crudo)
            if localidad is None:
                lectura.omitidos.append(Rechazo(
                    hoja.title, n_fila, f'localidad "{loc_crudo}" fuera del casco urbano'))
                continue
            err = _Errores()
            clase = clase_trabajo(_celda(fila, col['clase']))
            if clase is None:
                err.agregar('CLASE: vacía o no reconocida')
            valores = {}
            etiquetas = {
                'personas': 'Personas orientadas', 'viv_insp': 'Viviendas insp.',
                'viv_pos': 'Viviendas pos.', 'abatizadas': 'Abatizadas',
                'deschatarrizadas': 'Deschatarrizadas', 'fumigadas': 'Fumigadas',
                'dep_insp': 'Depósitos insp.', 'dep_pos': 'Depósitos pos.',
                'dep_tratados': 'Depósitos tratados', 'muestras': 'Muestras',
            }
            for campo, etiqueta in etiquetas.items():
                valores[campo] = err(entero, _celda(fila, col[campo]), etiqueta,
                                     requerido=(campo == 'viv_insp'))
            vi, vp = valores['viv_insp'], valores['viv_pos']
            if vi is not None and vp is not None and vp > vi:
                err.agregar(f'viviendas positivas ({vp}) mayor que inspeccionadas ({vi})')
            di, dp = valores['dep_insp'], valores['dep_pos']
            if di is not None and dp is not None and dp > di:
                err.agregar(f'depósitos positivos ({dp}) mayor que inspeccionados ({di})')
            clave = (localidad, anio, mes, clase)
            if clase and clave in vistos:
                err.agregar(f'registro repetido para {localidad}, {hoja.title} {anio}, {clase}')
            if err.lista:
                lectura.rechazos.append(Rechazo(hoja.title, n_fila, '; '.join(err.lista)))
                continue
            vistos.add(clave)
            lectura.registros.append({
                'hoja': hoja.title, 'fila': n_fila, 'localidad': localidad,
                'anio': anio, 'mes': mes, 'clase': clase,
                **valores,  # None = no reportado (distinto de 0)
            })
    return lectura
