import json
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from catalogo.models import Receta, Ingrediente
from .models import MenuSemanal, ListaCompra, ItemListaCompra
from .sync import sincronizar_lista_compras


def get_current_week_dates():
    """
    Retorna la lista de fechas de la semana actual, desde el lunes hasta el domingo.
    """
    today = datetime.date.today()
    # Lunes de la semana actual
    start_of_week = today - datetime.timedelta(days=today.weekday())
    dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    dates = []
    
    for i in range(7):
        date_val = start_of_week + datetime.timedelta(days=i)
        dates.append({
            'nombre': dias_nombres[i],
            'fecha': date_val,
            'fecha_str': date_val.isoformat(),
        })
    return dates


def calcular_costo_semanal(user, start_date, end_date):
    """
    Calcula el costo total del menú semanal del usuario.
    Si alguna receta contiene ingredientes sin cantidad curada (NULL), retorna None (no disponible).
    """
    menus = MenuSemanal.objects.filter(
        fk_usuario=user,
        fecha__range=[start_date, end_date]
    ).select_related('fk_receta')

    costo_total = Decimal('0.00')
    no_disponible = False

    for menu in menus:
        receta = menu.fk_receta
        ingredientes_receta = receta.recetaingrediente_set.all()

        if not ingredientes_receta.exists():
            no_disponible = True
            break

        receta_costo = Decimal('0.00')
        curacion_pendiente = False
        
        for ri in ingredientes_receta:
            if ri.cantidad is None:
                curacion_pendiente = True
                break
            receta_costo += ri.cantidad * ri.fk_ingrediente.precio_actual

        if curacion_pendiente:
            no_disponible = True
            break

        # Escalar según porciones base y tamaño familiar
        factor = Decimal(user.tamano_familia) / Decimal(receta.porciones_base)
        costo_total += receta_costo * factor

    if no_disponible:
        return None
    return costo_total.quantize(Decimal('0.01'))


@login_required
def dashboard(request):
    """
    Dashboard del usuario: muestra el resumen del presupuesto familiar y el menú de la semana.
    """
    dates = get_current_week_dates()
    start_date = dates[0]['fecha']
    end_date = dates[-1]['fecha']

    costo_acumulado = calcular_costo_semanal(request.user, start_date, end_date)
    presupuesto_semanal = request.user.presupuesto_semanal

    sobrepasado = False
    presupuesto_restante = None
    porcentaje_presupuesto = 0

    if costo_acumulado is not None:
        presupuesto_restante = (presupuesto_semanal - costo_acumulado).quantize(Decimal('0.01'))
        if costo_acumulado > presupuesto_semanal:
            sobrepasado = True
        
        if presupuesto_semanal > 0:
            porcentaje_presupuesto = int((costo_acumulado / presupuesto_semanal) * 100)
            if porcentaje_presupuesto > 100:
                porcentaje_presupuesto = 100

    # Obtener menús de la semana
    menus = MenuSemanal.objects.filter(
        fk_usuario=request.user,
        fecha__range=[start_date, end_date]
    ).select_related('fk_receta').order_by('fecha', 'momento')

    # Verificar si hay una lista de compras existente
    lista_compras_existe = ListaCompra.objects.filter(fk_usuario=request.user).exists()

    return render(request, 'planificacion/dashboard.html', {
        'costo_acumulado': costo_acumulado,
        'presupuesto_restante': presupuesto_restante,
        'porcentaje_presupuesto': porcentaje_presupuesto,
        'sobrepasado': sobrepasado,
        'menus': menus,
        'lista_compras_existe': lista_compras_existe,
        'dates': dates,
    })


