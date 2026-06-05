import pytest
from django.core.management import call_command
from catalogo.models import Categoria, Ingrediente, Receta

@pytest.mark.django_db
def test_seed_catalogo_creates_expected_counts():
    # Asegurarnos de iniciar con la base vacía en el test
    Categoria.objects.all().delete()
    Ingrediente.objects.all().delete()
    Receta.objects.all().delete()
    
    # Ejecutar seed
    call_command("seed_catalogo", "--no-input")
    
    # Validar conteos
    assert Categoria.objects.count() == 7
    assert Ingrediente.objects.count() == 55
    assert Receta.objects.count() == 35
