from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from .forms import RegistroForm, EditarPerfilForm
from .models import RestriccionUsuario


def registro_usuario(request):
    """
    Vista para el registro de nuevos usuarios.
    Si el registro es exitoso, inicia sesión al usuario automáticamente y lo redirige al dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, f"¡Bienvenido, {user.nombre}! Tu cuenta ha sido creada exitosamente.")
            return redirect('dashboard')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = RegistroForm()
        
    return render(request, 'usuarios/registro.html', {'form': form})


class CustomLoginView(LoginView):
    """
    Vista de inicio de sesión personalizada que utiliza el template del proyecto.
    """
    template_name = 'usuarios/login.html'
    redirect_authenticated_user = True


class CustomLogoutView(LogoutView):
    """
    Vista de cierre de sesión personalizada.
    """
    next_page = '/'


@login_required
def perfil_usuario(request):
    """
    Vista para ver el perfil del usuario y sus restricciones dietéticas.
    """
    restricciones = request.user.restricciones.all()
    tipos_restriccion = RestriccionUsuario.TIPOS_RESTRICCION
    return render(request, 'usuarios/perfil.html', {
        'restricciones': restricciones,
        'tipos_restriccion': tipos_restriccion
    })


@login_required
def editar_perfil(request):
    """
    Vista para editar los datos personales del perfil (nombre, presupuesto, etc.).
    """
    if request.method == 'POST':
        form = EditarPerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Tu perfil ha sido actualizado correctamente.")
            return redirect('perfil')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = EditarPerfilForm(instance=request.user)
        
    return render(request, 'usuarios/editar_perfil.html', {'form': form})


@login_required
@require_POST
def agregar_restriccion(request):
    """
    Endpoint HTMX para agregar una restricción dietética al usuario.
    Retorna el fragmento HTML actualizado con la lista de restricciones.
    """
    tipo = request.POST.get('tipo')
    descripcion = request.POST.get('descripcion', '')
    
    if tipo:
        # Evitar duplicados del mismo tipo para el usuario
        if not RestriccionUsuario.objects.filter(fk_usuario=request.user, tipo=tipo).exists():
            RestriccionUsuario.objects.create(
                fk_usuario=request.user,
                tipo=tipo,
                descripcion=descripcion
            )
            
    restricciones = request.user.restricciones.all()
    return render(request, 'usuarios/partials/_restricciones_list.html', {
        'restricciones': restricciones
    })


@login_required
@require_http_methods(["DELETE", "POST"])
def eliminar_restriccion(request, pk):
    """
    Endpoint HTMX para eliminar una restricción dietética del usuario.
    Retorna el fragmento HTML actualizado.
    """
    restriccion = get_object_or_404(RestriccionUsuario, pk=pk, fk_usuario=request.user)
    restriccion.delete()
    
    restricciones = request.user.restricciones.all()
    return render(request, 'usuarios/partials/_restricciones_list.html', {
        'restricciones': restricciones
    })