@login_required
def menu_semanal(request):
    """
    Grid de planificación semanal de comidas.
    """
    dates = get_current_week_dates()
    start_date = dates[0]['fecha']
    end_date = dates[-1]['fecha']

    # Obtener recetas para dropdowns
    recetas_disponibles = Receta.objects.all().order_by('nombre')

    # Obtener ingredientes para dropdowns
    ingredientes_disponibles = Ingrediente.objects.all().order_by('nombre')

    # Obtener menús de la semana actual
    menus = MenuSemanal.objects.filter(
        fk_usuario=request.user,
        fecha__range=[start_date, end_date]
    ).select_related('fk_receta')

    menu_slots = {}
    for m in menus:
        menu_slots[(m.fecha.isoformat(), m.momento)] = m

    # Obtener ingredientes individuales planificados para la semana actual
    ingredientes_semanales = IngredienteSemanal.objects.filter(
        fk_usuario=request.user,
        fecha__range=[start_date, end_date]
    ).select_related('fk_ingrediente')

    ingrediente_slots = {}
    for ing_sem in ingredientes_semanales:
        ingrediente_slots[(ing_sem.fecha.isoformat(), ing_sem.momento, ing_sem.fk_ingrediente.pk)] = ing_sem

    # Construir grilla mapeada
    grid = []
    for day in dates:
        row = {
            'nombre': day['nombre'],
            'fecha': day['fecha'],
            'fecha_str': day['fecha_str'],
            'slots': []
        }
        for momento_code, momento_label in MenuSemanal.MOMENTOS:
            menu_entry = menu_slots.get((day['fecha_str'], momento_code))
            
            # Obtener todos los ingredientes individuales para este slot
            ingredientes_en_slot = [
                ing_sem for (fecha_str, momento, ing_pk), ing_sem in ingrediente_slots.items()
                if fecha_str == day['fecha_str'] and momento == momento_code
            ]

            row['slots'].append({
                'momento_code': momento_code,
                'momento_label': momento_label,
                'menu_entry': menu_entry,
                'ingredientes_en_slot': ingredientes_en_slot,
            })
        grid.append(row)

    return render(request, 'planificacion/menu_semanal.html', {
        'grid': grid,
        'recetas': recetas_disponibles,
        'ingredientes': ingredientes_disponibles,
        'momentos': MenuSemanal.MOMENTOS,
    })


@login_required
def render_add_to_selection_form(request, receta_id):
    """
    Endpoint HTMX para renderizar el formulario de selección de fecha y momento
    para agregar una receta al menú semanal.
    """
    receta = get_object_or_404(Receta, pk=receta_id)
    dates = get_current_week_dates()
    
    return render(request, 'planificacion/partials/_add_to_selection_form.html', {
        'receta': receta,
        'dates': dates,
        'momentos': MenuSemanal.MOMENTOS,
    })


@login_required
@require_POST
def agregar_menu_semanal_htmx(request):
    """
    Endpoint HTMX para agregar una receta al menú semanal.
    Retorna un mensaje de éxito o error para ser intercambiado en el DOM.
    """
    receta_id = request.POST.get('recet-id') # Usamos 'recet-id' del hidden input
    fecha_str = request.POST.get('fecha')
    momento = request.POST.get('momento')

    if not all([receta_id, fecha_str, momento]):
        return HttpResponse(
            '<div class="p-3 bg-red-50 border border-error text-error text-xs font-bold rounded-lg mb-2">Error: Faltan parámetros requeridos.</div>',
            status=400
        )

    try:
        fecha = datetime.date.fromisoformat(fecha_str)
        receta = get_object_or_404(Receta, pk=receta_id)
    except (ValueError, Receta.DoesNotExist):
        return HttpResponse(
            '<div class="p-3 bg-red-50 border border-error text-error text-xs font-bold rounded-lg mb-2">Error: Receta o fecha inválida.</div>',
            status=400
        )

    # Validar duplicación del slot
    if MenuSemanal.objects.filter(fk_usuario=request.user, fecha=fecha, momento=momento).exists():
        return HttpResponse(
            '<div class="p-3 bg-red-50 border border-error text-error text-xs font-bold rounded-lg mb-2">Ya tienes planificada una receta en esta fecha y momento.</div>',
            status=400
        )

    MenuSemanal.objects.create(
        fk_usuario=request.user,
        fk_receta=receta,
        fecha=fecha,
        momento=momento
    )
    
    # Retornar un mensaje de éxito y el formulario vacío para permitir agregar otra receta
    return HttpResponse(
        f'<div class="p-3 bg-green-50 border border-exito text-exito text-xs font-bold rounded-lg mb-2">¡{receta.nombre} agregada al menú!</div>'
        '<p class="text-xs text-gray-500">Selecciona una receta para agregarla a tu menú semanal.</p>'
    )


@login_required
@require_POST
def agregar_menu_semanal(request):
    """
    Endpoint para agregar una receta al menú semanal.
    Si ya existe una receta en el mismo día y momento, retorna un mensaje de error legible.
    """
    fecha_str = request.POST.get('fecha')
    momento = request.POST.get('momento')
    receta_id = request.POST.get('receta_id')

    if not fecha_str or not momento or not receta_id:
        messages.error(request, "Faltan parámetros requeridos.")
        return redirect('menu_semanal')

    try:
        fecha = datetime.date.fromisoformat(fecha_str)
        receta = get_object_or_404(Receta, pk=receta_id)
    except ValueError:
        messages.error(request, "Fecha inválida.")
        return redirect('menu_semanal')

    # Validar duplicación del slot
    if MenuSemanal.objects.filter(fk_usuario=request.user, fecha=fecha, momento=momento).exists():
        # Si es petición HTMX, retornar error legible en HTML
        if request.headers.get('HX-Request') == 'true':
            return HttpResponse(
                '<div class="p-3 bg-red-50 border border-error text-error text-xs font-bold rounded-lg mb-2">Ya tienes planificada una receta en esta fecha y momento.</div>',
                status=400
            )
        messages.error(request, "Ya tienes planificada una receta en esta fecha y momento.")
        return redirect('menu_semanal')

    MenuSemanal.objects.create(
        fk_usuario=request.user,
        fk_receta=receta,
        fecha=fecha,
        momento=momento
    )

    if request.headers.get('HX-Request') == 'true':
        # HTMX se encarga de recargar la grilla redireccionando o actualizando
        return HttpResponse('<script>window.location.reload();</script>')

    messages.success(request, f"Se agregó {receta.nombre} a tu menú.")
    return redirect('menu_semanal')


