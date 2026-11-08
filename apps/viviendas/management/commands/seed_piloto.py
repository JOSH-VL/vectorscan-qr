"""
Comando de datos ficticios para capturas del Capítulo VI — VectorScan QR.

Siembra el piloto académico (usuarios, zonas del casco urbano, viviendas con QR,
inspecciones y auditoría) usando los modelos TAL COMO ESTÁN. No crea migraciones,
no modifica modelos, no toca vistas ni templates. Toda la clasificación de riesgo la
calcula el propio `Inspeccion.save()`; aquí solo se siembran los hallazgos.

Uso (dentro de Docker):
    docker compose exec web python manage.py seed_piloto

Reglas de seguridad:
- Solo corre con DEBUG=True (entorno demo). Si DEBUG=False, aborta.
- Es idempotente: limpia lo que sembró en corridas anteriores (sus propios usuarios
  y las viviendas/inspecciones que ellos registraron) y vuelve a sembrar. No toca
  datos creados a mano bajo el superusuario 'admin'.
"""
import datetime
import os
import random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.usuarios.models import Rol, Usuario, UsuarioHistorico
from apps.viviendas.models import Vivienda, ViviendaHistorico
from apps.inspecciones.models import Inspeccion, InspeccionHistorico


# --- Marcas de idempotencia -------------------------------------------------
# Usuarios que crea (y por tanto administra) este comando. 'admin' NO está acá:
# es el superusuario y no se borra; solo se le ajustan nombre/rol/clave.
SEED_USERNAMES = ['oficinista', 'tecnico1', 'tecnico2', 'tecnico_inactivo']
SHARED_PASSWORD = 'vectorscan2026'

SEMILLA_RNG = 2026  # determinismo entre corridas

# --- Catálogo de zonas: casco urbano de San Felipe, Retalhuleu --------------
# Solo los seis barrios del casco urbano. Nada de aldeas/caseríos/lotificaciones.
BARRIOS = [
    'Barrio El Centro',
    'Barrio La Llovizna',
    'Barrio El Campo',
    'Barrio El Jardín',
    'Barrio Camilo Alvarado',
    'Barrio La Linterna',
]

# --- Pools para datos realistas pero ficticios ------------------------------
APELLIDOS = ['De León', 'Tzoc', 'Ixcoy', 'Mangandí', 'Sontay', 'Tiguilá',
             'Chávez', 'Barrios', 'Solís', 'Ramírez', 'Coché', 'Say',
             'Mejía', 'Quiroa', 'López', 'Gómez', 'Pérez', 'Morales']
NOMBRES = ['María', 'José', 'Juana', 'Pedro', 'Ana', 'Carlos', 'Rosa', 'Luis',
           'Marta', 'Francisco', 'Catarina', 'Manuel', 'Lucía', 'Mario',
           'Elena', 'Byron', 'Dora', 'Edgar', 'Floridalma', 'Hugo', 'Ingrid',
           'Walter', 'Yolanda', 'Otoniel', 'Silvia', 'Diego']

REFERENCIAS = [
    'Frente a la cancha polideportiva',
    'A media cuadra de la escuela oficial',
    'Contiguo a la tienda La Bendición',
    'Cerca del puente El Zarco',
    'Atrás del mercado municipal',
    'Portón negro, casa de dos niveles',
    'Casa esquinera color celeste',
    'A la par de la iglesia evangélica',
    'Sobre calle principal adoquinada',
    'Frente al tanque de agua del barrio',
]

OBS = {
    'Alto': ['Pila sin tapadera con larvas',
             'Toneles destapados con larvas de Aedes',
             'Llantas con agua estancada y larvas',
             'Floreros con larvas en patio trasero',
             'Larvas en barril de recolección de lluvia'],
    'Medio': ['Pila con agua estancada sin tapadera',
              'Toneles con agua acumulada, sin larvas visibles',
              'Recipientes potenciales en patio',
              'Llantas acumuladas con riesgo de criadero',
              'Cubetas destapadas en área de lavado'],
    'Bajo': ['Depósitos tapados y limpios',
             'Patio ordenado, sin criaderos',
             'Pila con tapadera y cloro aplicado',
             'Sin recipientes con agua estancada',
             'Vivienda sin condiciones de riesgo'],
}


