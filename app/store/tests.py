from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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


class EmployeePanelTests(TestCase):
    def setUp(self):
        self.role_admin = RolEmpleado.objects.create(descripcion='admin')
        self.role_employee = RolEmpleado.objects.create(descripcion='empleado')

        self.user = get_user_model().objects.create_user(
            username='empleado1',
            email='empleado1@minimachines.cl',
            password='pass1234',
            first_name='María',
            last_name='Rojas',
            is_staff=False,
        )
        self.employee = UsuarioEmpleado.objects.create(
            nombre='María',
            apellido='Rojas',
            run='11.222.333-4',
            correo='empleado1@minimachines.cl',
            telefono='+56900000000',
            password='pass1234',
            idrol=self.role_employee,
        )

        self.paint = Pintura.objects.create(color='Rojo', descripcion='Pintura roja', valor=15000, activo=True)
        self.wheel = Rueda.objects.create(descripcion='Rueda deportiva', valor=8000, activo=True)
        self.seat = Silla.objects.create(descripcion='Silla de lujo', valor=12000, activo=True)
        self.light = Luces.objects.create(color='Blanco', descripcion='Luz LED', valor=11000, activo=True)

        self.vehicle = Vehiculo.objects.create(
            modelo='F40',
            marca='Ferrari',
            valor_base=240000,
            pintura=self.paint,
            rueda=self.wheel,
            silla=self.seat,
            luces=self.light,
            activo=True,
        )

        self.client_one = UsuarioCliente.objects.create(
            nombre='Cristian',
            apellido='Pérez',
            run='12.345.678-9',
            correo='cristian.perez@gmail.com',
            telefono='+56911111111',
            direccion='Santiago',
            password='pass1234',
        )
        self.client_two = UsuarioCliente.objects.create(
            nombre='Paula',
            apellido='Rojas',
            run='15.678.901-2',
            correo='paula.rojas@gmail.com',
            telefono='+56922222222',
            direccion='Viña del Mar',
            password='pass1234',
        )

        Pedido.objects.create(
            cliente=self.client_one,
            vehiculo=self.vehicle,
            pintura=self.paint,
            rueda=self.wheel,
            silla=self.seat,
            luces=self.light,
            total=240000 + 15000 + 8000 + 12000 + 11000,
        )
        Pedido.objects.create(
            cliente=self.client_two,
            vehiculo=self.vehicle,
            pintura=self.paint,
            rueda=self.wheel,
            silla=self.seat,
            luces=self.light,
            total=250000,
        )

    def test_employee_panel_shows_orders_and_filters_by_client(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('panel'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pedidos recientes')
        self.assertContains(response, 'Cristian')
        self.assertContains(response, 'Paula')

        filtered = self.client.get(reverse('panel'), {'cliente': self.client_one.id})
        self.assertEqual(filtered.status_code, 200)
        self.assertContains(filtered, 'Cristian')
        self.assertNotContains(filtered, 'Paula')
