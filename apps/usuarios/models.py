from django.db import models
from django.contrib.auth.models import AbstractUser

class Rol(models.Model):
    ADMINISTRADOR = 'admin'
    OFICINISTA = 'oficinista'
    TECNICO = 'tecnico'
    ROLES_CHOICES = [(ADMINISTRADOR,'Administrador'),(OFICINISTA,'Oficinista'),(TECNICO,'Técnico de campo')]
    nombre = models.CharField(max_length=50, unique=True, choices=ROLES_CHOICES)
    descripcion = models.CharField(max_length=200, blank=True)
    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
    def __str__(self):
        return self.get_nombre_display()

class Usuario(AbstractUser):
    ESTADO_CHOICES = [('Activo','Activo'),('Inactivo','Inactivo')]
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, null=True, blank=True, related_name='usuarios')
    nombre_completo = models.CharField(max_length=150, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-fecha_creacion']
    def __str__(self):
        return f"{self.nombre_completo or self.username} ({self.rol})"
    @property
    def esta_activo(self):
        return self.estado == 'Activo'

class UsuarioHistorico(models.Model):
    TIPO_OP = [('INSERT','Creación'),('UPDATE','Actualización'),('DELETE_LOGICO','Eliminación lógica')]
    usuario_original = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='historial')
    username = models.CharField(max_length=150)
    nombre_completo = models.CharField(max_length=150, blank=True)
    rol_nombre = models.CharField(max_length=50, blank=True)
    estado = models.CharField(max_length=10)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    usuario_cambio = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='cambios_realizados')
    tipo_operacion = models.CharField(max_length=20, choices=TIPO_OP)
    class Meta:
        verbose_name = 'Historial de Usuario'
        verbose_name_plural = 'Historial de Usuarios'
        ordering = ['-fecha_cambio']
    def __str__(self):
        return f"{self.username} - {self.tipo_operacion} ({self.fecha_cambio})"
