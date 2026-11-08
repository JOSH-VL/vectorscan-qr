"""
Utilidades comunes de la importación: normalización de texto, detección de
datos sensibles, delimitación geográfica, lectura de encabezados y conversión
de celdas con validación.

Regla de privacidad: los mensajes de error y de rechazo NUNCA repiten el
contenido de celdas de texto (podría ser un nombre). Solo dicen hoja, fila,
columna y motivo.
"""
import datetime
import re
import unicodedata
from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# Texto
# --------------------------------------------------------------------------- #
def norm(valor):
    """Mayúsculas, sin tildes, solo letras/dígitos separados por un espacio."""
    if valor is None:
        return ''
    s = unicodedata.normalize('NFKD', str(valor)).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Z0-9]+', ' ', s.upper()).strip()


# --------------------------------------------------------------------------- #
# Datos sensibles (Decreto 57-2008): fichas epidemiológicas y formato MHT
# --------------------------------------------------------------------------- #
# Marcadores que no aparecen en los formatos de vigilancia entomológica pero sí
# en fichas de pacientes o en el control MHT de malaria. Se buscan en el nombre
# del archivo, en los nombres de hoja y en las primeras filas de cada hoja.
# Se evitan términos que pueden salir en títulos legítimos del MSPAS
# ("Vigilancia epidemiológica", "diagnóstico entomológico").
MARCADORES_SENSIBLES = {
    'FICHA EPIDEMIOLOGICA': 'ficha epidemiológica',
    'FICHA EPI': 'ficha epidemiológica',
    'PACIENTE': 'datos de pacientes',
    'FECHA DE NACIMIENTO': 'datos de pacientes',
    'FECHA NACIMIENTO': 'datos de pacientes',
    'DPI': 'datos de pacientes',
    'INICIO DE SINTOMAS': 'datos clínicos',
    'FECHA INICIO SINTOMAS': 'datos clínicos',
    'MHT': 'formato MHT (malaria)',
    'MALARIA': 'formato MHT (malaria)',
    'PALUDISMO': 'formato MHT (malaria)',
    'GOTA GRUESA': 'formato MHT (malaria)',
    'PLASMODIUM': 'formato MHT (malaria)',
}
FILAS_A_REVISAR = 25


def _contiene_marcador(texto_norm):
    relleno = f' {texto_norm} '
    for marcador, tipo in MARCADORES_SENSIBLES.items():
        if f' {marcador}' in relleno:
            # Coincidencia al inicio de palabra (evita falsos positivos internos).
            # Se devuelve el marcador (texto fijo), nunca el contenido de la celda.
            return f'{tipo}, marcador "{marcador}"'
    return None


def detectar_datos_sensibles(nombre_archivo, libro):
    """
    Devuelve una descripción del tipo de dato sensible detectado, o None.
    No devuelve ni registra el contenido de las celdas.
    """
    tipo = _contiene_marcador(norm(nombre_archivo))
    if tipo:
        return f'{tipo} (por el nombre del archivo)'
    for hoja in libro.worksheets:
        tipo = _contiene_marcador(norm(hoja.title))
        if tipo:
            return f'{tipo} (hoja "{hoja.title}")'
        for fila in hoja.iter_rows(max_row=FILAS_A_REVISAR, values_only=True):
            for celda in fila:
                if isinstance(celda, str):
                    tipo = _contiene_marcador(norm(celda))
                    if tipo:
                        return f'{tipo} (encabezados de la hoja "{hoja.title}")'
    return None


# --------------------------------------------------------------------------- #
# Delimitación: solo los 6 barrios del casco urbano de San Felipe
# --------------------------------------------------------------------------- #
BARRIOS_CASCO_URBANO = [
    'Barrio El Centro',
    'Barrio La Llovizna',
    'Barrio El Campo',
    'Barrio El Jardín',
    'Barrio Camilo Alvarado',
    'Barrio La Linterna',
]
_PREFIJOS_LOCALIDAD = ('BARRIO ', 'BO ', 'B ', 'COLONIA ', 'COL ', 'SECTOR ')


def _sin_prefijo(texto_norm):
    for p in _PREFIJOS_LOCALIDAD:
        if texto_norm.startswith(p):
            return texto_norm[len(p):]
    return texto_norm


_BARRIOS_POR_CLAVE = {_sin_prefijo(norm(b)): b for b in BARRIOS_CASCO_URBANO}


def barrio_canonico(valor):
    """'EL CENTRO', 'Bo. El Centro'... → 'Barrio El Centro'. None si está fuera
    del casco urbano (aldeas, caseríos, lotificaciones)."""
    return _BARRIOS_POR_CLAVE.get(_sin_prefijo(norm(valor)))


# --------------------------------------------------------------------------- #
# Clase de trabajo
# --------------------------------------------------------------------------- #
_CLASES = {
    'ENC': 'ENC', 'ENCUESTA': 'ENC',
    'VERIF': 'VERIF', 'VER': 'VERIF', 'VERIFICACION': 'VERIF',
    'ACCION': 'ACCION',
    'PLAN': 'PLAN',
    'TRATAMIENTO': 'TRATAMIENTO', 'TRAT': 'TRATAMIENTO',
    'FUM': 'FUM', 'FUMIGACION': 'FUM',
}


def clase_trabajo(valor):
    return _CLASES.get(norm(valor))


