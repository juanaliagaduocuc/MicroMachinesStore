from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from MicroMachinesStore.app.store.models import (
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


class Command(BaseCommand):
    help = 'Seed roles, admin user, employees, clients, vehicles, accessories, and purchase orders in one pass.'

    @transaction.atomic
    def handle(self, *args, **options):
        admin_role, _ = RolEmpleado.objects.update_or_create(id=1, defaults={'descripcion': 'admin'})
        employee_role, _ = RolEmpleado.objects.update_or_create(id=2, defaults={'descripcion': 'empleado'})

        User = get_user_model()
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@minimachines.cl', 'is_staff': True, 'is_superuser': True},
        )
        admin_user.email = 'admin@minimachines.cl'
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.set_password('Admin123')
        admin_user.save()

        UsuarioEmpleado.objects.update_or_create(
            correo='admin@minimachines.cl',
            defaults={
                'nombre': 'Admin',
                'apellido': 'Sistema',
                'run': '10.000.000-1',
                'telefono': '+56900000000',
                'password': 'Admin123',
                'idrol': admin_role,
            },
        )

        pinturas = [
            Pintura.objects.get_or_create(color='Rojo', descripcion='Pintura roja brillante', valor=15000)[0],
            Pintura.objects.get_or_create(color='Azul', descripcion='Pintura azul metálico', valor=17000)[0],
            Pintura.objects.get_or_create(color='Negro', descripcion='Pintura negra mate', valor=18000)[0],
            Pintura.objects.get_or_create(color='Blanco', descripcion='Pintura blanca perlada', valor=16000)[0],
        ]

        ruedas = [
            Rueda.objects.get_or_create(descripcion='Rueda deportiva 1', valor=8000)[0],
            Rueda.objects.get_or_create(descripcion='Rueda off-road 2', valor=9500)[0],
            Rueda.objects.get_or_create(descripcion='Rueda vintage 3', valor=7000)[0],
        ]

        sillas = [
            Silla.objects.get_or_create(descripcion='Silla deportiva', valor=12000)[0],
            Silla.objects.get_or_create(descripcion='Silla lujo', valor=15000)[0],
        ]

        luces = [
            Luces.objects.get_or_create(color='Blanco', descripcion='Luz LED blanca', valor=11000)[0],
            Luces.objects.get_or_create(color='Amarillo', descripcion='Luz LED amarilla', valor=10000)[0],
            Luces.objects.get_or_create(color='Azul', descripcion='Luz LED azul', valor=12000)[0],
        ]

        employee_data = [
            ('Ana', 'García', '11.345.678-9', 'ana.garcia@minimachines.cl', '+56911111111', admin_role),
            ('Mateo', 'Silva', '14.876.432-1', 'mateo.silva@minimachines.cl', '+56911111112', employee_role),
            ('Fernanda', 'López', '17.221.334-5', 'fernanda.lopez@minimachines.cl', '+56911111113', employee_role),
            ('Diego', 'Mendoza', '18.455.211-7', 'diego.mendoza@minimachines.cl', '+56911111114', employee_role),
            ('Valentina', 'Castro', '19.332.876-0', 'valentina.castro@minimachines.cl', '+56911111115', employee_role),
        ]

        for nombre, apellido, run, correo, telefono, rol in employee_data:
            UsuarioEmpleado.objects.update_or_create(
                correo=correo,
                defaults={
                    'nombre': nombre,
                    'apellido': apellido,
                    'run': run,
                    'telefono': telefono,
                    'password': 'pass1234',
                    'idrol': rol,
                },
            )
            user = User.objects.update_or_create(
                username=correo,
                defaults={
                    'email': correo,
                    'first_name': nombre,
                    'last_name': apellido,
                    'is_staff': False,
                    'is_active': True,
                },
            )[0]
            user.set_password('pass1234')
            user.save()

        client_data = [
            ('Cristian', 'Pérez', '11.222.333-4', 'cristian.perez@gmail.com', '+56922222221', 'Av. Los Andes 123, Santiago'),
            ('Paula', 'Rojas', '16.543.671-8', 'paula.rojas@gmail.com', '+56922222222', 'Calle El Bosque 456, Viña del Mar'),
            ('Sebastián', 'Ramírez', '15.112.765-3', 'sebastian.ramirez@gmail.com', '+56922222223', 'Avenida Libertador 789, Concepción'),
            ('María', 'Fuentes', '13.564.879-2', 'maria.fuentes@gmail.com', '+56922222224', 'Paseo del Mar 321, Valparaíso'),
            ('Lucas', 'Ortiz', '18.998.456-1', 'lucas.ortiz@gmail.com', '+56922222225', 'Calle Aconcagua 88, Temuco'),
        ]

        for nombre, apellido, run, correo, telefono, direccion in client_data:
            UsuarioCliente.objects.update_or_create(
                correo=correo,
                defaults={
                    'nombre': nombre,
                    'apellido': apellido,
                    'run': run,
                    'telefono': telefono,
                    'direccion': direccion,
                    'password': 'pass1234',
                },
            )
            user = User.objects.update_or_create(
                username=correo,
                defaults={
                    'email': correo,
                    'first_name': nombre,
                    'last_name': apellido,
                    'is_staff': False,
                    'is_active': True,
                },
            )[0]
            user.set_password('pass1234')
            user.save()

        vehicles = [
            ('Ferrari F40', 'Ferrari', 240000, pinturas[0], ruedas[0], sillas[0], luces[0]),
            ('Porsche 911', 'Porsche', 260000, pinturas[1], ruedas[1], sillas[1], luces[1]),
            ('Jeep Wrangler', 'Jeep', 210000, pinturas[2], ruedas[0], sillas[0], luces[2]),
            ('Lamborghini Countach', 'Lamborghini', 280000, pinturas[0], ruedas[1], sillas[1], luces[1]),
            ('Ford Mustang', 'Ford', 230000, pinturas[3], ruedas[2], sillas[0], luces[0]),
            ('Mini Cooper', 'Mini', 180000, pinturas[1], ruedas[2], sillas[1], luces[2]),
        ]

        for modelo, marca, valor_base, pintura, rueda, silla, luces_obj in vehicles:
            Vehiculo.objects.update_or_create(
                modelo=modelo,
                marca=marca,
                defaults={
                    'valor_base': valor_base,
                    'pintura': pintura,
                    'rueda': rueda,
                    'silla': silla,
                    'luces': luces_obj,
                    'activo': True,
                },
            )

        clients = list(UsuarioCliente.objects.all()[:3])
        available_vehicles = list(Vehiculo.objects.filter(activo=True)[:2])

        if len(clients) >= 3 and len(available_vehicles) >= 2:
            for client in clients:
                for vehicle in available_vehicles:
                    Pedido.objects.get_or_create(
                        cliente=client,
                        vehiculo=vehicle,
                        defaults={'total': vehicle.valor_base},
                    )

        self.stdout.write(self.style.SUCCESS('Roles creados: admin y empleado.'))
        self.stdout.write(self.style.SUCCESS(f'Usuario admin: {admin_user.username} / Admin123'))
        self.stdout.write(self.style.SUCCESS('Datos cargados correctamente: 5 empleados, 5 clientes, 6 vehículos, 3 ruedas, 3 luces y 2 sillas.'))
        self.stdout.write(self.style.SUCCESS(f'Pedidos creados: {Pedido.objects.filter(cliente__in=clients).count()}'))