@login_required
@require_POST
def agregar_ingrediente_semanal_htmx(request):
    """
    Endpoint HTMX para agregar un ingrediente individual al menú semanal.
    """
    ingrediente_id = request.POST.get('ingrediente_id')
    fecha_str = request.POST.get('fecha')
    momento = request.POST.get('momento')
    cantidad = request.POST.get('cantidad')

    if not all([ingrediente_id, fecha_str, momento, cantidad]):
        return HttpResponse(
            '<div class="p-3 bg-red-50 border border-error text-error text-xs font-bold rounded-lg mb-2">Error: Faltan parámetros requeridos.</div>',
            status=400
        )

    try:
        fecha = datetime.date.fromisoformat(fecha_str)
        ingrediente = get_object_or_404(Ingrediente, pk=ingrediente_id)
        cantidad_decimal = Decimal(cantidad)
        if cantidad_decimal <= 0:
            raise ValueError("La cantidad debe ser mayor que cero.")
    except (ValueError, Ingrediente.DoesNotExist):
        return HttpResponse(
            '<div class="p-3 bg-red-50 border border-error text-error text-xs font-bold rounded-lg mb-2">Error: Ingrediente, fecha o cantidad inválida.</div>',
            status=400
        )

    # Validar duplicación del slot para el mismo ingrediente
    if IngredienteSemanal.objects.filter(fk_usuario=request.user, fk_ingrediente=ingrediente, fecha=fecha, momento=momento).exists():
        return HttpResponse(
            '<div class="p-3 bg-red-50 border border-error text-error text-xs font-bold rounded-lg mb-2">Ya tienes este ingrediente planificado en esta fecha y momento.</div>',
            status=400
        )

    IngredienteSemanal.objects.create(
        fk_usuario=request.user,
        fk_ingrediente=ingrediente,
        fecha=fecha,
        momento=momento,
        cantidad=cantidad_decimal
    )
    
    return HttpResponse(
        f'<div class="p-3 bg-green-50 border border-exito text-exito text-xs font-bold rounded-lg mb-2">¡{ingrediente.nombre} agregado al menú!</div>'
    )


@login_required
@require_POST
def remover_ingrediente_semanal_htmx(request, pk):
    """
    Endpoint HTMX para remover un ingrediente individual del menú semanal.
    """
    ingrediente_sem = get_object_or_404(IngredienteSemanal, pk=pk, fk_usuario=request.user)
    nombre_ingrediente = ingrediente_sem.fk_ingrediente.nombre
    ingrediente_sem.delete()

    return HttpResponse(
        f'<div class="p-3 bg-green-50 border border-exito text-exito text-xs font-bold rounded-lg mb-2">¡{nombre_ingrediente} eliminado del menú!</div>'
    )


@login_required
@require_POST
def remover_menu_semanal(request, pk):
    """
    Endpoint para remover una receta del menú semanal.
    """
    menu = get_object_or_404(MenuSemanal, pk=pk, fk_usuario=request.user)
    nombre_receta = menu.fk_receta.nombre
    menu.delete()

    if request.headers.get('HX-Request') == 'true':
        return HttpResponse('<script>window.location.reload();</script>')

    messages.success(request, f"Se eliminó {nombre_receta} de tu menú.")
    return redirect('menu_semanal')


