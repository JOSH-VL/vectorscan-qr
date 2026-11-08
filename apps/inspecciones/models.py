"""
Modelos del módulo de Inspecciones — VectorScan QR
Sprint 3: Visitas e Inspecciones
"""
from django.db import models
from django.conf import settings
from apps.viviendas.models import Vivienda


class Inspeccion(models.Model):
    """Registro de una inspección domiciliaria."""

    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]
    RIESGO_CHOICES = [
        ('Alto', 'Alto'),
        ('Medio', 'Medio'),
        ('Bajo', 'Bajo'),
    ]
    # Fase 2: clase de trabajo según la hoja INF del consolidado MSPAS.
    CLASE_TRABAJO = [
        ('ENC', 'Encuesta'),
        ('VERIF', 'Verificación'),
        ('ACCION', 'Acción'),
        ('PLAN', 'Plan'),
        ('TRATAMIENTO', 'Tratamiento'),
        ('FUM', 'Fumigación'),
    ]

    vivienda = models.ForeignKey(
        Vivienda,
        on_delete=models.PROTECT,
        related_name='inspecciones',
        verbose_name='Vivienda'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='inspecciones_realizadas',
        verbose_name='Técnico responsable'
    )
    fecha_inspeccion = models.DateTimeField(auto_now_add=True)
    num_depositos = models.PositiveIntegerField(
        default=0,
        verbose_name='Depósitos inspeccionados'
    )
    depositos_positivos = models.PositiveIntegerField(
        default=0,
        verbose_name='Depósitos positivos con larvas'
    )
    presencia_larvas = models.BooleanField(
        default=False,
        verbose_name='¿Presencia de larvas?'
    )
    criaderos_potenciales = models.BooleanField(
        default=False,
        verbose_name='¿Criaderos potenciales?'
    )
    # Medidas de control aplicadas
    aplico_larvicida = models.BooleanField(default=False, verbose_name='Aplicó larvicida')
    elimino_criaderos = models.BooleanField(default=False, verbose_name='Eliminó criaderos')
    programo_fumigacion = models.BooleanField(default=False, verbose_name='Programó fumigación')
    educo_residente = models.BooleanField(default=False, verbose_name='Educación al residente')
    # Clasificación automática
    nivel_riesgo = models.CharField(
        max_length=10,
        choices=RIESGO_CHOICES,
        blank=True,
        verbose_name='Nivel de riesgo'
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='Activo'
    )
    clase_trabajo = models.CharField(
        max_length=15,
        choices=CLASE_TRABAJO,
        default='ENC',
        verbose_name='Clase de trabajo'
    )
    # Marca los registros ficticios de `seed_piloto`. Los datos reales
    # (vistas, importar_formatos) quedan siempre en False.
    es_demo = models.BooleanField(default=False, editable=False,
                                  verbose_name='Dato de demostración')

    class Meta:
        verbose_name = 'Inspección'
        verbose_name_plural = 'Inspecciones'
        ordering = ['-fecha_inspeccion']

    def __str__(self):
        return f"{self.vivienda.codigo_qr} — {self.fecha_inspeccion.strftime('%d/%m/%Y')} — Riesgo {self.nivel_riesgo}"

    def save(self, *args, **kwargs):
        """Clasifica el riesgo automáticamente antes de guardar."""
        self.nivel_riesgo = self.clasificar_riesgo()
        super().save(*args, **kwargs)

    def clasificar_riesgo(self):
        """
        Algoritmo de clasificación de riesgo basado en reglas.
        RN-02: Larvas presentes → ALTO
        RN-03: Criaderos sin larvas → MEDIO
        RN-04: Sin criaderos ni larvas → BAJO
        """
        if self.presencia_larvas:
            return 'Alto'
        elif self.criaderos_potenciales:
            return 'Medio'
        else:
            return 'Bajo'

    @property
    def medidas_aplicadas_lista(self):
        """Retorna lista de medidas aplicadas."""
        medidas = []
        if self.aplico_larvicida:
            medidas.append('Aplicación de larvicida')
        if self.elimino_criaderos:
            medidas.append('Eliminación de criaderos')
        if self.programo_fumigacion:
            medidas.append('Programación de fumigación')
        if self.educo_residente:
            medidas.append('Educación al residente')
        return medidas if medidas else ['Ninguna']

    def depositos_cuadran(self):
        """
        Compara el desglose por tipo (DepositoInspeccion) contra los totales
        num_depositos / depositos_positivos que usa el clasificador.
        Solo avisa, no bloquea. Retorna (True, None) si no hay desglose o si
        cuadra; (False, mensaje) si no cuadra.
        """
        if not self.pk:
            return True, None
        totales = self.depositos.aggregate(
            insp=models.Sum('inspeccionados'), pos=models.Sum('positivos'))
        if totales['insp'] is None:
            return True, None  # sin desglose registrado
        if totales['insp'] == self.num_depositos and totales['pos'] == self.depositos_positivos:
            return True, None
        return False, (
            f"El desglose por tipo suma {totales['insp']} inspeccionados / "
            f"{totales['pos']} positivos, pero la inspección registra "
            f"{self.num_depositos} / {self.depositos_positivos}."
        )

    @property
    def color_riesgo(self):
        """Color CSS para el badge de riesgo."""
        colores = {'Alto': 'danger', 'Medio': 'warning', 'Bajo': 'success'}
        return colores.get(self.nivel_riesgo, 'secondary')

    @property
    def emoji_riesgo(self):
        """Emoji para el nivel de riesgo."""
        emojis = {'Alto': '🔴', 'Medio': '🟡', 'Bajo': '🟢'}
        return emojis.get(self.nivel_riesgo, '⚪')


