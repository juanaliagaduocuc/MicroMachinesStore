from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

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


class StoreApiTests(TestCase):
    def setUp(self):
        self.paint = Pintura.objects.create(color='Rojo', descripcion='Pintura roja', valor=15000)
        self.wheel = Rueda.objects.create(descripcion='Rueda deportiva', valor=8000)
        self.seat = Silla.objects.create(descripcion='Silla clásica', valor=12000)
        self.light = Luces.objects.create(color='Blanco', descripcion='Luces LED', valor=11000)
        self.vehicle = Vehiculo.objects.create(
            modelo='F40', marca='Ferrari', valor_base=240000, pintura=self.paint,
            rueda=self.wheel, silla=self.seat, luces=self.light,
        )

    def test_vehicle_api_returns_public_active_catalog_with_cors(self):
        response = self.client.get(reverse('api_vehiculos'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')
        self.assertEqual(response.json()['results'][0]['marca'], 'Ferrari')
        self.assertEqual(response.json()['results'][0]['precio_base'], '240000')

    def test_accessory_api_returns_active_catalog(self):
        inactive = Pintura.objects.create(color='Verde', descripcion='No disponible', valor=5000, activo=False)

        response = self.client.get(reverse('api_accesorios'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 4)
        self.assertNotIn(inactive.color, [item['nombre'] for item in response.json()['results']])

    @patch('store.views.fetch_public_json')
    def test_integrations_page_shows_external_data_and_handles_failure(self, fetch_json):
        fetch_json.side_effect = [
            {'Results': [{'MakeName': 'Toyota', 'MakeId': 1}]},
            {'rates': {'CLP': 950.0}, 'time_last_update_utc': '2026-10-05'},
        ]
        response = self.client.get(reverse('integraciones'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Toyota')
        self.assertContains(response, '950.00 CLP')

        fetch_json.side_effect = [None, None]
        unavailable = self.client.get(reverse('integraciones'))
        self.assertEqual(unavailable.status_code, 200)
        self.assertContains(unavailable, 'No se pudo obtener el tipo de cambio')
