from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('menu/', views.menu_semanal, name='menu_semanal'),
    path('menu/agregar/', views.agregar_menu_semanal, name='agregar_menu_semanal'),
    path('menu/remover/<int:pk>/', views.remover_menu_semanal, name='remover_menu_semanal'),
    path('lista-compra/', views.lista_compra, name='lista_compra'),
    path('lista-compra/generar/', views.generar_lista_compra, name='generar_lista_compra'),
    path('lista-compra/item/<int:pk>/', views.cambiar_estado_item, name='cambiar_estado_item'),
    path('lista-compra/sync/', views.sync_lista_compra, name='sync_lista_compra'),
]
