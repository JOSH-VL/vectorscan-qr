"""
Pruebas de importar_formatos con Excel FICTICIOS (apps/inspecciones/importacion/prueba.py).
No usan datos reales. Corren contra la base de pruebas de Django.
"""
import io
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase, override_settings
from openpyxl import load_workbook

from apps.inspecciones.importacion import prueba
from apps.inspecciones.importacion.comun import barrio_canonico, clase_trabajo, entero, ErrorCelda
from apps.inspecciones.importacion.lectores import leer_a1, leer_consolidado, leer_encuestas
from apps.usuarios.models import Usuario
from apps.viviendas.models import Vivienda


class _ConArchivos:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dir = tempfile.mkdtemp(prefix='vsqr_prueba_')
        cls.rutas = prueba.generar_todo(cls.dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)
        super().tearDownClass()

    def libro(self, nombre):
        return load_workbook(self.rutas[nombre], read_only=True, data_only=True)


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
class ComunTest(SimpleTestCase):

    def test_barrios_del_casco_urbano(self):
        for variante in ['EL CENTRO', 'Bo. El Centro', 'barrio el centro', 'El Centro ']:
            self.assertEqual(barrio_canonico(variante), 'Barrio El Centro')
        self.assertEqual(barrio_canonico('EL JARDIN'), 'Barrio El Jardín')
        self.assertEqual(barrio_canonico('Col. Camilo Alvarado'), 'Barrio Camilo Alvarado')

    def test_fuera_del_casco_urbano(self):
        for fuera in ['ALDEA EL ROSARIO', 'Caserío X', 'Lotificación Y', '', None]:
            self.assertIsNone(barrio_canonico(fuera))

    def test_clase_trabajo(self):
        self.assertEqual(clase_trabajo('Verificación'), 'VERIF')
        self.assertEqual(clase_trabajo('enc'), 'ENC')
        self.assertIsNone(clase_trabajo('XYZ'))

    def test_entero(self):
        self.assertEqual(entero(3.0, 'x'), 3)
        self.assertEqual(entero(' 12 ', 'x'), 12)
        self.assertIsNone(entero(None, 'x'))
        for malo in [-1, 2.5, 'abc', True]:
            with self.assertRaises(ErrorCelda):
                entero(malo, 'x')


# --------------------------------------------------------------------------- #
# Lectores
# --------------------------------------------------------------------------- #
class LectoresTest(_ConArchivos, SimpleTestCase):

    def test_a1(self):
        lec = leer_a1(self.libro('prueba_A1_ENC.xlsx'))
        self.assertEqual(lec.hojas_leidas, ['ENC1', 'ENC2'])
        self.assertEqual(len(lec.registros), 6)
        self.assertEqual(len(lec.rechazos), 5)
        self.assertEqual(len(lec.omitidos), 1)   # hoja de aldea
        motivos = ' | '.join(r.motivo for r in lec.rechazos)
        self.assertIn('positivos (3) mayor que inspeccionados (1)', motivos)
        self.assertIn('CASA: vacío', motivos)
        self.assertIn('casa marcada negativa', motivos)
        self.assertIn('No. Orden 2 repetido', motivos)
        self.assertIn('HAB: negativo', motivos)

        r1 = lec.registros[0]
        self.assertEqual((r1['localidad'], r1['clase'], r1['correlativo']), ('Barrio El Centro', 'ENC', 1))
        self.assertEqual((r1['manzana'], r1['numero_casa']), ('3', '12'))
        self.assertEqual(r1['depositos'], {'PILAS': (2, 1), 'LLANTAS': (1, 0)})
        self.assertEqual((r1['num_depositos'], r1['depositos_positivos']), (3, 1))
        self.assertTrue(r1['casa_positiva'])
        enc2 = [r for r in lec.registros if r['hoja'] == 'ENC2']
        self.assertEqual({r['clase'] for r in enc2}, {'VERIF'})
        self.assertEqual(enc2[0]['localidad'], 'Barrio La Llovizna')

    def test_encuestas(self):
        lec = leer_encuestas(self.libro('prueba_encuestas_2026.xlsx'))
        self.assertEqual(lec.hojas_leidas, ['2026'])   # EST. SALA se ignora
        self.assertEqual(len(lec.registros), 4)
        self.assertEqual(len(lec.rechazos), 1)
        self.assertEqual(len(lec.omitidos), 1)
        self.assertTrue(any('IC en la hoja 9.0' in a for a in lec.avisos))
        llovizna = lec.registros[1]
        self.assertEqual((llovizna['ic'], llovizna['ib'], llovizna['ir']), (30.0, 46.7, 11.7))

    def test_consolidado(self):
        lec = leer_consolidado(self.libro('prueba_consolidado_2026.xlsx'), 2026)
        self.assertEqual(lec.hojas_leidas, ['SEPTIEMBRE', 'OCTUBRE'])   # INF se ignora
        self.assertEqual(len(lec.registros), 4)
        self.assertEqual(len(lec.rechazos), 2)   # pos > insp, sin clase
        self.assertEqual(len(lec.omitidos), 1)
        fum = [r for r in lec.registros if r['clase'] == 'FUM'][0]
        self.assertEqual((fum['localidad'], fum['mes'], fum['fumigadas']), ('Barrio La Llovizna', 9, 30))


