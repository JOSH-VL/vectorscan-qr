from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from .indices import calcular_indices, estrato_indice_casas, indices_por_zona


class EstratoIndiceCasasTest(SimpleTestCase):
    """Cortes verificados contra la hoja EST. SALA (MSPAS 2026)."""

    def test_valores_de_la_hoja_est_sala(self):
        for ic in ['48.1', '30', '26', '25']:
            self.assertEqual(estrato_indice_casas(Decimal(ic))[0], 'ALTO', ic)
        for ic in ['24', '20.3', '14.8', '13.7', '10']:
            self.assertEqual(estrato_indice_casas(Decimal(ic))[0], 'MEDIANO', ic)
        for ic in ['9.9', '5.5', '3.7', '0']:
            self.assertEqual(estrato_indice_casas(Decimal(ic))[0], 'BAJO', ic)

    def test_sin_dato(self):
        self.assertEqual(estrato_indice_casas(None), (None, 'secondary'))


class CalcularIndicesTest(SimpleTestCase):

    def test_formulas(self):
        r = calcular_indices(casas_insp=20, casas_pos=5, recip_insp=80, recip_pos=8)
        self.assertEqual(r['ic'], Decimal('25.0'))   # 5/20
        self.assertEqual(r['ib'], Decimal('40.0'))   # 8/20
        self.assertEqual(r['ir'], Decimal('10.0'))   # 8/80
        self.assertEqual(r['estrato'], 'ALTO')

    def test_redondeo_un_decimal(self):
        r = calcular_indices(3, 1, 7, 1)
        self.assertEqual(r['ic'], Decimal('33.3'))
        self.assertEqual(r['ir'], Decimal('14.3'))

    def test_division_entre_cero(self):
        r = calcular_indices(0, 0, 0, 0)
        self.assertIsNone(r['ic'])
        self.assertIsNone(r['ib'])
        self.assertIsNone(r['ir'])
        self.assertIsNone(r['estrato'])


def _insp(vivienda_id, zona, larvas, num, pos):
    return SimpleNamespace(
        vivienda_id=vivienda_id, vivienda=SimpleNamespace(zona=zona),
        presencia_larvas=larvas, num_depositos=num, depositos_positivos=pos)


class IndicesPorZonaTest(SimpleTestCase):

    def test_casa_cuenta_una_vez_con_su_ultima_inspeccion(self):
        # Ordenadas de la más reciente a la más antigua.
        inspecciones = [
            _insp(1, 'Barrio El Centro', False, 4, 0),  # última de la casa 1
            _insp(1, 'Barrio El Centro', True, 5, 2),   # anterior, se ignora
            _insp(2, 'Barrio El Centro', True, 6, 3),
        ]
        filas, total = indices_por_zona(
            inspecciones, ['Barrio El Centro', 'Barrio La Linterna'])
        centro = filas[0]
        self.assertEqual((centro['casas_insp'], centro['casas_pos']), (2, 1))
        self.assertEqual((centro['recip_insp'], centro['recip_pos']), (10, 3))
        self.assertEqual(centro['ic'], Decimal('50.0'))
        # La zona sin inspecciones aparece en cero, sin estrato.
        self.assertEqual(filas[1]['casas_insp'], 0)
        self.assertIsNone(filas[1]['estrato'])
        self.assertEqual(total['casas_insp'], 2)


def _insp_completa(vivienda_id, zona, clase, larvas=False, num=4, pos=0, hab=5,
                   educo=True, larvicida=False, elimino=False):
    return SimpleNamespace(
        vivienda_id=vivienda_id, clase_trabajo=clase,
        vivienda=SimpleNamespace(zona=zona, num_habitantes=hab),
        presencia_larvas=larvas, num_depositos=num, depositos_positivos=pos,
        educo_residente=educo, aplico_larvicida=larvicida, elimino_criaderos=elimino)


class FilasConsolidadoTest(SimpleTestCase):

    def test_agrupa_por_localidad_y_clase(self):
        from .exportaciones import filas_consolidado
        inspecciones = [  # de la más reciente a la más antigua
            _insp_completa(1, 'Barrio El Centro', 'ENC', larvas=True, pos=2, larvicida=True),
            _insp_completa(1, 'Barrio El Centro', 'ENC'),            # anterior: se ignora
            _insp_completa(1, 'Barrio El Centro', 'VERIF', hab=5),   # otra clase: cuenta
            _insp_completa(2, 'Barrio El Centro', 'ENC', hab=3, educo=False, elimino=True),
            _insp_completa(3, 'Barrio El Campo', 'FUM', num=0),
        ]
        filas = {(f['localidad'], f['clase']): f for f in filas_consolidado(inspecciones)}
        self.assertEqual(len(filas), 3)

        enc = filas[('Barrio El Centro', 'ENC')]
        self.assertEqual((enc['viv_insp'], enc['viv_pos']), (2, 1))
        self.assertEqual(enc['personas'], 5)          # la casa 2 no fue orientada
        self.assertEqual((enc['abatizadas'], enc['deschatarrizadas']), (1, 1))
        self.assertEqual((enc['dep_insp'], enc['dep_pos']), (8, 2))

        self.assertEqual(filas[('Barrio El Centro', 'VERIF')]['viv_insp'], 1)
        self.assertEqual(filas[('Barrio El Campo', 'FUM')]['fumigadas'], 1)
