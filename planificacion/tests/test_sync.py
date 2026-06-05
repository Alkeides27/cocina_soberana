import pytest
import json
import datetime
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from catalogo.models import Ingrediente
from planificacion.models import ListaCompra, ItemListaCompra
from usuarios.tests.factories import UsuarioFactory

@pytest.mark.django_db
def test_sync_conflict_resolution_by_timestamp(client):
    user = UsuarioFactory()
    client.force_login(user)
    
    # Crear lista de compras y un item
    lista = ListaCompra.objects.create(fk_usuario=user)
    ing = Ingrediente.objects.create(
        nombre="Ingrediente Z", categoria_nutricional="CER", unidad_medida="gramos",
        origen="NAC", nivel_costo="ME"
    )
    
    # Item inicial: PENDIENTE
    item = ItemListaCompra.objects.create(
        fk_lista=lista, fk_ingrediente=ing, cantidad_total=Decimal("100.00"), estado="PENDIENTE"
    )
    
    # Obtener el timestamp inicial del servidor
    time_inicial = item.actualizado_at
    
    # 1. Conflicto Caso A: Cliente envía actualización con timestamp ANTERIOR
    time_anterior = (time_inicial - datetime.timedelta(minutes=10)).isoformat()
    
    payload_anterior = {
        "items": [
            {
                "item_id": item.id,
                "estado": "COMPRADO",
                "actualizado_at": time_anterior
            }
        ]
    }
    
    url = reverse("sync_lista_compra")
    response = client.post(
        url,
        json.dumps(payload_anterior),
        content_type="application/json"
    )
    assert response.status_code == 200
    
    # El servidor debió descartar la actualización por ser más antigua que la del servidor
    item.refresh_from_db()
    assert item.estado == "PENDIENTE"

    # 2. Conflicto Caso B: Cliente envía actualización con timestamp POSTERIOR
    time_posterior = (time_inicial + datetime.timedelta(minutes=10)).isoformat()
    
    payload_posterior = {
        "items": [
            {
                "item_id": item.id,
                "estado": "COMPRADO",
                "actualizado_at": time_posterior
            }
        ]
    }
    
    response = client.post(
        url,
        json.dumps(payload_posterior),
        content_type="application/json"
    )
    assert response.status_code == 200
    
    # El servidor debió aceptar la actualización porque el cliente tiene un timestamp más reciente
    item.refresh_from_db()
    assert item.estado == "COMPRADO"
