import pytest
from decimal import Decimal
from django.urls import reverse
from catalogo.models import Receta, Ingrediente, RecetaIngrediente
from planificacion.models import MenuSemanal, ListaCompra, ItemListaCompra
from usuarios.tests.factories import UsuarioFactory
from planificacion.views import get_current_week_dates
import datetime

@pytest.mark.django_db
def test_generacion_lista_compra_consolidada(client):
    user = UsuarioFactory(tamano_familia=4)
    client.force_login(user)
    
    # 1. Crear dos recetas con porciones base distintas y que comparten un ingrediente
    receta1 = Receta.objects.create(
        codigo="L001", nombre="Receta 1", porciones_base=2, calorias_por_porcion=100, nivel_costo="ME"
    )
    receta2 = Receta.objects.create(
        codigo="L002", nombre="Receta 2", porciones_base=4, calorias_por_porcion=100, nivel_costo="ME"
    )
    
    ingrediente_comun = Ingrediente.objects.create(
        nombre="Harina de maíz precocida", categoria_nutricional="CER", unidad_medida="gramos",
        origen="NAC", nivel_costo="ME"
    )
    ingrediente_unico = Ingrediente.objects.create(
        nombre="Queso blanco", categoria_nutricional="LAC", unidad_medida="gramos",
        origen="NAC", nivel_costo="EM"
    )
    
    # Receta 1 usa 100g de harina y 50g de queso. Porciones base = 2
    RecetaIngrediente.objects.create(fk_receta=receta1, fk_ingrediente=ingrediente_comun, cantidad=Decimal("100.00"))
    RecetaIngrediente.objects.create(fk_receta=receta1, fk_ingrediente=ingrediente_unico, cantidad=Decimal("50.00"))
    
    # Receta 2 usa 200g de harina. Porciones base = 4
    RecetaIngrediente.objects.create(fk_receta=receta2, fk_ingrediente=ingrediente_comun, cantidad=Decimal("200.00"))
    
    # Planificar ambas comidas en la semana actual
    dates = get_current_week_dates()
    lunes = dates[0]["fecha"]
    martes = dates[1]["fecha"]
    
    MenuSemanal.objects.create(fk_usuario=user, fk_receta=receta1, fecha=lunes, momento="DESAYUNO")
    MenuSemanal.objects.create(fk_usuario=user, fk_receta=receta2, fecha=martes, momento="DESAYUNO")
    
    # Generar la lista de compras
    url_generar = reverse("generar_lista_compra")
    response = client.post(url_generar)
    assert response.status_code == 302  # Redirige a lista_compra
    
    # Verificar la lista de compras generada
    lista = ListaCompra.objects.filter(fk_usuario=user).first()
    assert lista is not None
    
    items = ItemListaCompra.objects.filter(fk_lista=lista)
    assert items.count() == 2
    
    # Verificar cantidades escaladas
    # Harina en Receta 1: 100 * (4 / 2) = 200g
    # Harina en Receta 2: 200 * (4 / 4) = 200g
    # Total harina = 400.00g
    item_harina = items.get(fk_ingrediente=ingrediente_comun)
    assert item_harina.cantidad_total == Decimal("400.00")
    
    # Queso en Receta 1: 50 * (4 / 2) = 100g
    # Total queso = 100.00g
    item_queso = items.get(fk_ingrediente=ingrediente_unico)
    assert item_queso.cantidad_total == Decimal("100.00")
