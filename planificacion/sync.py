from datetime import datetime
from django.utils import timezone
from .models import ItemListaCompra


def sincronizar_lista_compras(user, client_items):
    """
    Sincroniza los ítems modificados sin conexión enviados por el cliente.
    Reconcilia los conflictos comparando el timestamp de última actualización:
    si el del cliente es más reciente, actualiza el servidor; de lo contrario, se descarta.
    """
    for client_item in client_items:
        item_id = client_item.get('item_id')
        estado = client_item.get('estado')
        actualizado_at_str = client_item.get('actualizado_at')
        
        if not item_id or not estado or not actualizado_at_str:
            continue
            
        try:
            ts = actualizado_at_str
            # Si termina en Z y ya contiene un offset (+00:00) en el cuerpo, removemos el Z
            if ts.endswith('Z') and ('+' in ts[:-1] or '-' in ts[:-6]):
                ts = ts[:-1]
                
            if ts.endswith('Z'):
                client_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            else:
                client_time = datetime.fromisoformat(ts)
                
            if timezone.is_naive(client_time):
                client_time = timezone.make_aware(client_time)
        except ValueError:
            # Timestamp inválido, ignorar cambio
            continue
            
        try:
            # Buscar el ítem garantizando que pertenezca al usuario autenticado
            db_item = ItemListaCompra.objects.get(pk=item_id, fk_lista__fk_usuario=user)
            
            # Reconciliación: si la marca del cliente es posterior, actualizamos el servidor
            if client_time > db_item.actualizado_at:
                db_item.estado = estado
                db_item.save()
        except ItemListaCompra.DoesNotExist:
            continue
