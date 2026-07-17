from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver


class Categoria(models.Model):
    """
    Taxonomía de recetas (ej. Desayuno, Almuerzo, Cena, etc.).
    """
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre de categoría")
    slug = models.SlugField(max_length=50, unique=True, verbose_name="Slug")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self) -> str:
        return self.nombre


class Ingrediente(models.Model):
    """
    Ingredientes del catálogo de Cocina Soberana.
    """
    CATEGORIAS_NUTRICIONALES = [
        ('CER', 'Cereales'),
        ('LEG', 'Leguminosas'),
        ('TUB', 'Tubérculos'),
        ('VEG', 'Vegetales'),
        ('FRU', 'Frutas'),
        ('PRA', 'Proteína Animal'),
        ('HUE', 'Huevos'),
        ('LAC', 'Lácteos'),
        ('GRA', 'Grasas'),
        ('CON', 'Condimentos'),
        ('HIE', 'Hierbas'),
        ('EDU', 'Edulcorantes'),
        ('LIQ', 'Líquidos'),
    ]

    ORIGENES = [
        ('NAC', 'Nacional'),
        ('IMP', 'Importado accesible'),
    ]

    NIVELES_COSTO = [
        ('ME', 'Muy Económico'),
        ('EM', 'Económico Moderado'),
        ('NA', 'No Aplica'),
    ]

    TEMPORADAS = [
        ('TODO', 'Todo el año'),
        ('PRIMAVERA', 'Primavera'),
        ('VERANO', 'Verano'),
        ('OTONO', 'Otoño'),
        ('INVIERNO', 'Invierno'),
    ]

    nombre = models.CharField(max_length=150, unique=True, verbose_name="Nombre")
    categoria_nutricional = models.CharField(
        max_length=3,
        choices=CATEGORIAS_NUTRICIONALES,
        verbose_name="Categoría Nutricional"
    )
    unidad_medida = models.CharField(max_length=20, verbose_name="Unidad de medida")
    origen = models.CharField(max_length=3, choices=ORIGENES, verbose_name="Origen")
    nivel_costo = models.CharField(max_length=2, choices=NIVELES_COSTO, verbose_name="Nivel de costo")
    temporada = models.CharField(
        max_length=10,
        choices=TEMPORADAS,
        default='TODO',
        verbose_name="Temporada"
    )
    precio_actual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Precio actual"
    )
    fecha_precio = models.DateField(null=True, blank=True, verbose_name="Fecha del precio")

    class Meta:
        verbose_name = "Ingrediente"
        verbose_name_plural = "Ingredientes"

    def __str__(self) -> str:
        return f"{self.nombre} ({self.unidad_medida})"

    def calcular_costo(self, cantidad):
        if cantidad is None or self.precio_actual is None:
            return Decimal('0.00')

        unidad = self.unidad_medida
        precio = self.precio_actual

        if unidad in ['gramos', 'ml']:
            # El precio de referencia está expresado por kilogramo o litro (1000 unidades base)
            return cantidad * (precio / Decimal('1000.00'))
        elif unidad == 'unidad':
            # Ingredientes cuyo precio de referencia ya es por unidad (precio directo)
            precio_por_unidad = {
                'Jojoto maíz tierno',
                'Plátano maduro',
                'Plátano verde',
            }
            if self.nombre in precio_por_unidad:
                return cantidad * precio
            elif self.nombre == 'Huevos':
                # El precio de referencia es por 15 huevos (medio cartón); $0.30 c/u aprox.
                return cantidad * (precio / Decimal('15.00'))
            else:
                # Vegetales y frutas medidos en unidades pero cotizados por peso ($/kg)
                pesos_promedio = {
                    'Cebolla': Decimal('0.15'),       # 150g
                    'Tomate': Decimal('0.12'),         # 120g
                    'Ají dulce': Decimal('0.015'),     # 15g
                    'Pimentón': Decimal('0.15'),       # 150g
                    'Zanahoria': Decimal('0.10'),      # 100g
                    'Berenjena': Decimal('0.25'),      # 250g
                    'Aguacate': Decimal('0.30'),       # 300g
                    'Limón': Decimal('0.08'),          # 80g
                    'Repollo': Decimal('1.00'),        # 1kg (se usa fraccionado en recetas)
                    'Apio rama': Decimal('0.15'),      # 150g
                }
                peso = pesos_promedio.get(self.nombre, Decimal('0.10'))
                return cantidad * peso * precio
        elif unidad == 'diente':
            # Ajo: peso promedio de 1 diente ≈ 5g (0.005 kg)
            return cantidad * Decimal('0.005') * precio
        elif unidad == 'manojo':
            # Hierbas: peso promedio de 1 manojo ≈ 50g (0.05 kg)
            return cantidad * Decimal('0.05') * precio

        return cantidad * precio