class DepositoInspeccion(models.Model):
    """
    Desglose de depósitos por tipo, según el Formulario A-1 (hoja ENC1).
    NO reemplaza num_depositos/depositos_positivos de Inspeccion (los usa el
    clasificador); los desglosa. Ver Inspeccion.depositos_cuadran().
    """

    TIPOS = [
        ('PILAS', 'Pilas'),
        ('TONELES', 'Toneles'),
        ('LLANTAS', 'Llantas'),
        ('FLOREROS', 'Floreros'),
        ('CUBETAS', 'Cubetas'),
        ('ARBOL_PLANTAS', 'Árbol y plantas'),
        ('POZOS', 'Pozos y similares'),
        ('TANQUES', 'Tanques'),
        ('OTROS', 'Otros'),
    ]

    inspeccion = models.ForeignKey(
        Inspeccion,
        on_delete=models.CASCADE,
        related_name='depositos',
        verbose_name='Inspección'
    )
    tipo = models.CharField(max_length=20, choices=TIPOS, verbose_name='Tipo de depósito')
    inspeccionados = models.PositiveIntegerField(default=0, verbose_name='Inspeccionados')
    positivos = models.PositiveIntegerField(default=0, verbose_name='Positivos')

    class Meta:
        verbose_name = 'Depósito de inspección'
        verbose_name_plural = 'Depósitos de inspección'
        ordering = ['inspeccion', 'tipo']
        unique_together = [('inspeccion', 'tipo')]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(positivos__lte=models.F('inspeccionados')),
                name='deposito_positivos_lte_inspeccionados',
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.positivos}/{self.inspeccionados}"


class InspeccionHistorico(models.Model):
    """Tabla histórica para trazabilidad de inspecciones."""

    TIPO_OP = [
        ('INSERT', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE_LOGICO', 'Eliminación lógica'),
    ]

    inspeccion_original = models.ForeignKey(
        Inspeccion,
        on_delete=models.CASCADE,
        related_name='historial'
    )
    vivienda_codigo = models.CharField(max_length=100)
    presencia_larvas = models.BooleanField(default=False)
    criaderos_potenciales = models.BooleanField(default=False)
    nivel_riesgo = models.CharField(max_length=10)
    clase_trabajo = models.CharField(max_length=15, blank=True)
    estado = models.CharField(max_length=10)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    usuario_cambio = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cambios_inspecciones'
    )
    tipo_operacion = models.CharField(max_length=20, choices=TIPO_OP)

    class Meta:
        verbose_name = 'Historial de Inspección'
        verbose_name_plural = 'Historial de Inspecciones'
        ordering = ['-fecha_cambio']

    def __str__(self):
        return f"{self.vivienda_codigo} — {self.tipo_operacion} ({self.fecha_cambio})"
