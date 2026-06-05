from django.db.models import QuerySet
from typing import Dict, Any


def filtrar_recetas(queryset: QuerySet, params: Dict[str, Any]) -> QuerySet:
    """
    Filtra un QuerySet de Recetas de forma combinada según los parámetros de búsqueda.
    Maneja filtros por categoría (slug), nivel de costo (ME/EM), y banderas dietéticas.
    """
    # Filtro por categoría (ej. 'desayuno')
    categoria = params.get('categoria')
    if categoria and categoria != 'todas':
        queryset = queryset.filter(categorias__slug=categoria)
    
    # Filtro por nivel de costo (ej. 'ME', 'EM')
    nivel_costo = params.get('nivel_costo')
    if nivel_costo and nivel_costo != 'todos':
        queryset = queryset.filter(nivel_costo=nivel_costo)
    
    # Filtros dietéticos (se activan si el checkbox envía 'on' o 'true')
    if params.get('es_vegetariana') in ['on', 'true', True]:
        queryset = queryset.filter(es_vegetariana=True)
    if params.get('es_vegana') in ['on', 'true', True]:
        queryset = queryset.filter(es_vegana=True)
    if params.get('es_sin_gluten') in ['on', 'true', True]:
        queryset = queryset.filter(es_sin_gluten=True)
    if params.get('es_sin_lactosa') in ['on', 'true', True]:
        queryset = queryset.filter(es_sin_lactosa=True)
        
    return queryset.distinct()