class Receta(models.Model):
    """
    Recetas del catálogo curado de Cocina Soberana.
    """
    NIVELES_COSTO = [
        ('ME', 'Muy Económico'),
        ('EM', 'Económico Moderado'),
    ]

    codigo = models.CharField(max_length=10, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    porciones_base = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(1)],
        verbose_name="Porciones base"
    )
    calorias_por_porcion = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Calorías por porción (kcal)"
    )
    proteinas_g = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Proteínas por porción (g)"
    )
    carbohidratos_g = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Carbohidratos por porción (g)"
    )
    grasas_g = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Grasas por porción (g)"
    )
    fibra_g = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Fibra por porción (g)"
    )
    nivel_costo = models.CharField(max_length=2, choices=NIVELES_COSTO, verbose_name="Nivel de costo")
    notas_preparacion = models.TextField(blank=True, verbose_name="Notas de preparación")
    
    es_vegetariana = models.BooleanField(default=False, verbose_name="Es vegetariana")
    es_vegana = models.BooleanField(default=False, verbose_name="Es vegana")
    es_sin_gluten = models.BooleanField(default=False, verbose_name="Es sin gluten")
    es_sin_lactosa = models.BooleanField(default=False, verbose_name="Es sin lactosa")

    categorias = models.ManyToManyField(
        Categoria,
        through='RecetaCategoria',
        related_name='recetas',
        verbose_name="Categorías"
    )
    ingredientes = models.ManyToManyField(
        Ingrediente,
        through='RecetaIngrediente',
        related_name='recetas',
        verbose_name="Ingredientes"
    )

    class Meta:
        verbose_name = "Receta"
        verbose_name_plural = "Recetas"

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"


class RecetaCategoria(models.Model):
    """
    Tabla puente M:N entre Receta y Categoria.
    """
    fk_receta = models.ForeignKey(Receta, on_delete=models.CASCADE, verbose_name="Receta")
    fk_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, verbose_name="Categoría")

    class Meta:
        verbose_name = "Categoría de Receta"
        verbose_name_plural = "Categorías de Recetas"
        unique_together = ('fk_receta', 'fk_categoria')

    def __str__(self) -> str:
        return f"{self.fk_receta.codigo} -> {self.fk_categoria.nombre}"


class RecetaIngrediente(models.Model):
    """
    Tabla puente M:N entre Receta e Ingrediente con cantidades específicas.
    """
    fk_receta = models.ForeignKey(Receta, on_delete=models.CASCADE, verbose_name="Receta")
    fk_ingrediente = models.ForeignKey(Ingrediente, on_delete=models.PROTECT, verbose_name="Ingrediente")
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Cantidad"
    )
    nota_uso = models.CharField(max_length=200, blank=True, verbose_name="Nota de uso")

    class Meta:
        verbose_name = "Ingrediente de Receta"
        verbose_name_plural = "Ingredientes de Recetas"
        unique_together = ('fk_receta', 'fk_ingrediente')

    def __str__(self) -> str:
        return f"{self.fk_receta.codigo} -> {self.fk_ingrediente.nombre}"

    @property
    def costo(self):
        return self.fk_ingrediente.calcular_costo(self.cantidad)


class HistorialPrecioIngrediente(models.Model):
    """
    Registro histórico de los precios de los ingredientes para análisis de evolución.
    """
    fk_ingrediente = models.ForeignKey(
        Ingrediente,
        on_delete=models.CASCADE,
        related_name='historial_precios',
        verbose_name="Ingrediente"
    )
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Precio"
    )
    fecha = models.DateField(verbose_name="Fecha")

    class Meta:
        verbose_name = "Historial de Precio"
        verbose_name_plural = "Historiales de Precios"
        indexes = [
            models.Index(fields=['fk_ingrediente', '-fecha']),
        ]

    def __str__(self) -> str:
        return f"{self.fk_ingrediente.nombre} - {self.precio} ({self.fecha})"


# Signals
@receiver(post_save, sender=HistorialPrecioIngrediente)
def actualizar_precio_ingrediente(sender, instance, **kwargs):
    """
    Signal que actualiza el precio actual y la fecha de precio de un ingrediente
    con el registro de historial más reciente (por fecha y luego por ID).
    """
    ingrediente = instance.fk_ingrediente
    ultimo_precio = HistorialPrecioIngrediente.objects.filter(
        fk_ingrediente=ingrediente
    ).order_by('-fecha', '-id').first()

    if ultimo_precio:
        ingrediente.precio_actual = ultimo_precio.precio
        ingrediente.fecha_precio = ultimo_precio.fecha
        ingrediente.save(update_fields=['precio_actual', 'fecha_precio'])
