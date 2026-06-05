import pytest
from django.urls import reverse
from django.db import IntegrityError
from catalogo.models import Receta
from planificacion.models import MenuSemanal
from usuarios.tests.factories import UsuarioFactory
import datetime

@pytest.mark.django_db
def test_menu_agregar_remover_y_restriccion_duplicados(client):
    user = UsuarioFactory()
    client.force_login(user)
    
    receta1 = Receta.objects.create(
        codigo="M001", nombre="Comida 1", porciones_base=4, calorias_por_porcion=150, nivel_costo="ME"
    )
    receta2 = Receta.objects.create(
        codigo="M002", nombre="Comida 2", porciones_base=4, calorias_por_porcion=250, nivel_costo="ME"
    )
    
    hoy = datetime.date.today()
    hoy_str = hoy.isoformat()
    
    url_agregar = reverse("agregar_menu_semanal")
    
    # 1. Agregar receta exitosamente
    data = {
        "fecha": hoy_str,
        "momento": "DESAYUNO",
        "receta_id": receta1.pk
    }
    response = client.post(url_agregar, data)
    assert response.status_code == 302
    assert MenuSemanal.objects.filter(fk_usuario=user, fecha=hoy, momento="DESAYUNO").exists()
    
    # 2. Intentar agregar en el mismo slot (debe fallar la inserción)
    # Por el lado del backend/views, si se envía una petición normal (no HTMX), redirige con mensaje de error y no duplica
    data2 = {
        "fecha": hoy_str,
        "momento": "DESAYUNO",
        "receta_id": receta2.pk
    }
    response = client.post(url_agregar, data2)
    assert response.status_code == 302
    assert MenuSemanal.objects.filter(fk_usuario=user, fecha=hoy, momento="DESAYUNO").count() == 1
    
    # Si hacemos la petición HTMX, el view retorna código 400 y mensaje
    response_htmx = client.post(url_agregar, data2, HTTP_HX_REQUEST="true")
    assert response_htmx.status_code == 400
    assert "Ya tienes planificada una receta" in response_htmx.content.decode("utf-8")
    
    # Verificar a nivel de base de datos el UniqueConstraint / unique_together
    from django.db import transaction
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            MenuSemanal.objects.create(
                fk_usuario=user,
                fk_receta=receta2,
                fecha=hoy,
                momento="DESAYUNO"
            )
        
    # 3. Remover receta del menú
    menu_entry = MenuSemanal.objects.get(fk_usuario=user, fecha=hoy, momento="DESAYUNO")
    url_remover = reverse("remover_menu_semanal", kwargs={"pk": menu_entry.pk})
    response_remover = client.post(url_remover)
    assert response_remover.status_code == 302
    assert not MenuSemanal.objects.filter(fk_usuario=user, fecha=hoy, momento="DESAYUNO").exists()
