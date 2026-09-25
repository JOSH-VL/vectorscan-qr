"""
Modelos del módulo de Viviendas y QR — VectorScan QR
Sprint 2: Registro de Viviendas y Generación de Códigos QR
"""
import uuid
import qrcode
import io
import os
from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile


class Vivienda(models.Model):
    """Modelo principal de viviendas del programa de ETV."""

    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]

    codigo_qr = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        verbose_name='Código QR'
    )
    direccion = models.CharField(max_length=255, verbose_name='Dirección')
    responsable_familia = models.CharField(
        max_length=150,
        verbose_name='Responsable de familia'
    )
    num_habitantes = models.PositiveIntegerField(
        default=0,
        verbose_name='Número de habitantes'
    )
    zona = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Zona'
    )
    referencia = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Referencia de ubicación'
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Teléfono de contacto'
    )
    imagen_qr = models.ImageField(
        upload_to='qr_codes/',
        blank=True,
        null=True,
        verbose_name='Imagen QR'
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='Activo'
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='viviendas_registradas',
        verbose_name='Registrado por'
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Vivienda'
        verbose_name_plural = 'Viviendas'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.codigo_qr} — {self.direccion}"

    @property
    def esta_activa(self):
        return self.estado == 'Activo'

    def save(self, *args, **kwargs):
        """Genera el código QR automáticamente al crear la vivienda."""
        if not self.codigo_qr:
            # Generar código único: VSQR-XXXXXX
            self.codigo_qr = f"VSQR-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
        # Generar imagen QR si no existe
        if not self.imagen_qr:
            self._generar_imagen_qr()

    def _generar_imagen_qr(self):
        """Genera la imagen PNG del código QR."""
        # El QR contiene la URL de inspección de la vivienda
        qr_data = f"VECTORSCAN|{self.codigo_qr}|{self.id}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Guardar imagen en memoria y luego en el campo ImageField
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        filename = f"qr_{self.codigo_qr}.png"
        self.imagen_qr.save(filename, ContentFile(buffer.read()), save=True)

    def regenerar_qr(self):
        """Regenera la imagen QR (por si se daña o pierde)."""
        if self.imagen_qr:
            # Borrar imagen anterior
            if os.path.isfile(self.imagen_qr.path):
                os.remove(self.imagen_qr.path)
            self.imagen_qr = None
        self._generar_imagen_qr()

    @property
    def total_inspecciones(self):
        """Cuenta las inspecciones realizadas a esta vivienda."""
        return self.inspecciones.filter(estado='Activo').count() if hasattr(self, 'inspecciones') else 0

    @property
    def ultima_inspeccion(self):
        """Retorna la última inspección activa."""
        if hasattr(self, 'inspecciones'):
            return self.inspecciones.filter(estado='Activo').first()
        return None


class ViviendaHistorico(models.Model):
    """Tabla histórica para trazabilidad de cambios en viviendas."""

    TIPO_OP = [
        ('INSERT', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE_LOGICO', 'Eliminación lógica'),
    ]

    vivienda_original = models.ForeignKey(
        Vivienda,
        on_delete=models.CASCADE,
        related_name='historial'
    )
    codigo_qr = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)
    responsable_familia = models.CharField(max_length=150)
    num_habitantes = models.PositiveIntegerField(default=0)
    zona = models.CharField(max_length=50, blank=True)
    estado = models.CharField(max_length=10)
    # Campos de auditoría
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    usuario_cambio = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cambios_viviendas'
    )
    tipo_operacion = models.CharField(max_length=20, choices=TIPO_OP)

    class Meta:
        verbose_name = 'Historial de Vivienda'
        verbose_name_plural = 'Historial de Viviendas'
        ordering = ['-fecha_cambio']

    def __str__(self):
        return f"{self.codigo_qr} — {self.tipo_operacion} ({self.fecha_cambio})"