@login_required
@require_POST
def generar_lista_compra(request):
    """
    Genera la lista de compras consolidando los ingredientes de todo el menú semanal
    escalados según el tamaño del grupo familiar del usuario.
    """
    dates = get_current_week_dates()
    start_date = dates[0]['fecha']
    end_date = dates[-1]['fecha']

    menus = MenuSemanal.objects.filter(
        fk_usuario=request.user,
        fecha__range=[start_date, end_date]
    ).select_related('fk_receta')

    if not menus.exists():
        messages.error(request, "No tienes comidas planificadas en tu menú para esta semana.")
        return redirect('menu_semanal')

    with transaction.atomic():
        # Limpiar lista anterior
        ListaCompra.objects.filter(fk_usuario=request.user).delete()

        # Crear nueva cabecera de lista
        lista = ListaCompra.objects.create(fk_usuario=request.user)

        # Consolidar ingredientes de recetas
        for menu in menus:
            receta = menu.fk_receta
            receta_ingredientes = receta.recetaingrediente_set.select_related('fk_ingrediente').all()

            for ri in receta_ingredientes:
                ingrediente = ri.fk_ingrediente
                
                # Si cantidad es NULL (v1 sin curar), consolidamos como 0.00
                cantidad_original = ri.cantidad if ri.cantidad is not None else Decimal('0.00')
                factor = Decimal(request.user.tamano_familia) / Decimal(receta.porciones_base)
                cantidad_escalada = cantidad_original * factor

                if ingrediente.id in consolidado:
                    consolidado[ingrediente.id]['cantidad'] += cantidad_escalada
                else:
                    consolidado[ingrediente.id] = {
                        'ingrediente': ingrediente,
                        'cantidad': cantidad_escalada
                    }

        # Consolidar ingredientes individuales del plan semanal
        ingredientes_semanales = IngredienteSemanal.objects.filter(
            fk_usuario=request.user,
            fecha__range=[start_date, end_date]
        ).select_related('fk_ingrediente')

        for ing_sem in ingredientes_semanales:
            ingrediente = ing_sem.fk_ingrediente
            cantidad_individual = ing_sem.cantidad * request.user.tamano_familia # Escalar por tamaño de familia

            if ingrediente.id in consolidado:
                consolidado[ingrediente.id]['cantidad'] += cantidad_individual
            else:
                consolidado[ingrediente.id] = {
                    'ingrediente': ingrediente,
                    'cantidad': cantidad_individual
                }

        # Guardar ítems de la lista
        for ing_id, data in consolidado.items():
            ItemListaCompra.objects.create(
                fk_lista=lista,
                fk_ingrediente=data['ingrediente'],
                cantidad_total=data['cantidad'].quantize(Decimal('0.01')),
                estado='PENDIENTE'
            )

    messages.success(request, "Lista de compras generada y consolidada con éxito.")
    return redirect('lista_compra')


@login_required
def lista_compra(request):
    """
    Muestra la lista de compras del usuario agrupada por categoría nutricional.
    """
    lista = ListaCompra.objects.filter(fk_usuario=request.user).first()
    
    items_por_categoria = {}
    
    if lista:
        items = lista.items.select_related('fk_ingrediente').order_by('fk_ingrediente__nombre')
        for item in items:
            cat_display = item.fk_ingrediente.get_categoria_nutricional_display()
            if cat_display not in items_por_categoria:
                items_por_categoria[cat_display] = []
            items_por_categoria[cat_display].append(item)

    return render(request, 'planificacion/lista_compra.html', {
        'lista': lista,
        'items_por_categoria': items_por_categoria,
    })


@login_required
@require_POST
def cambiar_estado_item(request, pk):
    """
    Endpoint HTMX para cambiar el estado (Pendiente / Comprado) de un ítem de la lista.
    Retorna únicamente el fragmento del ítem actualizado.
    """
    item = get_object_or_404(ItemListaCompra, pk=pk, fk_lista__fk_usuario=request.user)
    
    item.estado = 'COMPRADO' if item.estado == 'PENDIENTE' else 'PENDIENTE'
    item.save()

    return render(request, 'planificacion/partials/_item_compra.html', {'item': item})


@csrf_exempt
@login_required
@require_POST
def sync_lista_compra(request):
    """
    Endpoint para sincronización bidireccional offline/online de la lista de compras.
    """
    try:
        data = json.loads(request.body)
        client_items = data.get('items', [])
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'JSON inválido'}, status=400)

    # Procesar reconciliación por marcas de tiempo
    sincronizar_lista_compras(request.user, client_items)

    # Obtener el estado consolidado del servidor para responderle al cliente
    lista = ListaCompra.objects.filter(fk_usuario=request.user).first()
    items_response = []

    if lista:
        for item in lista.items.select_related('fk_ingrediente').all():
            items_response.append({
                'item_id': item.id,
                'estado': item.estado,
                'actualizado_at': item.actualizado_at.isoformat() + 'Z'
            })

    # Actualizar fecha de sincronización de la cabecera
    if lista:
        lista.sincronizada_at = timezone.now()
        lista.save()

    return JsonResponse({
        'status': 'success',
        'items': items_response
    })
