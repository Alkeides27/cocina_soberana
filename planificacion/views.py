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
from .models import MenuSemanal, ListaCompra, ItemListaCompra, IngredienteSemanal
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
    Calcula el costo total del menú semanal del usuario consolidando todos los ingredientes
    y estimando el costo en base a paquetes comerciales enteros (math.ceil).
    Si alguna receta contiene ingredientes sin cantidad curada (NULL), retorna None (no disponible).
    """
    import math
    from collections import defaultdict
    from .models import MenuSemanal, IngredienteSemanal
    
    menus = MenuSemanal.objects.filter(
        fk_usuario=user,
        fecha__range=[start_date, end_date]
    ).select_related('fk_receta')
    
    ingredientes_semanales = IngredienteSemanal.objects.filter(
        fk_usuario=user,
        fecha__range=[start_date, end_date]
    ).select_related('fk_ingrediente')
    
    # Si no hay planificación alguna, el costo acumulado es 0
    if not menus.exists() and not ingredientes_semanales.exists():
        return Decimal('0.00')
        
    consolidado = defaultdict(Decimal)
    ingredientes_obj = {}
    
    # Consolidar ingredientes de recetas
    for menu in menus:
        receta = menu.fk_receta
        receta_ingredientes = receta.recetaingrediente_set.select_related('fk_ingrediente').all()
        
        if not receta_ingredientes.exists():
            return None
            
        for ri in receta_ingredientes:
            if ri.cantidad is None:
                return None
            
            ingrediente = ri.fk_ingrediente
            factor = Decimal(user.tamano_familia) / Decimal(receta.porciones_base)
            cantidad_escalada = ri.cantidad * factor
            
            consolidado[ingrediente.id] += cantidad_escalada
            ingredientes_obj[ingrediente.id] = ingrediente
            
    # Consolidar ingredientes individuales
    for ing_sem in ingredientes_semanales:
        ingrediente = ing_sem.fk_ingrediente
        cantidad_individual = ing_sem.cantidad * Decimal(user.tamano_familia)
        consolidado[ingrediente.id] += cantidad_individual
        ingredientes_obj[ingrediente.id] = ingrediente
        
    # Calcular costo basado en paquetes comerciales enteros
    costo_total = Decimal('0.00')
    for ing_id, cantidad in consolidado.items():
        ing = ingredientes_obj[ing_id]
        presentacion = ing.presentacion_comercial or Decimal('1.00')
        
        # Redondear hacia arriba para obtener paquetes comerciales enteros
        paquetes = math.ceil(float(cantidad) / float(presentacion))
        costo_paquete = ing.calcular_costo(presentacion)
        costo_total += Decimal(str(paquetes)) * costo_paquete
        
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

    # Obtener recetas para dropdowns filtradas por categoría
    categoria_slug = request.GET.get('categoria', 'todos')
    if categoria_slug == 'todos' or not categoria_slug:
        recetas_disponibles = Receta.objects.all().order_by('nombre')
    else:
        recetas_disponibles = Receta.objects.filter(categorias__slug=categoria_slug).order_by('nombre')

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
                'fecha_str': day['fecha_str'],  # necesario para el ID único del <td> en _slot_celda.html
            })
        grid.append(row)

    # Calcular presupuesto acumulado
    costo_acumulado = calcular_costo_semanal(request.user, start_date, end_date)
    presupuesto_semanal = request.user.presupuesto_semanal
    sobrepasado = False
    presupuesto_restante = Decimal('0.00')
    if costo_acumulado is not None:
        presupuesto_restante = presupuesto_semanal - costo_acumulado
        sobrepasado = costo_acumulado > presupuesto_semanal

    CATEGORIAS_FILTRO = [
        ('todos', 'Todos'),
        ('desayuno', 'Desayunos'),
        ('almuerzo', 'Almuerzos'),
        ('cena', 'Cenas'),
        ('merienda', 'Meriendas'),
        ('sopa', 'Sopas'),
        ('postre', 'Postres'),
    ]

    return render(request, 'planificacion/menu_semanal.html', {
        'grid': grid,
        'recetas': recetas_disponibles,
        'ingredientes': ingredientes_disponibles,
        'momentos': MenuSemanal.MOMENTOS,
        'costo_acumulado': costo_acumulado,
        'presupuesto_restante': presupuesto_restante,
        'sobrepasado': sobrepasado,
        'categoria_actual': categoria_slug,
        'categorias_list': CATEGORIAS_FILTRO,
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

def render_planner_content(request, categoria_slug=None):
    """
    Helper para obtener el fragmento de planificación renderizado listo para HTMX.
    """
    from django.template.loader import render_to_string
    dates = get_current_week_dates()
    start_date = dates[0]['fecha']
    end_date = dates[-1]['fecha']

    if not categoria_slug:
        categoria_slug = request.GET.get('categoria') or request.POST.get('categoria') or 'todos'

    if categoria_slug == 'todos' or not categoria_slug:
        recetas_disponibles = Receta.objects.all().order_by('nombre')
    else:
        recetas_disponibles = Receta.objects.filter(categorias__slug=categoria_slug).order_by('nombre')

    ingredientes_disponibles = Ingrediente.objects.all().order_by('nombre')

    menus = MenuSemanal.objects.filter(
        fk_usuario=request.user,
        fecha__range=[start_date, end_date]
    ).select_related('fk_receta')

    menu_slots = {}
    for m in menus:
        menu_slots[(m.fecha.isoformat(), m.momento)] = m

    ingredientes_semanales = IngredienteSemanal.objects.filter(
        fk_usuario=request.user,
        fecha__range=[start_date, end_date]
    ).select_related('fk_ingrediente')

    ingrediente_slots = {}
    for ing_sem in ingredientes_semanales:
        ingrediente_slots[(ing_sem.fecha.isoformat(), ing_sem.momento, ing_sem.fk_ingrediente.pk)] = ing_sem

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
            ingredientes_en_slot = [
                ing_sem for (fecha_str, momento, ing_pk), ing_sem in ingrediente_slots.items()
                if fecha_str == day['fecha_str'] and momento == momento_code
            ]
            row['slots'].append({
                'momento_code': momento_code,
                'momento_label': momento_label,
                'menu_entry': menu_entry,
                'ingredientes_en_slot': ingredientes_en_slot,
                'fecha_str': day['fecha_str'],
            })
        grid.append(row)

    costo_acumulado = calcular_costo_semanal(request.user, start_date, end_date)
    presupuesto_semanal = request.user.presupuesto_semanal
    sobrepasado = False
    presupuesto_restante = Decimal('0.00')
    if costo_acumulado is not None:
        presupuesto_restante = presupuesto_semanal - costo_acumulado
        sobrepasado = costo_acumulado > presupuesto_semanal

    CATEGORIAS_FILTRO = [
        ('todos', 'Todos'),
        ('desayuno', 'Desayunos'),
        ('almuerzo', 'Almuerzos'),
        ('cena', 'Cenas'),
        ('merienda', 'Meriendas'),
        ('sopa', 'Sopas'),
        ('postre', 'Postres'),
    ]

    html_content = render_to_string('planificacion/partials/_planner_content.html', {
        'grid': grid,
        'recetas': recetas_disponibles,
        'ingredientes': ingredientes_disponibles,
        'momentos': MenuSemanal.MOMENTOS,
        'costo_acumulado': costo_acumulado,
        'presupuesto_restante': presupuesto_restante,
        'sobrepasado': sobrepasado,
        'user': request.user,
        'categoria_actual': categoria_slug,
        'categorias_list': CATEGORIAS_FILTRO,
    }, request=request)
    
    return HttpResponse(html_content)


@login_required
def menu_semanal_content(request):
    """
    Endpoint HTMX para recargar la grilla y el presupuesto.
    """
    return render_planner_content(request)


@login_required
def filtrar_recetas_categoria(request):
    """
    Endpoint HTMX para filtrar las recetas del planificador por categoría.
    Retorna un fragmento con los <option> filtrados y un script para inyectarlos
    en todas las celdas vacías sin necesidad de re-renderizar la grilla completa.
    """
    categoria_slug = request.GET.get('categoria', 'todos')
    
    if categoria_slug == 'todos' or not categoria_slug:
        recetas = Receta.objects.all().order_by('nombre')
    else:
        recetas = Receta.objects.filter(categorias__slug=categoria_slug).order_by('nombre')
        
    return render(request, 'planificacion/partials/_opciones_receta.html', {
        'recetas': recetas,
        'categoria_actual': categoria_slug
    })



@login_required
@require_POST
def agregar_menu_semanal_slot(request):
    """
    Endpoint HTMX para agregar una receta al menú desde la grilla del planificador.
    Devuelve el contenido completo actualizado del planificador para re-renderizado SPA sin fallos de parseo.
    """
    fecha_str = request.POST.get('fecha')
    momento = request.POST.get('momento')
    receta_id = request.POST.get('receta_id')

    if not fecha_str or not momento or not receta_id:
        return HttpResponse(
            '<div class="p-4 align-top text-xs text-error font-bold">Error: faltan parámetros.</div>',
            status=400
        )

    try:
        fecha = datetime.date.fromisoformat(fecha_str)
        receta = get_object_or_404(Receta, pk=receta_id)
    except ValueError:
        return HttpResponse(
            '<div class="p-4 align-top text-xs text-error font-bold">Error: fecha inválida.</div>',
            status=400
        )

    # Crear si no existe (silencioso si ya está ocupado el slot)
    MenuSemanal.objects.get_or_create(
        fk_usuario=request.user,
        fecha=fecha,
        momento=momento,
        defaults={'fk_receta': receta}
    )

    return render_planner_content(request)


@login_required
@require_POST
def agregar_menu_semanal_htmx(request):
    """
    Endpoint HTMX para agregar una receta al menú semanal desde el catálogo (panel lateral).
    Retorna el formulario reiniciado + mensaje de éxito para mantener el botón activo.
    """
    receta_id = request.POST.get('recet-id')  # 'recet-id' viene del hidden input del partial
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

    # Devolvemos el formulario completo reiniciado + mensaje de éxito temporal
    dates = get_current_week_dates()
    success_html = (
        f'<div class="p-2 bg-green-50 border border-exito text-exito text-xs font-bold rounded-lg mb-3">'
        f'✓ {receta.nombre} agregada al menú'
        f'</div>'
    )
    from django.template.loader import render_to_string
    form_html = render_to_string(
        'planificacion/partials/_add_to_selection_form.html',
        {'receta': receta, 'dates': dates, 'momentos': MenuSemanal.MOMENTOS},
        request=request,
    )
    return HttpResponse(success_html + form_html)


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
    
    success_msg = f'<div class="p-3 bg-green-50 border border-exito text-exito text-xs font-bold rounded-lg mb-2">¡{ingrediente.nombre} agregado al menú!</div>'
    
    response = HttpResponse(success_msg)
    response['HX-Trigger'] = 'updatePlanner'
    return response



@login_required
def render_add_ingrediente_form(request):
    """
    Endpoint HTMX para renderizar el formulario de selección de fecha, momento,
    ingrediente y cantidad para agregar un ingrediente individual al menú semanal.
    """
    dates = get_current_week_dates()
    ingredientes_disponibles = Ingrediente.objects.all().order_by('nombre')
    
    return render(request, 'planificacion/partials/_add_ingrediente_form.html', {
        'dates': dates,
        'ingredientes': ingredientes_disponibles,
        'momentos': MenuSemanal.MOMENTOS,
    })


@login_required
@require_POST
def remover_ingrediente_semanal_htmx(request, pk):
    """
    Endpoint HTMX para remover un ingrediente individual del menú semanal.
    Devuelve el planificador completo actualizado.
    """
    ingrediente_sem = get_object_or_404(IngredienteSemanal, pk=pk, fk_usuario=request.user)
    ingrediente_sem.delete()

    return render_planner_content(request)


@login_required
@require_POST
def remover_menu_semanal(request, pk):
    """
    Endpoint para remover una receta del menú semanal.
    Si viene de HTMX, devuelve el planificador completo actualizado.
    """
    menu = get_object_or_404(MenuSemanal, pk=pk, fk_usuario=request.user)
    nombre_receta = menu.fk_receta.nombre
    menu.delete()

    if request.headers.get('HX-Request') == 'true':
        return render_planner_content(request)

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

        # Consolidar ingredientes
        consolidado = {}

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
    Cada ítem incluye `paquetes_necesarios` calculado a partir de `presentacion_comercial`.
    """
    import math
    lista = ListaCompra.objects.filter(fk_usuario=request.user).first()

    items_por_categoria = {}

    if lista:
        items = lista.items.select_related('fk_ingrediente').order_by('fk_ingrediente__nombre')
        for item in items:
            # Calcular cuántas unidades comerciales hay que comprar
            presentacion = item.fk_ingrediente.presentacion_comercial or Decimal('1')
            paquetes = math.ceil(float(item.cantidad_total) / float(presentacion))
            item.paquetes_necesarios = paquetes

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
def vaciar_lista_compra(request):
    """
    Elimina todos los ítems de la lista de compras del usuario.
    Protegido por hx-confirm en el template para evitar borrados accidentales.
    """
    ListaCompra.objects.filter(fk_usuario=request.user).delete()
    messages.success(request, "Lista de compras vaciada correctamente.")
    if request.headers.get('HX-Request') == 'true':
        response = HttpResponse()
        response['HX-Redirect'] = request.path.replace('vaciar/', '')
        return response
    return redirect('lista_compra')



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


