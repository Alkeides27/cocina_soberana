from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario


class RegistroForm(UserCreationForm):
    """
    Formulario para el registro de nuevos usuarios en Cocina Soberana.
    Extiende UserCreationForm para añadir los campos de información familiar y de presupuesto.
    """
    nombre = forms.CharField(
        max_length=100,
        required=True,
        label="Nombre completo",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primario focus:border-transparent outline-none transition'
        })
    )
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primario focus:border-transparent outline-none transition'
        })
    )
    tamano_familia = forms.IntegerField(
        min_value=1,
        max_value=20,
        required=True,
        initial=1,
        label="Miembros de la familia",
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primario focus:border-transparent outline-none transition'
        })
    )
    presupuesto_semanal = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        required=True,
        initial=0,
        label="Presupuesto semanal disponible",
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primario focus:border-transparent outline-none transition',
            'step': '0.01'
        })
    )
    moneda = forms.ChoiceField(
        choices=[('USD', 'USD'), ('VES', 'VES')],
        required=True,
        initial='USD',
        label="Moneda",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primario focus:border-transparent outline-none transition'
        })
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'email', 'nombre', 'tamano_familia', 'presupuesto_semanal', 'moneda')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicar clases Tailwind a los inputs de username y password heredados
        for field_name in ['username']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primario focus:border-transparent outline-none transition'
                })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email


class EditarPerfilForm(forms.ModelForm):
    """
    Formulario para editar el perfil del usuario (nombre, tamaño familia, presupuesto y moneda).
    """
    nombre = forms.CharField(
        max_length=100,
        required=True,
        label="Nombre completo",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primario focus:border-transparent outline-none transition'
        })
    )
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primario focus:border-transparent outline-none transition'
        })
    )
    tamano_familia = forms.IntegerField(
        min_value=1,
        max_value=20,
        required=True,
        label="Miembros de la familia",
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primario focus:border-transparent outline-none transition'
        })
    )
    presupuesto_semanal = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        required=True,
        label="Presupuesto semanal disponible",
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primario focus:border-transparent outline-none transition',
            'step': '0.01'
        })
    )
    moneda = forms.ChoiceField(
        choices=[('USD', 'USD'), ('VES', 'VES')],
        required=True,
        label="Moneda",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primario focus:border-transparent outline-none transition'
        })
    )

    class Meta:
        model = Usuario
        fields = ('nombre', 'email', 'tamano_familia', 'presupuesto_semanal', 'moneda')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este correo electrónico ya está en uso por otro usuario.")
        return email
