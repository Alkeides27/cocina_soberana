from django.contrib import admin
from .models import (
    Categoria,
    Ingrediente,
    Receta,
    RecetaCategoria,
    RecetaIngrediente,
    HistorialPrecioIngrediente
)


class RecetaCategoriaInline(admin.TabularInline):
    """
    Permite asociar categorías directamente desde el panel de edición de una Receta.
    """
    model = RecetaCategoria
    extra = 1


class RecetaIngredienteInline(admin.TabularInline):
    """
    Permite gestionar los ingredientes de una receta y sus cantidades
    directamente desde el panel de la receta.
    """
    model = RecetaIngrediente
    extra = 1


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug')
    search_fields = ('nombre', 'slug')
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(Ingrediente)
class IngredienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria_nutricional', 'unidad_medida', 'origen', 'nivel_costo', 'precio_actual', 'fecha_precio')
    search_fields = ('nombre',)
    list_filter = ('categoria_nutricional', 'origen', 'nivel_costo')


@admin.register(Receta)
class RecetaAdmin(admin.ModelAdmin):
    list_display = (
        'codigo',
        'nombre',
        'porciones_base',
        'calorias_por_porcion',
        'nivel_costo',
        'es_vegetariana',
        'es_vegana',
        'es_sin_gluten',
        'es_sin_lactosa'
    )
    search_fields = ('codigo', 'nombre', 'notas_preparacion')
    list_filter = ('nivel_costo', 'es_vegetariana', 'es_vegana', 'es_sin_gluten', 'es_sin_lactosa')
    inlines = [RecetaCategoriaInline, RecetaIngredienteInline]


@admin.register(RecetaCategoria)
class RecetaCategoriaAdmin(admin.ModelAdmin):
    list_display = ('fk_receta', 'fk_categoria')
    search_fields = ('fk_receta__codigo', 'fk_receta__nombre', 'fk_categoria__nombre')
    list_filter = ('fk_categoria',)


@admin.register(RecetaIngrediente)
class RecetaIngredienteAdmin(admin.ModelAdmin):
    list_display = ('fk_receta', 'fk_ingrediente', 'cantidad', 'nota_uso')
    search_fields = ('fk_receta__codigo', 'fk_receta__nombre', 'fk_ingrediente__nombre')


@admin.register(HistorialPrecioIngrediente)
class HistorialPrecioIngredienteAdmin(admin.ModelAdmin):
    list_display = ('fk_ingrediente', 'precio', 'fecha')
    search_fields = ('fk_ingrediente__nombre',)
    list_filter = ('fecha', 'fk_ingrediente__categoria_nutricional')