@login_required
@require_POST
def vaciar_planificacion(request):
    """
    Elimina todas las recetas e ingredientes planificados de la semana actual,
    y también elimina la lista de compras del usuario si existe.
    Retorna el parcial _planner_content.html vacío con presupuesto a cero.
    """
    dates = get_current_week_dates()
    start_date = dates[0]['fecha']
    end_date = dates[-1]['fecha']
    
    # 1. Eliminar planificación de la semana
    MenuSemanal.objects.filter(
        fk_usuario=request.user,
        fecha__range=[start_date, end_date]
    ).delete()
    
    IngredienteSemanal.objects.filter(
        fk_usuario=request.user,
        fecha__range=[start_date, end_date]
    ).delete()
    
    # 2. Eliminar lista de compras vinculada (para evitar estado corrupto)
    ListaCompra.objects.filter(fk_usuario=request.user).delete()
    
    # 3. Preparar variables para re-renderizar la vista limpia
    recetas_disponibles = Receta.objects.all().order_by('nombre')
    ingredientes_disponibles = Ingrediente.objects.all().order_by('nombre')
    
    # Construir grilla vacía
    grid = []
    for day in dates:
        row = {
            'nombre': day['nombre'],
            'fecha': day['fecha'],
            'fecha_str': day['fecha_str'],
            'slots': []
        }
        for momento_code, momento_label in MenuSemanal.MOMENTOS:
            row['slots'].append({
                'momento_code': momento_code,
                'momento_label': momento_label,
                'menu_entry': None,
                'ingredientes_en_slot': [],
                'fecha_str': day['fecha_str'],
            })
        grid.append(row)
        
    messages.success(request, "Se ha reiniciado la planificación de esta semana.")
    
    # Dado que es HTMX, devolvemos directamente el partial completo
    return render(request, 'planificacion/partials/_planner_content.html', {
        'grid': grid,
        'recetas': recetas_disponibles,
        'ingredientes': ingredientes_disponibles,
        'momentos': MenuSemanal.MOMENTOS,
        'costo_acumulado': Decimal('0.00'),
        'presupuesto_restante': request.user.presupuesto_semanal,
        'sobrepasado': False,
    })


