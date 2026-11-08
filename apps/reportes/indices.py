"""
Índices entomológicos por ZONA — VectorScan QR (Fase 2)

Son indicadores AGREGADOS por zona y periodo (mes). No tienen relación con el
riesgo por VIVIENDA (Alto/Medio/Bajo) que calcula Inspeccion.clasificar_riesgo();
esa lógica no se toca ni se usa aquí.

Fórmulas (hoja ENCUESTAS Y VERIFICACIONES, MSPAS):
  - Índice de Casas (I.C.)       = casas positivas ÷ casas inspeccionadas × 100
  - Índice de Breteau (I.B.)     = recipientes positivos ÷ casas inspeccionadas × 100
  - Índice de Recipientes (I.R.) = recipientes positivos ÷ recipientes inspeccionados × 100

Criterios de conteo:
  - Una casa se cuenta una sola vez por mes: si tuvo varias inspecciones en el
    mes, se usa la última.
  - Casa positiva = esa inspección tiene larvas (presencia_larvas) o al menos
    un depósito positivo.
  - Recipientes = num_depositos / depositos_positivos de la inspección (los
    totales; el desglose por tipo de DepositoInspeccion debe cuadrar con ellos).
"""
from decimal import Decimal, ROUND_HALF_UP

# --------------------------------------------------------------------------- #
# Estratificación por Índice de Casas
#
# Cortes DEDUCIDOS de la hoja "EST. SALA" del Excel oficial MSPAS 2026
# (48.1/30/26 = ALTO; 24/20.3/14.8/13.7 = MEDIANO; 5.5/3.7/0 = BAJO).
# PENDIENTES DE CONFIRMACIÓN VERBAL CON LA OFICINISTA del Centro de Salud.
# No presentarlos como oficiales hasta confirmarlos.
#
# Cada fila es (límite inferior inclusivo, estrato, color Bootstrap), de mayor
# a menor. Para cambiar los cortes, editar solo esta tabla.
# --------------------------------------------------------------------------- #
ESTRATOS_INDICE_CASAS = [
    (Decimal('25'), 'ALTO', 'danger'),
    (Decimal('10'), 'MEDIANO', 'warning'),
    (Decimal('0'), 'BAJO', 'success'),
]
CORTES_CONFIRMADOS = False


def _pct(numerador, denominador):
    """Porcentaje con 1 decimal; None si el denominador es 0."""
    if not denominador:
        return None
    valor = Decimal(numerador) * 100 / Decimal(denominador)
    return valor.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def estrato_indice_casas(ic):
    """Devuelve (estrato, color) para un I.C.; (None, 'secondary') si no hay dato."""
    if ic is None:
        return None, 'secondary'
    for limite, estrato, color in ESTRATOS_INDICE_CASAS:
        if ic >= limite:
            return estrato, color
    return None, 'secondary'


def calcular_indices(casas_insp, casas_pos, recip_insp, recip_pos):
    """Calcula I.C., I.B., I.R. y el estrato a partir de los conteos."""
    ic = _pct(casas_pos, casas_insp)
    estrato, color = estrato_indice_casas(ic)
    return {
        'casas_insp': casas_insp,
        'casas_pos': casas_pos,
        'recip_insp': recip_insp,
        'recip_pos': recip_pos,
        'ic': ic,
        'ib': _pct(recip_pos, casas_insp),
        'ir': _pct(recip_pos, recip_insp),
        'estrato': estrato,
        'color': color,
    }


def indices_por_zona(inspecciones, zonas):
    """
    `inspecciones`: iterable de Inspeccion activas del periodo, ordenadas de la
    más reciente a la más antigua (con vivienda cargada).
    `zonas`: lista de nombres de zona a reportar (aparecen aunque tengan 0).

    Retorna (filas_por_zona, fila_total).
    """
    # Última inspección del periodo por vivienda.
    ultima_por_vivienda = {}
    for insp in inspecciones:
        ultima_por_vivienda.setdefault(insp.vivienda_id, insp)

    conteos = {z: [0, 0, 0, 0] for z in zonas}
    for insp in ultima_por_vivienda.values():
        c = conteos.setdefault(insp.vivienda.zona, [0, 0, 0, 0])
        c[0] += 1
        if insp.presencia_larvas or insp.depositos_positivos > 0:
            c[1] += 1
        c[2] += insp.num_depositos
        c[3] += insp.depositos_positivos

    filas = [dict(zona=z, **calcular_indices(*c)) for z, c in conteos.items()]
    totales = [sum(c[i] for c in conteos.values()) for i in range(4)]
    total = dict(zona='Total casco urbano', **calcular_indices(*totales))
    return filas, total
