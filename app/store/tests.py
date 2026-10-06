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
        self.assertContains(response, 'Administradas desde la API REST')

        sales = self.client.get(reverse('api_ventas'))
        filtered = self.client.get(reverse('api_ventas'), {'cliente': self.client_one.id})
        self.assertEqual(sales.status_code, 200)
        self.assertEqual({sale['cliente'] for sale in sales.json()['results']}, {'Cristian Pérez', 'Paula Rojas'})
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual({sale['cliente'] for sale in filtered.json()['results']}, {'Cristian Pérez'})
        invalid_filter = self.client.get(reverse('api_ventas'), {'cliente': 'no-numero'})
        self.assertEqual(invalid_filter.status_code, 400)

    def test_employee_panel_paginates_sales_five_per_page(self):
        for _ in range(6):
            Pedido.objects.create(cliente=self.client_one, vehiculo=self.vehicle, total=1000)
        self.client.force_login(self.user)

        first_page = self.client.get(reverse('api_ventas'))
        second_page = self.client.get(reverse('api_ventas'), {'page': 2})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(len(first_page.json()['results']), 5)
        self.assertEqual(first_page.json()['count'], 8)
        self.assertEqual(first_page.json()['page'], 1)
        self.assertEqual(len(second_page.json()['results']), 3)
        self.assertEqual(second_page.json()['page'], 2)


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

    def test_sales_api_requires_employee_and_returns_all_sales(self):
        customer = UsuarioCliente.objects.create(
            nombre='Ana', apellido='Pérez', run='12.345.678-9',
            correo='ana@example.com', telefono='123', direccion='Santiago', password='pass',
        )
        Pedido.objects.create(
            cliente=customer, vehiculo=self.vehicle, pintura=self.paint,
            rueda=self.wheel, silla=self.seat, luces=self.light, total=286000,
        )
        Pedido.objects.create(cliente=customer, pintura=self.paint, total=15000)

        self.assertEqual(self.client.get(reverse('api_ventas')).status_code, 401)

        user = get_user_model().objects.create_user(username='cliente', password='pass')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('api_ventas')).status_code, 403)

        user.is_superuser = True
        user.save()
        response = self.client.get(reverse('api_ventas'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 2)
        self.assertEqual(response.json()['total_ventas'], '301000')
        self.assertEqual(
            {sale['producto'] for sale in response.json()['results']},
            {'Ferrari F40', 'Accesorio'},
        )

    def test_sales_api_supports_create_update_and_delete(self):
        customer = UsuarioCliente.objects.create(
            nombre='Ana', apellido='Pérez', run='12.345.678-9',
            correo='ana@example.com', telefono='123', direccion='Santiago', password='pass',
        )
        user = get_user_model().objects.create_superuser(
            username='admin', email='admin@example.com', password='pass',
        )
        self.client.force_login(user)
        payload = {
            'cliente': customer.id,
            'vehiculo': self.vehicle.id,
            'pintura': self.paint.id,
            'rueda': self.wheel.id,
            'silla': self.seat.id,
            'luces': self.light.id,
            'total': '286000',
        }

        invalid = self.client.post(
            reverse('api_ventas'),
            data={**payload, 'total': '2.5'},
            content_type='application/json',
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(Pedido.objects.count(), 0)

        created = self.client.post(
            reverse('api_ventas'), data=payload, content_type='application/json',
        )
        self.assertEqual(created.status_code, 201)
        sale_id = created.json()['id']
        self.assertEqual(created.json()['total'], '286000')

        updated = self.client.patch(
            reverse('api_venta_detalle', args=[sale_id]),
            data='{"total":"290000"}', content_type='application/json',
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['total'], '290000')
        updated_again = self.client.patch(
            reverse('api_venta_detalle', args=[sale_id]),
            data='{"cliente":%d,"total":"291000"}' % customer.id,
            content_type='application/json',
        )
        self.assertEqual(updated_again.status_code, 200)
        self.assertEqual(updated_again.json()['total'], '291000')

        deleted = self.client.delete(reverse('api_venta_detalle', args=[sale_id]))
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Pedido.objects.filter(pk=sale_id).exists())
        missing = self.client.get(reverse('api_venta_detalle', args=[sale_id]))
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()['error'], 'Venta no encontrada.')

    @patch('store.views.fetch_public_json')
    def test_integrations_page_shows_external_data_and_handles_failure(self, fetch_json):
        fetch_json.side_effect = [
            {'Results': [{'MakeName': 'Toyota', 'MakeId': 1}]},
            {'status': 'success', 'message': 'https://images.dog.ceo/breeds/hound-english/n02089973_100.jpg'},
            {'setup': 'Why did the car stop?', 'punchline': 'It ran out of road.', 'type': 'general'},
        ]
        response = self.client.get(reverse('integraciones'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Toyota')
        self.assertContains(response, 'Generar nombre')
        self.assertNotContains(response, 'Tipo de cambio')
        self.assertContains(response, 'Why did the car stop?')
        self.assertContains(response, 'https://images.dog.ceo/breeds/hound-english/n02089973_100.jpg')

        fetch_json.side_effect = [None, None, None]
        unavailable = self.client.get(reverse('integraciones'))
        self.assertEqual(unavailable.status_code, 200)
        self.assertContains(unavailable, 'Los chistes están en pits')

    @patch('store.views.fetch_public_json')
    def test_random_plate_name_api_formats_name_and_reports_failure(self, fetch_json):
        fetch_json.return_value = [
            {'word': 'turbo', 'tags': ['n']},
            {'word': 'piston', 'tags': ['n']},
            {'word': 'quickly', 'tags': ['adv']},
            {'word': 'supercalifragilistic', 'tags': ['n']},
        ]
        response = self.client.get(reverse('api_nombre_patente'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()['name'].split()), {'TURBO', 'PISTON'})

        fetch_json.return_value = None
        unavailable = self.client.get(reverse('api_nombre_patente'))
        self.assertEqual(unavailable.status_code, 503)
        self.assertIn('error', unavailable.json())

        fetch_json.return_value = [{'word': 'speed', 'tags': ['n']}]
        insufficient = self.client.get(reverse('api_nombre_patente'))
        self.assertEqual(insufficient.status_code, 502)
        self.assertIn('error', insufficient.json())
