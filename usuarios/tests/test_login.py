import pytest
from django.urls import reverse
from usuarios.tests.factories import UsuarioFactory

@pytest.mark.django_db
def test_login_logout_flow(client):
    user = UsuarioFactory(username="tester", password="SoberanoPass123!")
    
    # Login con credenciales válidas
    url_login = reverse("login")
    response = client.post(url_login, {"username": "tester", "password": "SoberanoPass123!"})
    assert response.status_code == 302  # Redirecciona a LOGIN_REDIRECT_URL
    assert int(client.session["_auth_user_id"]) == user.pk

    # Logout
    url_logout = reverse("logout")
    response = client.post(url_logout)
    assert response.status_code == 302  # Redirecciona a LOGOUT_REDIRECT_URL
    assert "_auth_user_id" not in client.session

@pytest.mark.django_db
def test_login_invalido(client):
    UsuarioFactory(username="tester", password="SoberanoPass123!")
    
    url_login = reverse("login")
    # Credenciales incorrectas
    response = client.post(url_login, {"username": "tester", "password": "wrongpassword"})
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session
