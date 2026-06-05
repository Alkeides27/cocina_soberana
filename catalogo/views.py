from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.core.paginator import Paginator
from decimal import Decimal
from .models import Receta, Categoria
from .filters import filtrar_recetas


class ListaRecetasView(ListView):
    """
    Vista de listado de recetas con paginación integrada y soporte para filtros.
    """
    model = Receta
    template_name = 'catalogo/lista.html'
    context_object_name = 'recetas'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().order_by('codigo')
        return filtrar_recetas(queryset, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.all()
        
        # Mantener los parámetros de filtros para la paginación tradicional
        query_params = self.request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        context['query_params'] = query_params.urlencode()
        context['filtros_activos'] = self.request.GET
        return context


class DetalleRecetaView(DetailView):
    """
    Vista de detalle de receta.
    Muestra los detalles nutricionales, ingredientes, y calcula el costo estimado
    escalado para el tamaño de familia del usuario logueado.
    """
    model = Receta
    template_name = 'catalogo/detalle.html'
    context_object_name = 'receta'
    slug_field = 'codigo'
    slug_url_kwarg = 'codigo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        receta = self.get_object()
        
        # Cargar relaciones con ingredientes eficientemente
        ingredientes_receta = receta.recetaingrediente_set.select_related('fk_ingrediente').all()
        context['ingredientes_receta'] = ingredientes_receta
        
        # Calcular costo estimado de la receta para el usuario actual
        costo_estimado = None
        user = self.request.user
        
        if user.is_authenticated:
            costo_total = Decimal('0.00')
            curacion_pendiente = False
            
            for ri in ingredientes_receta:
                if ri.cantidad is None:
                    # Si al menos un ingrediente tiene cantidad NULL, el costo no está disponible
                    curacion_pendiente = True
                    break
                costo_total += ri.cantidad * ri.fk_ingrediente.precio_actual
            
            # Solo estimar costo si hay cantidades curadas y existen ingredientes
            if not curacion_pendiente and ingredientes_receta.exists():
                factor = Decimal(user.tamano_familia) / Decimal(receta.porciones_base)
                costo_estimado = (costo_total * factor).quantize(Decimal('0.01'))
                
        context['costo_estimado'] = costo_estimado
        return context


def filtrar_recetas_ajax(request):
    """
    Endpoint HTMX para filtrar recetas sin recargar la página.
    Retorna únicamente la sección fragmentada de recetas y paginación.
    """
    queryset = Receta.objects.all().order_by('codigo')
    recetas = filtrar_recetas(queryset, request.GET)
    
    paginator = Paginator(recetas, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
        
    return render(request, 'catalogo/partials/_receta_list_fragment.html', {
        'page_obj': page_obj,
        'query_params': query_params.urlencode(),
    })
