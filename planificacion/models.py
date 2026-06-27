from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from catalogo.models import Receta, Ingrediente


class MenuSemanal(models.Model):
    """
    Planificación de comidas: asigna una receta para una fecha y momento del día
    para un usuario específico.
    """
    MOMENTOS = [
        ('DESAYUNO', 'Desayuno'),
        ('ALMUERZO', 'Almuerzo'),
        ('CENA', 'Cena'),
        ('MERIENDA', 'Merienda'),
    ]

    fk_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='menus',
        verbose_name="Usuario"
    )
    fk_receta = models.ForeignKey(
        Receta,
        on_delete=models.PROTECT,
        related_name='menus',
        verbose_name="Receta"
    )
    fecha = models.DateField(verbose_name="Fecha")
    momento = models.CharField(max_length=20, choices=MOMENTOS, verbose_name="Momento del día")

    class Meta:
        verbose_name = "Menú Semanal"
        verbose_name_plural = "Menús Semanales"
        unique_together = ('fk_usuario', 'fecha', 'momento')

    def __str__(self) -> str:
        return f"{self.fk_usuario.username} - {self.fecha} [{self.get_momento_display()}]: {self.fk_receta.nombre}"


class IngredienteSemanal(models.Model):
    """
    Permite añadir ingredientes individuales (ej. porciones de fruta) al plan semanal
    de un usuario, para una fecha y momento específicos.
    """
    MOMENTOS = [
        ('DESAYUNO', 'Desayuno'),
        ('ALMUERZO', 'Almuerzo'),
        ('CENA', 'Cena'),
        ('MERIENDA', 'Merienda'),
    ]

    fk_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ingredientes_semanales',
        verbose_name="Usuario"
    )
    fk_ingrediente = models.ForeignKey(
        Ingrediente,
        on_delete=models.PROTECT,
        related_name='ingredientes_semanales',
        verbose_name="Ingrediente"
    )
    fecha = models.DateField(verbose_name="Fecha")
    momento = models.CharField(max_length=20, choices=MOMENTOS, verbose_name="Momento del día")
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Cantidad"
    )

    class Meta:
        verbose_name = "Ingrediente Semanal"
        verbose_name_plural = "Ingredientes Semanales"
        unique_together = ('fk_usuario', 'fk_ingrediente', 'fecha', 'momento')

    def __str__(self) -> str:
        return f"{self.fk_usuario.username} - {self.fk_ingrediente.nombre} ({self.cantidad} {self.fk_ingrediente.unidad_medida}) - {self.fecha} [{self.get_momento_display()}]"


class ListaCompra(models.Model):
    """
    Lista de compras consolidada generada a partir de la planificación del usuario.
    """
    fk_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='listas_compra',
        verbose_name="Usuario"
    )
    fecha_generacion = models.DateField(auto_now_add=True, verbose_name="Fecha de generación")
    sincronizada_at = models.DateTimeField(null=True, blank=True, verbose_name="Sincronizada el")

    class Meta:
        verbose_name = "Lista de Compra"
        verbose_name_plural = "Listas de Compras"

    def __str__(self) -> str:
        return f"Lista de {self.fk_usuario.username} - {self.fecha_generacion}"


class ItemListaCompra(models.Model):
    """
    Ítems individuales dentro de una lista de compras consolidada.
    """
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('COMPRADO', 'Comprado'),
    ]

    fk_lista = models.ForeignKey(
        ListaCompra,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Lista de compra"
    )
    fk_ingrediente = models.ForeignKey(
        Ingrediente,
        on_delete=models.PROTECT,
        related_name='items_lista',
        verbose_name="Ingrediente"
    )
    cantidad_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Cantidad total"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PENDIENTE',
        verbose_name="Estado"
    )
    actualizado_at = models.DateTimeField(auto_now=True, verbose_name="Actualizado el")

    class Meta:
        verbose_name = "Ítem de Lista de Compra"
        verbose_name_plural = "Ítems de Listas de Compras"

    def __str__(self) -> str:
        return f"{self.fk_ingrediente.nombre}: {self.cantidad_total} ({self.get_estado_display()})"
