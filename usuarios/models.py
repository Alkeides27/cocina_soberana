from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado para Cocina Soberana.
    Extiende AbstractUser para incluir información sobre el tamaño de la familia,
    el presupuesto semanal y la moneda preferida.
    """
    email = models.EmailField(unique=True, verbose_name="Correo electrónico")
    nombre = models.CharField(max_length=100, verbose_name="Nombre completo")
    tamano_familia = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        verbose_name="Tamaño de la familia"
    )
    presupuesto_semanal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Presupuesto semanal"
    )
    moneda = models.CharField(
        max_length=3,
        choices=[('USD', 'USD'), ('VES', 'VES')],
        default='USD',
        verbose_name="Moneda"
    )

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self) -> str:
        return f"{self.username} ({self.nombre})"


class RestriccionUsuario(models.Model):
    """
    Modelo para gestionar las restricciones dietéticas personalizadas de los usuarios.
    """
    TIPOS_RESTRICCION = [
        ('VEGETARIANA', 'Vegetariana'),
        ('VEGANA', 'Vegana'),
        ('SIN_GLUTEN', 'Sin Gluten'),
        ('SIN_LACTOSA', 'Sin Lactosa'),
        ('OTRA', 'Otra'),
    ]

    fk_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="restricciones",
        verbose_name="Usuario"
    )
    tipo = models.CharField(
        max_length=50,
        choices=TIPOS_RESTRICCION,
        verbose_name="Tipo de restricción"
    )
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Descripción de la restricción"
    )

    class Meta:
        verbose_name = "Restricción de Usuario"
        verbose_name_plural = "Restricciones de Usuarios"

    def __str__(self) -> str:
        return f"{self.fk_usuario.username} - {self.get_tipo_display()}"
