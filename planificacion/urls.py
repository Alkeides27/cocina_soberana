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
    
    # HTMX endpoints para agregar al menú desde el catálogo
    path('menu/render-add-form/<int:receta_id>/', views.render_add_to_selection_form, name='render_add_to_selection_form'),
    path('menu/add-htmx/', views.agregar_menu_semanal_htmx, name='agregar_menu_semanal_htmx'),
    path('ingrediente/add-htmx/', views.agregar_ingrediente_semanal_htmx, name='agregar_ingrediente_semanal_htmx'),
    path('ingrediente/remove-htmx/<int:pk>/', views.remover_ingrediente_semanal_htmx, name='remover_ingrediente_semanal_htmx'),
    path('ingrediente/render-add-form/', views.render_add_ingrediente_form, name='render_add_ingrediente_form'),
]
