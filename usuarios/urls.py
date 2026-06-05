from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro_usuario, name='registro'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('perfil/', views.perfil_usuario, name='perfil'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    
    # Endpoints HTMX para restricciones
    path('restricciones/agregar/', views.agregar_restriccion, name='agregar_restriccion'),
    path('restricciones/eliminar/<int:pk>/', views.eliminar_restriccion, name='eliminar_restriccion'),
]
