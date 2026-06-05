from django.contrib import admin
from .models import MenuSemanal, ListaCompra, ItemListaCompra


class ItemListaCompraInline(admin.TabularInline):
    """
    Permite gestionar los ítems de una lista de compras directamente desde la lista.
    """
    model = ItemListaCompra
    extra = 1


@admin.register(MenuSemanal)
class MenuSemanalAdmin(admin.ModelAdmin):
    list_display = ('fk_usuario', 'fecha', 'momento', 'fk_receta')
    search_fields = ('fk_usuario__username', 'fk_usuario__nombre', 'fk_receta__nombre', 'fk_receta__codigo')
    list_filter = ('fecha', 'momento')


@admin.register(ListaCompra)
class ListaCompraAdmin(admin.ModelAdmin):
    list_display = ('fk_usuario', 'fecha_generacion', 'sincronizada_at')
    search_fields = ('fk_usuario__username', 'fk_usuario__nombre')
    list_filter = ('fecha_generacion',)
    inlines = [ItemListaCompraInline]


@admin.register(ItemListaCompra)
class ItemListaCompraAdmin(admin.ModelAdmin):
    list_display = ('fk_lista', 'fk_ingrediente', 'cantidad_total', 'estado', 'actualizado_at')
    search_fields = ('fk_lista__fk_usuario__username', 'fk_ingrediente__nombre', 'estado')
    list_filter = ('estado', 'fk_ingrediente__categoria_nutricional')
