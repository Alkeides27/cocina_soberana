from django.urls import path
from . import views

urlpatterns = [
    path('', views.ListaRecetasView.as_view(), name='lista_recetas'),
    path('receta/<str:codigo>/', views.DetalleRecetaView.as_view(), name='detalle_receta'),
    path('filtros/', views.filtrar_recetas_ajax, name='filtrar_recetas_ajax'),
]
