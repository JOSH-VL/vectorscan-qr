from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Usuario, Rol, UsuarioHistorico

def login_view(request):
    if request.user.is_authenticated:
        return redirect('usuarios:lista')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.esta_activo:
            login(request, user)
            messages.success(request, f'Bienvenido, {user.nombre_completo or user.username}.')
            return redirect('usuarios:lista')
        else:
            messages.error(request, 'Credenciales incorrectas o usuario inactivo.')
    return render(request, 'usuarios/login.html')

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('usuarios:login')

@login_required
def lista_usuarios(request):
    usuarios = Usuario.objects.filter(estado='Activo').select_related('rol')
    return render(request, 'usuarios/lista.html', {'usuarios': usuarios})

@login_required
def crear_usuario(request):
    roles = Rol.objects.all()
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        nombre = request.POST.get('nombre_completo')
        rol_id = request.POST.get('rol')
        if Usuario.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya existe.')
        else:
            rol = get_object_or_404(Rol, pk=rol_id)
            u = Usuario.objects.create_user(username=username, password=password, nombre_completo=nombre, rol=rol, estado='Activo')
            UsuarioHistorico.objects.create(usuario_original=u, username=u.username, nombre_completo=u.nombre_completo, rol_nombre=rol.nombre, estado=u.estado, usuario_cambio=request.user, tipo_operacion='INSERT')
            messages.success(request, f'Usuario {username} creado exitosamente.')
            return redirect('usuarios:lista')
    return render(request, 'usuarios/crear.html', {'roles': roles})

@login_required
def editar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    roles = Rol.objects.all()
    if request.method == 'POST':
        usuario.nombre_completo = request.POST.get('nombre_completo')
        usuario.rol = get_object_or_404(Rol, pk=request.POST.get('rol'))
        usuario.save()
        UsuarioHistorico.objects.create(usuario_original=usuario, username=usuario.username, nombre_completo=usuario.nombre_completo, rol_nombre=usuario.rol.nombre, estado=usuario.estado, usuario_cambio=request.user, tipo_operacion='UPDATE')
        messages.success(request, f'Usuario {usuario.username} actualizado.')
        return redirect('usuarios:lista')
    return render(request, 'usuarios/editar.html', {'usuario': usuario, 'roles': roles})

@login_required
def desactivar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        usuario.estado = 'Inactivo'
        usuario.is_active = False
        usuario.save()
        UsuarioHistorico.objects.create(usuario_original=usuario, username=usuario.username, nombre_completo=usuario.nombre_completo, rol_nombre=usuario.rol.nombre if usuario.rol else '', estado=usuario.estado, usuario_cambio=request.user, tipo_operacion='DELETE_LOGICO')
        messages.warning(request, f'Usuario {usuario.username} desactivado.')
        return redirect('usuarios:lista')
    return render(request, 'usuarios/confirmar_desactivar.html', {'usuario': usuario})
