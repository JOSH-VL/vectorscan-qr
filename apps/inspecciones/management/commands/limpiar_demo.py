"""
limpiar_demo — elimina los datos de demostración (es_demo=True) para dejar la
base lista para importar_formatos.

    python manage.py limpiar_demo               # muestra qué borra y pide escribir BORRAR
    python manage.py limpiar_demo --confirmar   # sin pregunta (para scripts)

Excepción documentada a la convención de borrado lógico: los datos demo son
ficticios y deben desaparecer físicamente para que no se mezclen con datos
reales (lo mismo hace seed_piloto al re-sembrar).

Borra SOLO lo marcado con es_demo=True: inspecciones demo (con su desglose de
depósitos e histórico, por CASCADE) y viviendas demo (con su histórico y su PNG
de QR). No toca usuarios ni ningún registro real. Si una inspección real apunta
a una vivienda demo, aborta sin borrar nada.
"""
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.inspecciones.models import Inspeccion
from apps.viviendas.models import Vivienda

PALABRA = 'BORRAR'


class Command(BaseCommand):
    help = 'Elimina viviendas e inspecciones con es_demo=True (pide confirmación).'

    def add_arguments(self, parser):
        parser.add_argument('--confirmar', action='store_true',
                            help=f'No preguntar (equivale a escribir {PALABRA}).')

    def handle(self, *args, **opts):
        viviendas = Vivienda.objects.filter(es_demo=True)
        inspecciones = Inspeccion.objects.filter(es_demo=True)
        n_viv, n_insp = viviendas.count(), inspecciones.count()

        if not n_viv and not n_insp:
            self.stdout.write(self.style.SUCCESS('No hay datos de demostración. Nada que borrar.'))
            return

        mezcladas = Inspeccion.objects.filter(vivienda__es_demo=True, es_demo=False).count()
        if mezcladas:
            raise CommandError(
                f'{mezcladas} inspección(es) REAL(es) apuntan a viviendas demo. No se '
                'borra nada: revisalas a mano antes de limpiar. Abortado.')

        self.stdout.write(f'Se borrarán: {n_viv} viviendas y {n_insp} inspecciones con es_demo=True')
        self.stdout.write('(con su histórico, desglose de depósitos y PNG de QR). '
                          'Usuarios y datos reales no se tocan.')
        if not opts['confirmar']:
            respuesta = input(f'Escribí {PALABRA} para confirmar: ')
            if respuesta.strip() != PALABRA:
                self.stdout.write(self.style.WARNING('Cancelado. No se borró nada.'))
                return

        pngs = [v.imagen_qr.path for v in viviendas if v.imagen_qr]
        with transaction.atomic():
            inspecciones.delete()
            viviendas.delete()

        # Los PNG se borran solo si la transacción se confirmó.
        for ruta in pngs:
            try:
                if os.path.isfile(ruta):
                    os.remove(ruta)
            except OSError:
                pass

        self.stdout.write(self.style.SUCCESS(
            f'Listo: {n_viv} viviendas y {n_insp} inspecciones demo eliminadas.'))
        self.stdout.write('Los usuarios del piloto (oficinista, tecnico1, tecnico2, '
                          'tecnico_inactivo) siguen existiendo; desactivalos si no se usan.')