# --------------------------------------------------------------------------- #
# Conversión de celdas
# --------------------------------------------------------------------------- #
class ErrorCelda(ValueError):
    pass


def entero(valor, campo, requerido=False):
    """Entero >= 0. Vacío → None (o error si es requerido)."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if requerido:
            raise ErrorCelda(f'{campo}: vacío')
        return None
    if isinstance(valor, bool):
        raise ErrorCelda(f'{campo}: no es un número')
    if isinstance(valor, float):
        if not valor.is_integer():
            raise ErrorCelda(f'{campo}: no es entero')
        valor = int(valor)
    if isinstance(valor, str):
        texto = valor.strip()
        if not re.fullmatch(r'\d+(\.0+)?', texto):
            raise ErrorCelda(f'{campo}: no es un número entero')
        valor = int(float(texto))
    if not isinstance(valor, int):
        raise ErrorCelda(f'{campo}: no es un número')
    if valor < 0:
        raise ErrorCelda(f'{campo}: negativo')
    return valor


def decimal_opcional(valor):
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    try:
        return float(str(valor).replace(',', '.').replace('%', ''))
    except ValueError:
        return None


def fecha(valor, campo):
    """Acepta fecha de Excel, dd/mm/aaaa o aaaa-mm-dd. No acepta fechas futuras."""
    if isinstance(valor, datetime.datetime):
        f = valor.date()
    elif isinstance(valor, datetime.date):
        f = valor
    elif isinstance(valor, str) and valor.strip():
        texto = valor.strip()
        for formato in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y'):
            try:
                f = datetime.datetime.strptime(texto, formato).date()
                break
            except ValueError:
                continue
        else:
            raise ErrorCelda(f'{campo}: fecha no reconocida')
    else:
        raise ErrorCelda(f'{campo}: vacía')
    if f > datetime.date.today():
        raise ErrorCelda(f'{campo}: fecha futura')
    if f.year < 2000:
        raise ErrorCelda(f'{campo}: fecha fuera de rango')
    return f


def texto_corto(valor, campo, max_len=20, requerido=False):
    """Para MZ/CASA: texto corto; un número de Excel 12.0 se lee como '12'."""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    texto = '' if valor is None else str(valor).strip()
    if not texto:
        if requerido:
            raise ErrorCelda(f'{campo}: vacío')
        return ''
    if len(texto) > max_len:
        raise ErrorCelda(f'{campo}: más de {max_len} caracteres')
    return texto


# --------------------------------------------------------------------------- #
# Encabezados de tabla (una o dos filas, con celdas combinadas)
# --------------------------------------------------------------------------- #
_SUBENCABEZADOS = ('INSP', 'POS', 'ABAT', 'DESCHAT', 'FUMIG', 'TRAT')


def mapa_columnas(fila_grupo, fila_sub):
    """
    Construye {indice_columna: clave_normalizada}. Si `fila_sub` trae
    subencabezados (Insp./Pos./...), la clave es 'GRUPO SUB' arrastrando el
    grupo de las celdas combinadas; si no, es el texto de `fila_grupo`.
    """
    usa_sub = fila_sub is not None and any(
        norm(v).startswith(_SUBENCABEZADOS) for v in fila_sub)
    columnas = {}
    grupo_actual = ''
    for i, valor in enumerate(fila_grupo):
        g = norm(valor)
        s = norm(fila_sub[i]) if usa_sub and i < len(fila_sub) else ''
        if g:
            grupo_actual = g
        if s:
            columnas[i] = f'{grupo_actual} {s}'
        elif g:
            columnas[i] = g
    return columnas, usa_sub


def buscar_columna(columnas, exactas=(), prefijos=()):
    for i, clave in columnas.items():
        if clave in exactas or any(clave.startswith(p) for p in prefijos):
            return i
    return None


def buscar_fila(filas, condicion, limite=FILAS_A_REVISAR):
    for i, fila in enumerate(filas[:limite]):
        if condicion([norm(v) for v in fila]):
            return i
    return None


def es_fila_vacia(fila):
    return all(v is None or (isinstance(v, str) and not v.strip()) for v in fila)


def valor_etiqueta(filas, etiqueta, limite=FILAS_A_REVISAR):
    """
    Busca un dato de cabecera tipo 'LOCALIDAD: El Centro' o 'FECHA' | valor.
    Devuelve el valor crudo (sin normalizar) o None.
    """
    for fila in filas[:limite]:
        for i, celda in enumerate(fila):
            n = norm(celda)
            if not n.startswith(etiqueta):
                continue
            if isinstance(celda, str) and ':' in celda:
                resto = celda.split(':', 1)[1].strip()
                if resto:
                    return resto
            for siguiente in fila[i + 1:]:
                if siguiente is not None and str(siguiente).strip():
                    return siguiente
    return None


# --------------------------------------------------------------------------- #
# Resultado de la lectura
# --------------------------------------------------------------------------- #
@dataclass
class Rechazo:
    hoja: str
    fila: int  # número de fila de Excel (1 = primera)
    motivo: str


@dataclass
class Lectura:
    registros: list = field(default_factory=list)
    rechazos: list = field(default_factory=list)   # filas con error de validación
    omitidos: list = field(default_factory=list)   # fuera de alcance (no es error)
    avisos: list = field(default_factory=list)     # inconsistencias que no bloquean
    hojas_leidas: list = field(default_factory=list)