# --------------------------------------------------------------------------- #
# Comando y candados
# --------------------------------------------------------------------------- #
@override_settings(DEBUG=False)
class ComandoTest(_ConArchivos, TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tecnico = Usuario.objects.create_user(username='tecnico_real', password='x')

    def correr(self, nombre, tipo, *extra):
        salida = io.StringIO()
        args = ['--archivo', self.rutas[nombre], '--tipo', tipo, *extra]
        if tipo == 'a1' and '--usuario' not in extra:
            args += ['--usuario', 'tecnico_real']
        call_command('importar_formatos', *args, stdout=salida)
        return salida.getvalue()

    def test_candado_debug(self):
        with override_settings(DEBUG=True):
            with self.assertRaisesMessage(CommandError, 'DEBUG=False'):
                self.correr('prueba_A1_ENC.xlsx', 'a1', '--dry-run')

    def test_candado_datos_demo(self):
        media = tempfile.mkdtemp()
        try:
            with override_settings(MEDIA_ROOT=media):
                Vivienda.objects.create(direccion='x', responsable_familia='x',
                                        registrado_por=self.tecnico, es_demo=True)
            with self.assertRaisesMessage(CommandError, 'es_demo=True'):
                self.correr('prueba_A1_ENC.xlsx', 'a1', '--dry-run')
        finally:
            shutil.rmtree(media, ignore_errors=True)

    def test_rechaza_ficha_epidemiologica_sin_mostrar_contenido(self):
        with self.assertRaises(CommandError) as ctx:
            self.correr('prueba_RECHAZO_ficha.xlsx', 'a1', '--dry-run')
        mensaje = str(ctx.exception)
        self.assertIn('Decreto 57-2008', mensaje)
        self.assertIn('ficha epidemiológica', mensaje)
        self.assertNotIn('PERSONA FICTICIA', mensaje)

    def test_rechaza_mht_por_contenido(self):
        with self.assertRaisesMessage(CommandError, 'formato MHT'):
            self.correr('prueba_RECHAZO_control.xlsx', 'consolidado', '--dry-run')

    def test_rechaza_por_nombre_de_archivo(self):
        ruta = Path(self.dir) / 'control_malaria_2026.xlsx'
        shutil.copy(self.rutas['prueba_consolidado_2026.xlsx'], ruta)
        with self.assertRaisesMessage(CommandError, 'nombre del archivo'):
            call_command('importar_formatos', '--archivo', str(ruta), '--tipo',
                         'consolidado', '--dry-run', stdout=io.StringIO())

    def test_rechaza_archivo_dentro_del_repo(self):
        with tempfile.NamedTemporaryFile(dir=settings.BASE_DIR, suffix='.xlsx') as tmp:
            with self.assertRaisesMessage(CommandError, 'dentro del repositorio'):
                call_command('importar_formatos', '--archivo', tmp.name, '--tipo',
                             'consolidado', '--dry-run', stdout=io.StringIO())

    def test_rechaza_xls(self):
        ruta = Path(self.dir) / 'viejo.xls'
        ruta.write_bytes(b'x')
        with self.assertRaisesMessage(CommandError, '.xls'):
            call_command('importar_formatos', '--archivo', str(ruta), '--tipo', 'a1',
                         '--usuario', 'tecnico_real', '--dry-run', stdout=io.StringIO())

    def test_tipo_equivocado(self):
        with self.assertRaisesMessage(CommandError, 'no corresponde'):
            self.correr('prueba_A1_ENC.xlsx', 'consolidado', '--dry-run')

    def test_a1_requiere_usuario_activo(self):
        with self.assertRaisesMessage(CommandError, 'usuario activo'):
            self.correr('prueba_A1_ENC.xlsx', 'a1', '--usuario', 'no_existe', '--dry-run')

    def test_dry_run_reporta_y_no_escribe(self):
        salida = self.correr('prueba_A1_ENC.xlsx', 'a1', '--dry-run')
        self.assertIn('Filas válidas: 6', salida)
        self.assertIn('Filas rechazadas: 5', salida)
        self.assertIn('[ENC1] fila', salida)
        self.assertIn('no se escribió nada', salida)
        self.assertEqual(Vivienda.objects.count(), 0)

    def test_consolidado_deduce_anio_del_nombre(self):
        salida = self.correr('prueba_consolidado_2026.xlsx', 'consolidado', '--dry-run')
        self.assertIn('Filas válidas: 4', salida)
