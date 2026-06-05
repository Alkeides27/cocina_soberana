import factory
from factory.django import DjangoModelFactory
from usuarios.models import Usuario, RestriccionUsuario

class UsuarioFactory(DjangoModelFactory):
    class Meta:
        model = Usuario

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user_{n}@test.com")
    nombre = factory.Faker("name")
    tamano_familia = 4
    presupuesto_semanal = 50.00
    moneda = "USD"
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Asegurar creación correcta de passwords
        password = kwargs.pop("password", "SoberanoPass123!")
        user = model_class(*args, **kwargs)
        user.set_password(password)
        user.save()
        return user

class RestriccionUsuarioFactory(DjangoModelFactory):
    class Meta:
        model = RestriccionUsuario

    fk_usuario = factory.SubFactory(UsuarioFactory)
    tipo = "VEGETARIANA"
    descripcion = "Dieta vegetariana"
