from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, RestriccionUsuario


class CustomUserAdmin(UserAdmin):
    """
    Extiende la administración de usuarios para incluir los campos personalizados
    de Cocina Soberana en listados y formularios de edición.
    """
    model = Usuario
    list_display = ('username', 'email', 'nombre', 'tamano_familia', 'presupuesto_semanal', 'moneda', 'is_staff')
    search_fields = ('username', 'email', 'nombre')
    list_filter = ('moneda', 'is_staff', 'is_active', 'is_superuser')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información de Cocina Soberana', {
            'fields': ('nombre', 'tamano_familia', 'presupuesto_semanal', 'moneda'),
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información de Cocina Soberana', {
            'fields': ('nombre', 'tamano_familia', 'presupuesto_semanal', 'moneda'),
        }),
    )


admin.site.register(Usuario, CustomUserAdmin)


@admin.register(RestriccionUsuario)
class RestriccionUsuarioAdmin(admin.ModelAdmin):
    """
    Administración de restricciones de dieta por usuario.
    """
    list_display = ('fk_usuario', 'tipo', 'descripcion')
    search_fields = ('fk_usuario__username', 'fk_usuario__nombre', 'tipo', 'descripcion')
    list_filter = ('tipo',)
