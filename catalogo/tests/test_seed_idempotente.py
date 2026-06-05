import pytest
from django.core.management import call_command
from catalogo.models import Categoria, Ingrediente, Receta

@pytest.mark.django_db
def test_seed_catalogo_idempotente():
    # Asegurarnos de iniciar con la base vacía en el test
    Categoria.objects.all().delete()
    Ingrediente.objects.all().delete()
    Receta.objects.all().delete()
    
    # Primera ejecución
    call_command("seed_catalogo", "--no-input")
    assert Categoria.objects.count() == 7
    assert Ingrediente.objects.count() == 55
    assert Receta.objects.count() == 35
    
    # Segunda ejecución (idempotencia)
    call_command("seed_catalogo", "--no-input")
    assert Categoria.objects.count() == 7
    assert Ingrediente.objects.count() == 55
    assert Receta.objects.count() == 35
