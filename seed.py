"""
Script para crear los roles iniciales y el superusuario.
Ejecutar: docker compose exec web python seed.py
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.usuarios.models import Rol, Usuario

# Crear roles
roles_data = [
    ('admin', 'Acceso completo a todos los módulos del sistema'),
    ('oficinista', 'Gestión de viviendas, reportes y exportaciones'),
    ('tecnico', 'Registro de inspecciones desde campo'),
]
for nombre, desc in roles_data:
    rol, created = Rol.objects.get_or_create(nombre=nombre, defaults={'descripcion': desc})
    print(f"{'Creado' if created else 'Ya existe'}: Rol {nombre}")

# Crear superusuario admin
if not Usuario.objects.filter(username='admin').exists():
    rol_admin = Rol.objects.get(nombre='admin')
    u = Usuario.objects.create_superuser(username='admin', password='admin2026', nombre_completo='Administrador del Sistema', rol=rol_admin, estado='Activo')
    print(f"Superusuario creado: admin / admin2026")
else:
    print("Superusuario admin ya existe")

print("\n¡Seed completado! Podés iniciar sesión con: admin / admin2026")