class Command(BaseCommand):
    help = 'Siembra datos ficticios del piloto para las capturas del Capítulo VI.'

    def handle(self, *args, **options):
        # --- Guard de entorno: demo únicamente ---
        if not settings.DEBUG:
            raise CommandError(
                'seed_piloto solo corre con DEBUG=True (entorno demo). '
                'Con DEBUG=False use importar_formatos con datos reales. Abortado.'
            )

        rng = random.Random(SEMILLA_RNG)
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n=== seed_piloto — datos ficticios para el Capítulo VI ===\n'))

        with transaction.atomic():
            self._limpiar()
            roles = self._roles()
            usuarios = self._usuarios(roles)
            viviendas = self._viviendas(usuarios, rng)
            self._inspecciones(viviendas, usuarios, rng)

        self._resumen(usuarios)

    # ------------------------------------------------------------------ #
    # Limpieza idempotente
    # ------------------------------------------------------------------ #
    def _limpiar(self):
        """Borra lo que sembró este comando en corridas anteriores."""
        usuarios_seed = Usuario.objects.filter(username__in=SEED_USERNAMES)

        # Viviendas sembradas = marcadas es_demo, más las registradas por los
        # usuarios-semilla (cubre siembras anteriores a que existiera es_demo).
        viviendas_seed = Vivienda.objects.filter(
            Q(es_demo=True) | Q(registrado_por__in=usuarios_seed))

        # Borrar los PNG de QR en disco para no dejar huérfanos en media/.
        for v in viviendas_seed:
            if v.imagen_qr:
                try:
                    if os.path.isfile(v.imagen_qr.path):
                        os.remove(v.imagen_qr.path)
                except (ValueError, OSError):
                    pass

        # Inspecciones de esas viviendas (InspeccionHistorico cae por CASCADE).
        n_insp = Inspeccion.objects.filter(vivienda__in=viviendas_seed).count()
        Inspeccion.objects.filter(vivienda__in=viviendas_seed).delete()

        # Viviendas (ViviendaHistorico cae por CASCADE).
        n_viv = viviendas_seed.count()
        viviendas_seed.delete()

        # Usuarios-semilla (su UsuarioHistorico cae por CASCADE; las referencias
        # usuario_cambio quedan en NULL por SET_NULL).
        n_usr = usuarios_seed.count()
        usuarios_seed.delete()

        if n_usr or n_viv or n_insp:
            self.stdout.write(
                f'  Limpieza previa: {n_usr} usuarios, {n_viv} viviendas, '
                f'{n_insp} inspecciones eliminados.')
        else:
            self.stdout.write('  Sin datos previos del seed. Primera siembra.')

    # ------------------------------------------------------------------ #
    # Roles y usuarios
    # ------------------------------------------------------------------ #
    def _roles(self):
        roles = {}
        defaults = {
            'admin': 'Acceso completo a todos los módulos del sistema',
            'oficinista': 'Gestión de viviendas, reportes y exportaciones',
            'tecnico': 'Registro de inspecciones desde campo',
        }
        for nombre, desc in defaults.items():
            rol, _ = Rol.objects.get_or_create(
                nombre=nombre, defaults={'descripcion': desc})
            roles[nombre] = rol
        return roles

    def _usuarios(self, roles):
        """Los 4 del piloto + 1 inactivo para evidenciar la eliminación lógica."""
        # admin: ya existe como superusuario; se le ajusta identidad del piloto.
        admin = Usuario.objects.filter(username='admin').first()
        if admin is None:
            admin = Usuario.objects.create_superuser(
                username='admin', password=SHARED_PASSWORD,
                nombre_completo='Josué Valiente', rol=roles['admin'],
                estado='Activo')
        else:
            admin.nombre_completo = 'Josué Valiente'
            admin.rol = roles['admin']
            admin.estado = 'Activo'
            admin.is_active = True
            admin.is_staff = True
            admin.is_superuser = True
            admin.set_password(SHARED_PASSWORD)
            admin.save()
        # Historial de creación de admin: una sola vez (idempotente).
        if not UsuarioHistorico.objects.filter(
                usuario_original=admin, tipo_operacion='INSERT').exists():
            self._hist_usuario(admin, admin, 'INSERT', dias=75)

        def crear(username, nombre, rol_key, estado='Activo'):
            u = Usuario.objects.create_user(
                username=username, password=SHARED_PASSWORD,
                nombre_completo=nombre, rol=roles[rol_key], estado=estado)
            u.is_staff = False
            u.is_superuser = False
            u.is_active = (estado == 'Activo')
            u.save()
            return u

        oficinista = crear('oficinista', 'Liz Mejía Quiroa', 'oficinista')
        tecnico1 = crear('tecnico1', 'Porfirio López Valiente', 'tecnico')
        tecnico2 = crear('tecnico2', 'Elder Barrios Gómez', 'tecnico')
        inactivo = crear('tecnico_inactivo', 'Mynor Say Coché', 'tecnico',
                         estado='Inactivo')

        # Auditoría de usuarios (Figura 13): creación de los tres y
        # creación + eliminación lógica del inactivo.
        self._hist_usuario(oficinista, admin, 'INSERT', dias=70)
        self._hist_usuario(tecnico1, admin, 'INSERT', dias=70)
        self._hist_usuario(tecnico2, admin, 'INSERT', dias=70)
        self._hist_usuario(inactivo, admin, 'INSERT', dias=68)
        self._hist_usuario(inactivo, admin, 'DELETE_LOGICO', dias=40)

        self.stdout.write('  Usuarios: admin, oficinista, tecnico1, tecnico2 '
                          '(+ tecnico_inactivo).')
        return {
            'admin': admin, 'oficinista': oficinista,
            'tecnico1': tecnico1, 'tecnico2': tecnico2, 'inactivo': inactivo,
        }

    # ------------------------------------------------------------------ #
    # Viviendas
    # ------------------------------------------------------------------ #
    def _plan_viviendas(self):
        """
        Lista de 40 especificaciones de vivienda. Cada una dice su barrio y el
        'papel' que juega en las inspecciones:
          - 'uninspected'                -> sin ninguna inspección (Figura 10)
          - ('single', nivel)            -> una sola inspección de ese nivel
          - ('long', patron)             -> 3 inspecciones (Figura 11)
        """
        plan = []

        # 5 viviendas longitudinales (Figura 11)
        plan += [
            ('Barrio La Llovizna', ('long', 'mejora')),    # A->M->B  (últ. Bajo)
            ('Barrio El Campo',    ('long', 'mejora')),    # A->M->B  (últ. Bajo)
            ('Barrio La Llovizna', ('long', 'empeora')),   # B->M->A  (últ. Alto)
            ('Barrio El Campo',    ('long', 'empeora')),   # B->M->A  (últ. Alto)
            ('Barrio La Llovizna', ('long', 'mantiene')),  # A->A->A  (últ. Alto)
        ]

        # 5 viviendas de alto riesgo con una sola inspección reciente (<=6 días)
        for barrio in ['Barrio La Llovizna', 'Barrio El Campo', 'Barrio El Campo',
                       'Barrio El Centro', 'Barrio El Jardín']:
            plan.append((barrio, ('single', 'Alto')))

        # Medio (12) y Bajo (8) de una sola inspección, por barrio
        medio_alloc = {
            'Barrio La Llovizna': 2, 'Barrio El Campo': 2, 'Barrio El Centro': 3,
            'Barrio El Jardín': 2, 'Barrio Camilo Alvarado': 2,
            'Barrio La Linterna': 1,
        }
        bajo_alloc = {
            'Barrio La Llovizna': 1, 'Barrio El Campo': 1, 'Barrio El Centro': 2,
            'Barrio El Jardín': 2, 'Barrio Camilo Alvarado': 1,
            'Barrio La Linterna': 1,
        }
        uninsp_alloc = {
            'Barrio La Llovizna': 3, 'Barrio El Campo': 2, 'Barrio El Centro': 2,
            'Barrio El Jardín': 1, 'Barrio Camilo Alvarado': 1,
            'Barrio La Linterna': 1,
        }
        for barrio, n in medio_alloc.items():
            plan += [(barrio, ('single', 'Medio'))] * n
        for barrio, n in bajo_alloc.items():
            plan += [(barrio, ('single', 'Bajo'))] * n
        for barrio, n in uninsp_alloc.items():
            plan += [(barrio, 'uninspected')] * n

        return plan

    def _viviendas(self, usuarios, rng):
        registradores = [usuarios['tecnico1'], usuarios['tecnico2']]
        plan = self._plan_viviendas()
        viviendas = []
        contador_mz = {b: 0 for b in BARRIOS}

        for i, (barrio, papel) in enumerate(plan):
            registrador = registradores[i % 2]
            v = Vivienda(
                direccion=self._direccion(barrio, contador_mz, rng),
                responsable_familia=self._nombre(rng),
                num_habitantes=rng.randint(3, 8),
                zona=barrio,
                referencia=rng.choice(REFERENCIAS),
                telefono=f'5{rng.randint(100,999)}-{rng.randint(1000,9999)}',
                registrado_por=registrador,
                es_demo=True,
            )
            v.save()  # genera codigo_qr VSQR-XXXXXXXX y el PNG por el flujo normal

            # Fecha de registro: antes de cualquier inspección.
            if papel == 'uninspected':
                dias_reg = rng.randint(35, 90)
            elif papel[0] == 'long':
                dias_reg = rng.randint(92, 100)
            else:
                dias_reg = rng.randint(31, 45)
            fecha_reg = self._fecha_laboral(dias_reg, rng)
            Vivienda.objects.filter(pk=v.pk).update(
                fecha_registro=fecha_reg, fecha_modificacion=fecha_reg)
            v.refresh_from_db()

            self._hist_vivienda(v, registrador, 'INSERT', fecha_reg)
            viviendas.append({'obj': v, 'papel': papel})

        # Unas cuantas modificaciones para que la auditoría muestre UPDATE.
        for v in viviendas[:4]:
            fecha_up = v['obj'].fecha_registro + datetime.timedelta(days=8)
            self._hist_vivienda(v['obj'], usuarios['oficinista'], 'UPDATE',
                                fecha_up)

        self.stdout.write(f'  Viviendas: {len(viviendas)} creadas con QR '
                          '(PNG en media/qr_codes/).')
        return viviendas

    # ------------------------------------------------------------------ #
    # Inspecciones
    # ------------------------------------------------------------------ #
    def _inspecciones(self, viviendas, usuarios, rng):
        tecnicos = [usuarios['tecnico1'], usuarios['tecnico2']]
        turno = {'i': 0}

        def crea_inspeccion(vivienda, nivel, dias_atras):
            tecnico = tecnicos[turno['i'] % 2]
            turno['i'] += 1
            flags = self._hallazgos(nivel, rng)
            insp = Inspeccion(vivienda=vivienda, usuario=tecnico, es_demo=True,
                              **flags)
            insp.save()  # el clasificador real fija nivel_riesgo
            fecha = self._fecha_laboral(dias_atras, rng)
            Inspeccion.objects.filter(pk=insp.pk).update(fecha_inspeccion=fecha)
            insp.refresh_from_db()
            self._hist_inspeccion(insp, tecnico, 'INSERT', fecha)
            return insp

        patrones_long = {
            'mejora':   ['Alto', 'Medio', 'Bajo'],
            'empeora':  ['Bajo', 'Medio', 'Alto'],
            'mantiene': ['Alto', 'Alto', 'Alto'],
        }
        dias_long = [88, 58, 28]  # ~90/60/30; la de 28 días cuenta para el total

        total = 0
        for item in viviendas:
            v, papel = item['obj'], item['papel']
            if papel == 'uninspected':
                continue
            if papel[0] == 'long':
                for nivel, dias in zip(patrones_long[papel[1]], dias_long):
                    crea_inspeccion(v, nivel, dias)
                    total += 1
            else:  # single
                nivel = papel[1]
                if nivel == 'Alto':
                    dias = rng.randint(1, 6)       # dentro de 7 días -> no urgente
                else:
                    dias = rng.randint(8, 29)      # reciente (<30) y variado
                crea_inspeccion(v, nivel, dias)
                total += 1

        self.stdout.write(f'  Inspecciones: {total} creadas; el clasificador '
                          'asignó cada nivel de riesgo.')

    def _hallazgos(self, nivel, rng):
        """Hallazgos que, pasados por clasificar_riesgo(), producen `nivel`."""
        if nivel == 'Alto':
            num = rng.randint(4, 9)
            return {
                'num_depositos': num,
                'depositos_positivos': rng.randint(1, min(3, num)),
                'presencia_larvas': True,
                'criaderos_potenciales': True,
                'aplico_larvicida': True,
                'elimino_criaderos': True,
                'programo_fumigacion': rng.random() < 0.5,
                'educo_residente': True,
                'observaciones': rng.choice(OBS['Alto']),
            }
        if nivel == 'Medio':
            return {
                'num_depositos': rng.randint(2, 7),
                'depositos_positivos': 0,
                'presencia_larvas': False,
                'criaderos_potenciales': True,
                'aplico_larvicida': rng.random() < 0.4,
                'elimino_criaderos': True,
                'programo_fumigacion': False,
                'educo_residente': True,
                'observaciones': rng.choice(OBS['Medio']),
            }
        return {  # Bajo
            'num_depositos': rng.randint(2, 5),
            'depositos_positivos': 0,
            'presencia_larvas': False,
            'criaderos_potenciales': False,
            'aplico_larvicida': False,
            'elimino_criaderos': False,
            'programo_fumigacion': False,
            'educo_residente': True,
            'observaciones': rng.choice(OBS['Bajo']),
        }

    # ------------------------------------------------------------------ #
    # Helpers de fechas e históricos
    # ------------------------------------------------------------------ #
    def _fecha_laboral(self, dias_atras, rng):
        """Datetime aware, lunes a viernes, 7:00–16:00, hace ~`dias_atras` días."""
        d = (timezone.localtime() - datetime.timedelta(days=dias_atras)).date()
        while d.weekday() >= 5:  # 5=sábado, 6=domingo -> correr a viernes
            d -= datetime.timedelta(days=1)
        hora = rng.randint(7, 15)
        minuto = rng.choice([0, 10, 15, 20, 30, 40, 45, 50])
        naive = datetime.datetime(d.year, d.month, d.day, hora, minuto)
        return timezone.make_aware(naive, timezone.get_current_timezone())

    def _hist_usuario(self, usuario, quien, tipo, dias):
        h = UsuarioHistorico.objects.create(
            usuario_original=usuario, username=usuario.username,
            nombre_completo=usuario.nombre_completo,
            rol_nombre=usuario.rol.nombre if usuario.rol else '',
            estado=usuario.estado, usuario_cambio=quien, tipo_operacion=tipo)
        self._fecha_hist(UsuarioHistorico, h.pk, dias)

    def _hist_vivienda(self, vivienda, quien, tipo, fecha):
        h = ViviendaHistorico.objects.create(
            vivienda_original=vivienda, codigo_qr=vivienda.codigo_qr,
            direccion=vivienda.direccion,
            responsable_familia=vivienda.responsable_familia,
            num_habitantes=vivienda.num_habitantes, zona=vivienda.zona,
            manzana=vivienda.manzana, numero_casa=vivienda.numero_casa,
            estado=vivienda.estado, usuario_cambio=quien, tipo_operacion=tipo)
        ViviendaHistorico.objects.filter(pk=h.pk).update(fecha_cambio=fecha)

    def _hist_inspeccion(self, insp, quien, tipo, fecha):
        h = InspeccionHistorico.objects.create(
            inspeccion_original=insp, vivienda_codigo=insp.vivienda.codigo_qr,
            presencia_larvas=insp.presencia_larvas,
            criaderos_potenciales=insp.criaderos_potenciales,
            nivel_riesgo=insp.nivel_riesgo, clase_trabajo=insp.clase_trabajo,
            estado=insp.estado,
            usuario_cambio=quien, tipo_operacion=tipo)
        InspeccionHistorico.objects.filter(pk=h.pk).update(fecha_cambio=fecha)

    def _fecha_hist(self, modelo, pk, dias):
        fecha = (timezone.localtime() - datetime.timedelta(days=dias))
        modelo.objects.filter(pk=pk).update(fecha_cambio=fecha)

    # ------------------------------------------------------------------ #
    # Datos realistas
    # ------------------------------------------------------------------ #
    def _nombre(self, rng):
        return f'{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}'

    def _direccion(self, barrio, contador_mz, rng):
        contador_mz[barrio] += 1
        mz = contador_mz[barrio]
        via = rng.choice(['Avenida', 'Calle'])
        num_via = rng.randint(1, 8)
        casa_a = rng.randint(1, 9)
        casa_b = rng.randint(10, 60)
        return (f'{num_via}a. {via} {casa_a}-{casa_b:02d}, '
                f'Mz. {mz} Casa {rng.randint(1, 25)}, {barrio}')

    # ------------------------------------------------------------------ #
    # Resumen de salida
    # ------------------------------------------------------------------ #
    def _resumen(self, usuarios):
        viv_seed = Vivienda.objects.filter(
            registrado_por__username__in=['tecnico1', 'tecnico2'])
        total_viv = viv_seed.count()
        con_insp = sum(1 for v in viv_seed if v.inspecciones.filter(
            estado='Activo').exists())
        sin_insp = total_viv - con_insp

        # Conteo por última inspección de cada vivienda.
        conteo = {'Alto': 0, 'Medio': 0, 'Bajo': 0}
        for v in viv_seed:
            ult = v.inspecciones.filter(estado='Activo').first()
            if ult:
                conteo[ult.nivel_riesgo] += 1

        self.stdout.write(self.style.SUCCESS('\n--- Resumen ---'))
        self.stdout.write(f'  Viviendas: {total_viv} '
                          f'({con_insp} inspeccionadas, {sin_insp} sin visita)')
        self.stdout.write(
            f'  Riesgo (última inspección): '
            f"Alto={conteo['Alto']}  Medio={conteo['Medio']}  Bajo={conteo['Bajo']}")
        objetivo = 'OK' if conteo == {'Alto': 8, 'Medio': 12, 'Bajo': 10} else \
            'REVISAR (se esperaba 8/12/10)'
        self.stdout.write(f'  Objetivo 8/12/10: {objetivo}')

        self.stdout.write(self.style.SUCCESS('\n--- Credenciales (todas) ---'))
        self.stdout.write(f'  Contraseña compartida: {SHARED_PASSWORD}')
        for key, label in [('admin', 'Administrador — Josué Valiente'),
                           ('oficinista', 'Oficinista — Liz Mejía Quiroa'),
                           ('tecnico1', 'Técnico — Porfirio López Valiente'),
                           ('tecnico2', 'Técnico — Elder Barrios Gómez'),
                           ('inactivo', 'Técnico INACTIVO — Mynor Say Coché')]:
            u = usuarios[key]
            self.stdout.write(f'    {u.username:18} {label}')
        self.stdout.write(self.style.WARNING(
            '  NOTA: la clave de admin pasó de admin2026 a la compartida.'))
        self.stdout.write('')
