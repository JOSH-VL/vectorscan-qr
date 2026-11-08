"""
generar_excel_prueba — crea Excel con datos FICTICIOS que imitan los formatos
MSPAS, para probar importar_formatos sin datos reales.

    python manage.py generar_excel_prueba --destino /tmp/excel_prueba
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.inspecciones.importacion.prueba import generar_todo


class Command(BaseCommand):
    help = 'Genera Excel de prueba con datos ficticios (estructura MSPAS).'

    def add_arguments(self, parser):
        parser.add_argument('--destino', default='/tmp/excel_prueba',
                            help='Carpeta de salida, fuera del repositorio.')

    def handle(self, *args, **opts):
        destino = Path(opts['destino']).expanduser().resolve()
        repo = Path(settings.BASE_DIR).resolve()
        if destino == repo or repo in destino.parents:
            raise CommandError('Elegí una carpeta fuera del repositorio.')
        for nombre, ruta in generar_todo(destino).items():
            self.stdout.write(f'  {ruta}')
        self.stdout.write(self.style.SUCCESS('Excel de prueba generados (datos ficticios).'))
