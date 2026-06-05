import pytest
from decimal import Decimal
from django.urls import reverse
from django.test import Client
from catalogo.models import Receta, Ingrediente, RecetaIngrediente
from usuarios.tests.factories import UsuarioFactory
from planificacion.views import calcular_costo_semanal
import datetime

@pytest.mark.django_db
def test_detalle_receta_costo_no_disponible_con_cantidad_null(client):
    # Crear un usuario de prueba
    user = UsuarioFactory(tamano_familia=4)
    client.force_login(user)

    # Crear una receta de prueba y un ingrediente
    receta = Receta.objects.create(
        codigo="C001", nombre="Receta de prueba", porciones_base=4, calorias_por_porcion=200,
        nivel_costo="ME", es_vegetariana=False, es_vegana=False, es_sin_gluten=False, es_sin_lactosa=False
    )
    ingrediente = Ingrediente.objects.create(
        nombre="Ingrediente X", categoria_nutricional="CER", unidad_medida="gramos",
        origen="NAC", nivel_costo="ME", precio_actual=Decimal("10.00")
    )
    
    # RecetaIngrediente con cantidad=None (sin curar)
    ri = RecetaIngrediente.objects.create(
        fk_receta=receta, fk_ingrediente=ingrediente, cantidad=None
    )
    
    url = reverse("detalle_receta", kwargs={"codigo": receta.codigo})
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["costo_estimado"] is None
    
    # Ahora cambiar cantidad a valor curado y verificar cálculo
    ri.cantidad = Decimal("100.00")
    ri.save()
    
    response = client.get(url)
    assert response.status_code == 200
    # Costo: 100 * 10 = 1000. Escala: 1000 * (4 / 4) = 1000.00
    assert response.context["costo_estimado"] == Decimal("1000.00")

@pytest.mark.django_db
def test_calcular_costo_semanal_no_disponible_con_cantidad_null():
    user = UsuarioFactory(tamano_familia=4)
    receta = Receta.objects.create(
        codigo="C002", nombre="Receta de prueba 2", porciones_base=4, calorias_por_porcion=200,
        nivel_costo="ME"
    )
    ingrediente = Ingrediente.objects.create(
        nombre="Ingrediente Y", categoria_nutricional="CER", unidad_medida="gramos",
        origen="NAC", nivel_costo="ME", precio_actual=Decimal("5.00")
    )
    ri = RecetaIngrediente.objects.create(
        fk_receta=receta, fk_ingrediente=ingrediente, cantidad=None
    )
    
    # Crear planificación en menú semanal
    from planificacion.models import MenuSemanal
    lunes = datetime.date.today()
    MenuSemanal.objects.create(
        fk_usuario=user, fk_receta=receta, fecha=lunes, momento="DESAYUNO"
    )
    
    # Calcular costo semanal
    costo = calcular_costo_semanal(user, lunes, lunes)
    assert costo is None
    
    # Curar cantidad del ingrediente
    ri.cantidad = Decimal("2.00")
    ri.save()
    
    costo = calcular_costo_semanal(user, lunes, lunes)
    # Costo: 2 * 5 = 10. Escala: 10 * (4 / 4) = 10.00
    assert costo == Decimal("10.00")
