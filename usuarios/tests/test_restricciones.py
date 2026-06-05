import pytest
from django.urls import reverse
from usuarios.models import RestriccionUsuario
from usuarios.tests.factories import UsuarioFactory, RestriccionUsuarioFactory

@pytest.mark.django_db
def test_agregar_restriccion(client):
    user = UsuarioFactory()
    client.force_login(user)
    
    url = reverse("agregar_restriccion")
    data = {
        "tipo": "SIN_GLUTEN",
        "descripcion": "Celíaco grave"
    }
    
    response = client.post(url, data)
    assert response.status_code == 200
    assert RestriccionUsuario.objects.filter(fk_usuario=user, tipo="SIN_GLUTEN").exists()
    
    # Intentar agregar duplicado del mismo tipo (debe omitirlo/no crearlo)
    client.post(url, data)
    assert RestriccionUsuario.objects.filter(fk_usuario=user, tipo="SIN_GLUTEN").count() == 1

@pytest.mark.django_db
def test_eliminar_restriccion(client):
    user = UsuarioFactory()
    restriccion = RestriccionUsuarioFactory(fk_usuario=user, tipo="VEGAN")
    client.force_login(user)
    
    url = reverse("eliminar_restriccion", kwargs={"pk": restriccion.pk})
    response = client.post(url)  # Acepta POST o DELETE
    assert response.status_code == 200
    assert not RestriccionUsuario.objects.filter(pk=restriccion.pk).exists()
