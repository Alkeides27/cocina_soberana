import pytest
from catalogo.models import Receta
from catalogo.filters import filtrar_recetas

@pytest.mark.django_db
def test_filtrar_recetas_dieteticas():
    # Crear recetas de prueba
    r1 = Receta.objects.create(
        codigo="T001", nombre="Receta Vegana", porciones_base=4, calorias_por_porcion=100,
        nivel_costo="ME", es_vegetariana=True, es_vegana=True, es_sin_gluten=False, es_sin_lactosa=True
    )
    r2 = Receta.objects.create(
        codigo="T002", nombre="Receta Carnivora", porciones_base=4, calorias_por_porcion=300,
        nivel_costo="EM", es_vegetariana=False, es_vegana=False, es_sin_gluten=True, es_sin_lactosa=False
    )
    
    qs = Receta.objects.all()
    
    # Filtrar vegetariana
    res = filtrar_recetas(qs, {"es_vegetariana": "true"})
    assert r1 in res
    assert r2 not in res
    
    # Filtrar vegana
    res = filtrar_recetas(qs, {"es_vegana": "true"})
    assert r1 in res
    assert r2 not in res
    
    # Filtrar sin gluten
    res = filtrar_recetas(qs, {"es_sin_gluten": "true"})
    assert r2 in res
    assert r1 not in res

    # Filtrar sin lactosa
    res = filtrar_recetas(qs, {"es_sin_lactosa": "true"})
    assert r1 in res
    assert r2 not in res
