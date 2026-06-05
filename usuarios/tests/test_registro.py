import pytest
from django.urls import reverse
from usuarios.models import Usuario
from usuarios.forms import RegistroForm
from usuarios.tests.factories import UsuarioFactory

@pytest.mark.django_db
def test_registro_exitoso(client):
    url = reverse("registro")
    data = {
        "username": "nuevousuario",
        "email": "nuevo@test.com",
        "nombre": "Nuevo Usuario",
        "tamano_familia": 4,
        "presupuesto_semanal": 100.50,
        "moneda": "USD",
        "password": "SoberanoPass123!",
        "password_confirm": "SoberanoPass123!"
    }
    
    # El RegistroForm requiere password_confirm que en UserCreationForm se llama de cierta forma
    # Pero vamos a validar el comportamiento del form y del post
    form = RegistroForm(data=data)
    # let's verify custom validations / fields
    assert form.fields["nombre"].required is True
    assert form.fields["email"].required is True
    assert form.fields["tamano_familia"].required is True
    assert form.fields["presupuesto_semanal"].required is True

    # Realizar el POST
    # Dado que UserCreationForm usa password1 y password2 para confirmación de contraseña en Django:
    post_data = data.copy()
    post_data["password1"] = "SoberanoPass123!"
    post_data["password2"] = "SoberanoPass123!"
    response = client.post(url, post_data)
    
    assert response.status_code == 302  # Redirección tras registro exitoso
    assert Usuario.objects.filter(username="nuevousuario").exists()
    usuario = Usuario.objects.get(username="nuevousuario")
    assert usuario.email == "nuevo@test.com"
    assert usuario.nombre == "Nuevo Usuario"
    assert usuario.tamano_familia == 4
    assert usuario.presupuesto_semanal == 100.50
    assert usuario.moneda == "USD"

@pytest.mark.django_db
def test_registro_email_duplicado(client):
    # Crear un usuario inicial
    UsuarioFactory(email="repetido@test.com")
    
    url = reverse("registro")
    post_data = {
        "username": "nuevousuario2",
        "email": "repetido@test.com",
        "nombre": "Nuevo Usuario 2",
        "tamano_familia": 3,
        "presupuesto_semanal": 45.00,
        "moneda": "VES",
        "password1": "SoberanoPass123!",
        "password2": "SoberanoPass123!"
    }
    response = client.post(url, post_data)
    assert response.status_code == 200  # Vuelve a renderizar la página con errores
    assert not Usuario.objects.filter(username="nuevousuario2").exists()
