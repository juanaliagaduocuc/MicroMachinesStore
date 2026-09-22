from django.core.validators import RegexValidator
from django.db import models


class RolEmpleado(models.Model):
    descripcion = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.descripcion


class UsuarioEmpleado(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    run = models.CharField(
        max_length=12,
        unique=True,
        validators=[RegexValidator(regex=r'^\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]$', message='RUN inválido')],
    )
    correo = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20)
    password = models.CharField(max_length=255)
    idrol = models.ForeignKey(RolEmpleado, on_delete=models.PROTECT, related_name='empleados')

    def __str__(self):
        return f'{self.nombre} {self.apellido}'


class UsuarioCliente(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    run = models.CharField(
        max_length=12,
        unique=True,
        validators=[RegexValidator(regex=r'^\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]$', message='RUN inválido')],
    )
    correo = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20)
    direccion = models.TextField()
    password = models.CharField(max_length=255)

    def __str__(self):
        return f'{self.nombre} {self.apellido}'


class Pintura(models.Model):
    color = models.CharField(max_length=50)
    descripcion = models.TextField()
    valor = models.DecimalField(max_digits=10, decimal_places=0)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.color


class Rueda(models.Model):
    descripcion = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=10, decimal_places=0)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.descripcion


class Silla(models.Model):
    descripcion = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=10, decimal_places=0)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.descripcion


class Luces(models.Model):
    color = models.CharField(max_length=50)
    descripcion = models.TextField()
    valor = models.DecimalField(max_digits=10, decimal_places=0)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.color


class Vehiculo(models.Model):
    modelo = models.CharField(max_length=100)
    marca = models.CharField(max_length=100)
    valor_base = models.DecimalField(max_digits=12, decimal_places=0)
    pintura = models.ForeignKey(Pintura, on_delete=models.PROTECT, related_name='vehiculos')
    rueda = models.ForeignKey(Rueda, on_delete=models.PROTECT, related_name='vehiculos', null=True, blank=True)
    silla = models.ForeignKey(Silla, on_delete=models.PROTECT, related_name='vehiculos')
    luces = models.ForeignKey(Luces, on_delete=models.PROTECT, related_name='vehiculos')
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.marca} {self.modelo}'


class Pedido(models.Model):
    cliente = models.ForeignKey(UsuarioCliente, on_delete=models.PROTECT, related_name='pedidos')
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name='pedidos', null=True, blank=True)
    pintura = models.ForeignKey(Pintura, on_delete=models.PROTECT, related_name='pedidos_pintura', null=True, blank=True)
    rueda = models.ForeignKey(Rueda, on_delete=models.PROTECT, related_name='pedidos_rueda', null=True, blank=True)
    silla = models.ForeignKey(Silla, on_delete=models.PROTECT, related_name='pedidos_silla', null=True, blank=True)
    luces = models.ForeignKey(Luces, on_delete=models.PROTECT, related_name='pedidos_luces', null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=0)

    def __str__(self):
        return f'Pedido #{self.id} - {self.cliente}'
