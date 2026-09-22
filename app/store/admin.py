from django.contrib import admin

from .models import (
    Luces,
    Pedido,
    Pintura,
    RolEmpleado,
    Rueda,
    Silla,
    UsuarioCliente,
    UsuarioEmpleado,
    Vehiculo,
)


def get_user_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'admin'
    try:
        empleado = UsuarioEmpleado.objects.get(correo=user.email)
        return empleado.idrol.descripcion.lower()
    except UsuarioEmpleado.DoesNotExist:
        return None


class BaseStoreAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        role = get_user_role(request.user)
        return role in {'admin', 'empleado'}

    def has_view_permission(self, request, obj=None):
        role = get_user_role(request.user)
        return role in {'admin', 'empleado'}

    def has_add_permission(self, request):
        role = get_user_role(request.user)
        return role == 'admin'

    def has_change_permission(self, request, obj=None):
        role = get_user_role(request.user)
        return role == 'admin'

    def has_delete_permission(self, request, obj=None):
        role = get_user_role(request.user)
        return role == 'admin'


class EmployeeProductAdmin(BaseStoreAdmin):
    def has_add_permission(self, request):
        role = get_user_role(request.user)
        return role in {'admin', 'empleado'}

    def has_change_permission(self, request, obj=None):
        role = get_user_role(request.user)
        return role in {'admin', 'empleado'}

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RolEmpleado)
class RolEmpleadoAdmin(BaseStoreAdmin):
    list_display = ('id', 'descripcion')


@admin.register(UsuarioEmpleado)
class UsuarioEmpleadoAdmin(BaseStoreAdmin):
    list_display = ('nombre', 'apellido', 'correo', 'telefono', 'idrol')


@admin.register(UsuarioCliente)
class UsuarioClienteAdmin(BaseStoreAdmin):
    list_display = ('nombre', 'apellido', 'correo', 'telefono')


@admin.register(Pintura)
class PinturaAdmin(EmployeeProductAdmin):
    list_display = ('color', 'descripcion', 'valor', 'activo')
    list_filter = ('activo',)


@admin.register(Rueda)
class RuedaAdmin(EmployeeProductAdmin):
    list_display = ('descripcion', 'valor', 'activo')
    list_filter = ('activo',)


@admin.register(Silla)
class SillaAdmin(EmployeeProductAdmin):
    list_display = ('descripcion', 'valor', 'activo')
    list_filter = ('activo',)


@admin.register(Luces)
class LucesAdmin(EmployeeProductAdmin):
    list_display = ('color', 'descripcion', 'valor', 'activo')
    list_filter = ('activo',)


@admin.register(Vehiculo)
class VehiculoAdmin(EmployeeProductAdmin):
    list_display = ('marca', 'modelo', 'valor_base', 'activo')
    list_filter = ('activo',)


@admin.register(Pedido)
class PedidoAdmin(BaseStoreAdmin):
    list_display = ('id', 'cliente', 'vehiculo', 'fecha', 'total')