@login_required
@require_POST
def repetir_dia_semana(request):
    """
    Copia toda la planificación (recetas e ingredientes) de un día específico
    al resto de los días de la semana actual, sobrescribiendo los existentes.
    """
    fecha_source_str = request.GET.get('fecha') or request.POST.get('fecha')
    if not fecha_source_str:
        return HttpResponse("Falta la fecha de origen.", status=400)
        
    try:
        fecha_source = datetime.date.fromisoformat(fecha_source_str)
    except ValueError:
        return HttpResponse("Fecha de origen inválida.", status=400)

    dates = get_current_week_dates()

    # Obtener la planificación del día origen
    menus_source = list(MenuSemanal.objects.filter(fk_usuario=request.user, fecha=fecha_source))
    ingredientes_source = list(IngredienteSemanal.objects.filter(fk_usuario=request.user, fecha=fecha_source))

    # Realizar en una transacción atómica
    from django.db import transaction
    with transaction.atomic():
        # 1. Eliminar lista de compras vinculada para forzar regeneración
        ListaCompra.objects.filter(fk_usuario=request.user).delete()

        for day in dates:
            fecha_dest = day['fecha']
            if fecha_dest == fecha_source:
                continue

            # 2. Limpiar planificación destino
            MenuSemanal.objects.filter(fk_usuario=request.user, fecha=fecha_dest).delete()
            IngredienteSemanal.objects.filter(fk_usuario=request.user, fecha=fecha_dest).delete()

            # 3. Copiar recetas
            for m in menus_source:
                MenuSemanal.objects.create(
                    fk_usuario=request.user,
                    fk_receta=m.fk_receta,
                    fecha=fecha_dest,
                    momento=m.momento
                )

            # 4. Copiar ingredientes individuales
            for ing in ingredientes_source:
                IngredienteSemanal.objects.create(
                    fk_usuario=request.user,
                    fk_ingrediente=ing.fk_ingrediente,
                    fecha=fecha_dest,
                    momento=ing.momento,
                    cantidad=ing.cantidad
                )

    messages.success(request, f"Se repitió la planificación del {fecha_source.strftime('%d/%m')} en toda la semana.")

    # Retorna la vista actualizada del planificador
    return render_planner_content(request)


