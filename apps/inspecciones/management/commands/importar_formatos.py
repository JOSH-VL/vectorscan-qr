"""
importar_formatos — carga de datos REALES de vigilancia entomológica (MSPAS).

    python manage.py importar_formatos --archivo /ruta/fuera/del/repo.xlsx \
        --tipo a1|encuestas|consolidado [--usuario USERNAME] [--clase ENC]
        [--anio 2026] [--dry-run]

Candados (en este orden; cualquiera aborta sin escribir nada):
  1. DEBUG=True → aborta. Es solo para producción (seed_piloto es solo demo).
  2. Hay viviendas o inspecciones con es_demo=True → aborta. Demo y real no
     se mezclan; hay que limpiar los datos demo primero.
  3. La ruta debe venir por argumento, existir, ser .xlsx/.xlsm y estar FUERA
     del repositorio (los Excel reales nunca se versionan).
  4. Fichas epidemiológicas o formato MHT → aborta (Decreto 57-2008). Se revisan
     nombre del archivo, nombres de hoja y encabezados, antes de leer las filas.
  5. Solo las 3 fuentes de vigilancia entomológica; si la estructura no
     corresponde al --tipo, aborta.

Luego valida fila por fila: las filas inválidas se reportan (hoja, fila, motivo)
y el resto del lote sigue. Las localidades fuera del casco urbano se omiten.
Los mensajes nunca repiten el contenido de celdas de texto.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openpyxl import load_workbook

from apps.inspecciones.importacion.comun import detectar_datos_sensibles
from apps.inspecciones.importacion.lectores import (
    ErrorAnio, ErrorEstructura, detectar_anio, leer_a1, leer_consolidado, leer_encuestas,
)
from apps.inspecciones.models import Inspeccion
from apps.usuarios.models import Usuario
from apps.viviendas.models import Vivienda

TIPOS = {
    'a1': 'Formulario A-1 (hoja ENC1)',
    'encuestas': 'Encuestas y verificaciones',
    'consolidado': 'Consolidado mensual de Vigilancia y Control del Dengue',
}
EXTENSIONES = ('.xlsx', '.xlsm')
MAX_RECHAZOS_EN_PANTALLA = 200


class Command(BaseCommand):
    help = ('Importa formatos MSPAS de vigilancia entomológica (A-1, encuestas, '
            'consolidado). Solo producción (DEBUG=False).')

    def add_arguments(self, parser):
        parser.add_argument('--archivo', required=True,
                            help='Ruta al .xlsx, fuera del repositorio.')
        parser.add_argument('--tipo', required=True, choices=sorted(TIPOS))
        parser.add_argument('--usuario',
                            help='Usuario activo responsable de las inspecciones (obligatorio para a1).')
        parser.add_argument('--clase', default='ENC',
                            choices=[c for c, _ in Inspeccion.CLASE_TRABAJO],
                            help='Clase de trabajo si el archivo no la indica (por defecto ENC).')
        parser.add_argument('--anio', type=int,
                            help='Año del consolidado si no se puede deducir del archivo.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo valida y reporta; no escribe nada.')

    # ------------------------------------------------------------------ #
    def handle(self, *args, **opts):
        self._candado_entorno()
        self._candado_demo()
        ruta = self._candado_ruta(opts['archivo'])
        usuario = self._usuario(opts) if opts['tipo'] == 'a1' else None

        try:
            libro = load_workbook(ruta, read_only=True, data_only=True)
        except Exception as e:  # archivo dañado, protegido, no es Excel
            raise CommandError(f'No se pudo abrir el archivo como Excel ({type(e).__name__}). Abortado.')

        try:
            sensible = detectar_datos_sensibles(ruta.name, libro)
            if sensible:
                raise CommandError(
                    f'RECHAZADO: el archivo parece contener {sensible}. '
                    'VectorScan QR solo importa vigilancia entomológica. Fichas '
                    'epidemiológicas y formato MHT contienen datos sensibles de '
                    'pacientes (Decreto 57-2008) y no se importan. No se leyó ninguna fila.')
            lectura = self._leer(libro, ruta, opts)
        finally:
            libro.close()

        self._reporte(lectura, opts)

        if opts['dry_run']:
            self.stdout.write(self.style.WARNING('\n--dry-run: no se escribió nada.'))
            return
        if not lectura.registros:
            self.stdout.write(self.style.WARNING('\nNo hay registros válidos; no se escribió nada.'))
            return
        self._escribir(lectura, opts, usuario)

    # ------------------------------------------------------------------ #
    # Candados
    # ------------------------------------------------------------------ #
    def _candado_entorno(self):
        if settings.DEBUG:
            raise CommandError(
                'importar_formatos solo corre con DEBUG=False (producción). Con '
                'DEBUG=True el entorno es de demostración (seed_piloto). Abortado.')

    def _candado_demo(self):
        n_viv = Vivienda.objects.filter(es_demo=True).count()
        n_insp = Inspeccion.objects.filter(es_demo=True).count()
        if n_viv or n_insp:
            raise CommandError(
                f'Hay datos de demostración sin limpiar ({n_viv} viviendas y '
                f'{n_insp} inspecciones con es_demo=True). Datos demo y reales no '
                'se mezclan: eliminá los datos demo antes de importar. Abortado.')

    def _candado_ruta(self, archivo):
        ruta = Path(archivo).expanduser().resolve()
        if not ruta.is_file():
            raise CommandError(f'No existe el archivo: {ruta}')
        if ruta.suffix.lower() == '.xls':
            raise CommandError(
                'Formato .xls (Excel 97-2003) no soportado. Abrilo en Excel y '
                'guardalo como .xlsx. Abortado.')
        if ruta.suffix.lower() not in EXTENSIONES:
            raise CommandError(f'Se esperaba un archivo .xlsx; se recibió "{ruta.suffix}". Abortado.')
        repo = Path(settings.BASE_DIR).resolve()
        if ruta == repo or repo in ruta.parents:
            raise CommandError(
                'El archivo está dentro del repositorio. Los Excel con datos reales '
                'no deben estar en la carpeta del proyecto. Copialo fuera (p. ej. '
                '"docker compose cp archivo.xlsx web:/tmp/") y pasá esa ruta. Abortado.')
        return ruta

    def _usuario(self, opts):
        if not opts['usuario']:
            raise CommandError('--usuario es obligatorio para --tipo a1 (técnico responsable).')
        u = Usuario.objects.filter(username=opts['usuario'], estado='Activo', is_active=True).first()
        if u is None:
            raise CommandError(f'No existe un usuario activo "{opts["usuario"]}". Abortado.')
        return u

    # ------------------------------------------------------------------ #
    # Lectura y reporte
    # ------------------------------------------------------------------ #
    def _leer(self, libro, ruta, opts):
        try:
            if opts['tipo'] == 'a1':
                return leer_a1(libro, opts['clase'])
            if opts['tipo'] == 'encuestas':
                return leer_encuestas(libro, opts['clase'])
            return leer_consolidado(libro, opts['anio'] or detectar_anio(ruta.name, libro))
        except ErrorAnio as e:
            raise CommandError(str(e))
        except ErrorEstructura as e:
            raise CommandError(f'El archivo no corresponde a {TIPOS[opts["tipo"]]}: {e} Abortado.')

    def _reporte(self, lectura, opts):
        self.stdout.write(self.style.SUCCESS(f'=== importar_formatos — {TIPOS[opts["tipo"]]} ==='))
        self.stdout.write(f'Hojas leídas: {", ".join(lectura.hojas_leidas) or "ninguna"}')
        self.stdout.write(f'Filas válidas: {len(lectura.registros)}')
        self.stdout.write(f'Filas rechazadas: {len(lectura.rechazos)}')
        self.stdout.write(f'Omitidas (fuera del casco urbano): {len(lectura.omitidos)}')
        if lectura.rechazos:
            self.stdout.write(self.style.ERROR('\nRechazadas (no se importan; el resto del lote sigue):'))
            for r in lectura.rechazos[:MAX_RECHAZOS_EN_PANTALLA]:
                self.stdout.write(f'  [{r.hoja}] fila {r.fila}: {r.motivo}')
            if len(lectura.rechazos) > MAX_RECHAZOS_EN_PANTALLA:
                self.stdout.write(f'  ... y {len(lectura.rechazos) - MAX_RECHAZOS_EN_PANTALLA} más.')
        if lectura.omitidos:
            self.stdout.write(self.style.WARNING('\nOmitidas por delimitación (solo los 6 barrios del casco urbano):'))
            for r in lectura.omitidos:
                self.stdout.write(f'  [{r.hoja}] fila {r.fila}: {r.motivo}')
        if lectura.avisos:
            self.stdout.write(self.style.WARNING('\nAvisos:'))
            for a in lectura.avisos:
                self.stdout.write(f'  {a}')

    # ------------------------------------------------------------------ #
    # Escritura
    # ------------------------------------------------------------------ #
    def _escribir(self, lectura, opts, usuario):
        # PENDIENTE DE AUTORIZACIÓN: guardar requiere cambios de modelo
        # (clave de importación en Inspeccion y tablas para encuestas y
        # consolidado). Hasta que se aprueben y se migren, solo --dry-run.
        raise CommandError(
            'La escritura todavía no está habilitada (pendiente de los cambios de '
            'modelo). Usá --dry-run para validar el archivo.')
