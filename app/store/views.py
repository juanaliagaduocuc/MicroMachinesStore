from decimal import Decimal, InvalidOperation
import json
import random
from urllib.parse import urlsplit
from urllib.request import urlopen

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET, require_http_methods

from .forms import LoginForm, RegisterForm
from .models import Luces, Pedido, Pintura, Rueda, Silla, UsuarioCliente, UsuarioEmpleado, Vehiculo


def get_user_role(user):
    if not user or not user.is_authenticated:
        return 'cliente'
    if user.is_superuser:
        return 'admin'
    try:
        empleado = UsuarioEmpleado.objects.get(correo=user.email)
        return empleado.idrol.descripcion.lower()
    except UsuarioEmpleado.DoesNotExist:
        return 'cliente'


def home(request):
    role = get_user_role(request.user)
    user_name = request.user.first_name or request.user.username if request.user.is_authenticated else 'visitante'
    context = {
        'role': role,
        'user_name': user_name,
        'is_authenticated': request.user.is_authenticated,
    }
    return render(request, 'store/home.html', context)


def store(request):
    vehicles_list = Vehiculo.objects.filter(activo=True).select_related('pintura', 'rueda', 'silla', 'luces')[:6]
    return render(request, 'store/vehicles.html', {
        'title': 'Tienda',
        'items': [
            {
                'id': item.id,
                'name': f'{item.marca} {item.modelo}',
                'price': f'${item.valor_base:,.0f}',
                'description': f'Pintura: {item.pintura.color} · Rueda: {item.rueda.descripcion if item.rueda else "N/A"} · Silla: {item.silla.descripcion} · Luces: {item.luces.color}',
            }
            for item in vehicles_list
        ]
    })


def vehicles(request):
    vehicles_list = Vehiculo.objects.filter(activo=True).select_related('pintura', 'rueda', 'silla', 'luces')
    context = {
        'title': 'Catálogo de vehículos',
        'items': [
            {
                'id': item.id,
                'name': f'{item.marca} {item.modelo}',
                'price': f'${item.valor_base:,.0f}',
                'description': f'Pintura: {item.pintura.color} · Rueda: {item.rueda.descripcion if item.rueda else "N/A"} · Silla: {item.silla.descripcion} · Luces: {item.luces.color}',
            }
            for item in vehicles_list
        ],
    }
    return render(request, 'store/vehicles.html', context)


@require_GET
def api_vehicles(request):
    vehicles_list = Vehiculo.objects.filter(activo=True).select_related('pintura', 'rueda', 'silla', 'luces')
    results = [{
        'id': item.id,
        'marca': item.marca,
        'modelo': item.modelo,
        'precio_base': str(item.valor_base),
        'pintura': item.pintura.color,
        'rueda': item.rueda.descripcion if item.rueda else None,
        'silla': item.silla.descripcion,
        'luces': item.luces.color,
    } for item in vehicles_list]
    response = JsonResponse({'count': len(results), 'results': results})
    response['Access-Control-Allow-Origin'] = '*'
    return response


@require_GET
def api_accessories(request):
    results = []
    for model, kind, name_field, description_field in [
        (Pintura, 'pintura', 'color', 'descripcion'),
        (Rueda, 'rueda', 'descripcion', 'descripcion'),
        (Silla, 'silla', 'descripcion', 'descripcion'),
        (Luces, 'luces', 'color', 'descripcion'),
    ]:
        results.extend({
            'id': item.id,
            'tipo': kind,
            'nombre': getattr(item, name_field),
            'descripcion': getattr(item, description_field),
            'precio': str(item.valor),
        } for item in model.objects.filter(activo=True))
    response = JsonResponse({'count': len(results), 'results': results})
    response['Access-Control-Allow-Origin'] = '*'
    return response


def sales_api_denial(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Autenticación requerida.'}, status=401)
    if get_user_role(request.user) not in {'admin', 'empleado'}:
        return JsonResponse({'error': 'Acceso restringido a empleados.'}, status=403)
    return None


def serialize_sale(pedido):
    if pedido.vehiculo:
        producto = f'{pedido.vehiculo.marca} {pedido.vehiculo.modelo}'
        detalles = [
            f'Pintura: {(pedido.pintura or pedido.vehiculo.pintura).color}',
            f'Rueda: {(pedido.rueda or pedido.vehiculo.rueda).descripcion if pedido.rueda or pedido.vehiculo.rueda else "Sin rueda"}',
            f'Silla: {(pedido.silla or pedido.vehiculo.silla).descripcion}',
            f'Luces: {(pedido.luces or pedido.vehiculo.luces).color}',
        ]
    else:
        producto = 'Accesorio'
        detalles = [
            f'{nombre}: {valor}'
            for accesorio, nombre, atributo in [
                (pedido.pintura, 'Pintura', 'color'),
                (pedido.rueda, 'Rueda', 'descripcion'),
                (pedido.silla, 'Silla', 'descripcion'),
                (pedido.luces, 'Luces', 'color'),
            ]
            if accesorio and (valor := getattr(accesorio, atributo))
        ]

    return {
        'id': pedido.id,
        'fecha': pedido.fecha.isoformat(),
        'cliente_id': pedido.cliente_id,
        'cliente': f'{pedido.cliente.nombre} {pedido.cliente.apellido}',
        'vehiculo_id': pedido.vehiculo_id,
        'pintura_id': pedido.pintura_id,
        'rueda_id': pedido.rueda_id,
        'silla_id': pedido.silla_id,
        'luces_id': pedido.luces_id,
        'producto': producto,
        'detalle': ' · '.join(detalles),
        'total': str(pedido.total),
    }


def read_sale_data(request, pedido=None):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError('El cuerpo debe ser JSON válido.')
    if not isinstance(data, dict):
        raise ValueError('El cuerpo debe ser un objeto JSON.')

    fields = {'cliente', 'vehiculo', 'pintura', 'rueda', 'silla', 'luces', 'total'}
    if data.keys() - fields:
        raise ValueError('La solicitud contiene campos no permitidos.')

    values = {
        'cliente': pedido.cliente_id if pedido else None,
        'vehiculo': pedido.vehiculo_id if pedido else None,
        'pintura': pedido.pintura_id if pedido else None,
        'rueda': pedido.rueda_id if pedido else None,
        'silla': pedido.silla_id if pedido else None,
        'luces': pedido.luces_id if pedido else None,
        'total': pedido.total if pedido else None,
    }
    values.update(data)

    models = {
        'cliente': UsuarioCliente,
        'vehiculo': Vehiculo,
        'pintura': Pintura,
        'rueda': Rueda,
        'silla': Silla,
        'luces': Luces,
    }
    for field, model in models.items():
        identifier = values[field]
        if field == 'cliente' and identifier is None:
            raise ValueError('Selecciona un cliente.')
        if identifier is None and field != 'cliente':
            continue
        if isinstance(identifier, bool) or not str(identifier).isdigit():
            raise ValueError(f'El identificador de {field} no es válido.')
        related = model.objects.filter(pk=int(identifier)).first()
        if related is None:
            raise ValueError(f'No existe el registro indicado para {field}.')
        values[field] = related

    vehicle_changed = pedido is None or values['vehiculo'] and values['vehiculo'].pk != pedido.vehiculo_id
    if values['vehiculo']:
        if vehicle_changed:
            for field in ('pintura', 'rueda', 'silla', 'luces'):
                if field not in data:
                    values[field] = getattr(values['vehiculo'], field)
    elif sum(values[field] is not None for field in ('pintura', 'rueda', 'silla', 'luces')) != 1:
        raise ValueError('Una venta de accesorio debe incluir exactamente un accesorio.')

    try:
        total = Decimal(str(values['total']))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError('El total debe ser un número entero válido.')
    if not total.is_finite() or total < 0 or total >= Decimal('1000000000000') or total != total.to_integral_value():
        raise ValueError('El total debe ser un entero entre 0 y 999999999999.')
    values['total'] = total
    return {f'{field}_id' if field != 'total' else field: getattr(value, 'pk', value)
            for field, value in values.items()}


@require_GET
def api_sales_options(request):
    denial = sales_api_denial(request)
    if denial:
        return denial

    products = [{
        'key': f'vehiculo-{vehicle.id}',
        'label': f'{vehicle.marca} {vehicle.modelo}',
        'total': str(vehicle.valor_base + vehicle.pintura.valor + vehicle.silla.valor
                     + vehicle.luces.valor + (vehicle.rueda.valor if vehicle.rueda else 0)),
        'data': {
            'vehiculo': vehicle.id,
            'pintura': vehicle.pintura_id,
            'rueda': vehicle.rueda_id,
            'silla': vehicle.silla_id,
            'luces': vehicle.luces_id,
        },
    } for vehicle in Vehiculo.objects.filter(activo=True).select_related(
        'pintura', 'rueda', 'silla', 'luces'
    )]
    for model, kind, name_field in [
        (Pintura, 'pintura', 'color'),
        (Rueda, 'rueda', 'descripcion'),
        (Silla, 'silla', 'descripcion'),
        (Luces, 'luces', 'color'),
    ]:
        products.extend({
            'key': f'{kind}-{item.id}',
            'label': f'{kind.title()}: {getattr(item, name_field)}',
            'total': str(item.valor),
            'data': {'vehiculo': None, 'pintura': None, 'rueda': None, 'silla': None, 'luces': None, kind: item.id},
        } for item in model.objects.filter(activo=True))

    return JsonResponse({
        'clientes': [{
            'id': client.id,
            'nombre': f'{client.nombre} {client.apellido}',
        } for client in UsuarioCliente.objects.order_by('nombre', 'apellido')],
        'productos': products,
    })


@require_http_methods(['GET', 'POST'])
def api_sales(request):
    denial = sales_api_denial(request)
    if denial:
        return denial

    if request.method == 'POST':
        try:
            values = read_sale_data(request)
        except ValueError as error:
            return JsonResponse({'error': str(error)}, status=400)
        pedido = Pedido.objects.create(**values)
        pedido = Pedido.objects.select_related(
            'cliente', 'vehiculo', 'vehiculo__pintura', 'vehiculo__rueda',
            'vehiculo__silla', 'vehiculo__luces', 'pintura', 'rueda', 'silla', 'luces'
        ).get(pk=pedido.pk)
        return JsonResponse(serialize_sale(pedido), status=201)

    pedidos = Pedido.objects.select_related(
        'cliente', 'vehiculo', 'vehiculo__pintura', 'vehiculo__rueda',
        'vehiculo__silla', 'vehiculo__luces', 'pintura', 'rueda', 'silla', 'luces'
    ).order_by('-fecha', '-id')
    client_id = request.GET.get('cliente')
    if client_id:
        if not client_id.isdigit():
            return JsonResponse({'error': 'El identificador del cliente no es válido.'}, status=400)
        pedidos = pedidos.filter(cliente_id=int(client_id))

    page = Paginator(pedidos, 5).get_page(request.GET.get('page'))
    return JsonResponse({
        'count': page.paginator.count,
        'total_ventas': str(pedidos.aggregate(total=Sum('total'))['total'] or 0),
        'page': page.number,
        'pages': page.paginator.num_pages,
        'results': [serialize_sale(pedido) for pedido in page.object_list],
    })


@require_http_methods(['GET', 'PATCH', 'DELETE'])
def api_sale_detail(request, sale_id):
    denial = sales_api_denial(request)
    if denial:
        return denial
    pedido = Pedido.objects.select_related(
        'cliente', 'vehiculo', 'vehiculo__pintura', 'vehiculo__rueda',
        'vehiculo__silla', 'vehiculo__luces', 'pintura', 'rueda', 'silla', 'luces'
    ).filter(pk=sale_id).first()
    if pedido is None:
        return JsonResponse({'error': 'Venta no encontrada.'}, status=404)

    if request.method == 'GET':
        return JsonResponse(serialize_sale(pedido))
    if request.method == 'DELETE':
        pedido.delete()
        return HttpResponse(status=204)

    try:
        values = read_sale_data(request, pedido)
    except ValueError as error:
        return JsonResponse({'error': str(error)}, status=400)
    Pedido.objects.filter(pk=pedido.pk).update(**values)
    pedido.refresh_from_db()
    return JsonResponse(serialize_sale(pedido))


def fetch_public_json(url):
    try:
        with urlopen(url, timeout=5) as response:
            return json.loads(response.read())
    except (OSError, ValueError):
        return None


def integrations(request):
    makes_data = fetch_public_json(
        'https://vpic.nhtsa.dot.gov/api/vehicles/GetMakesForVehicleType/car?format=json'
    )
    dog_data = fetch_public_json('https://dog.ceo/api/breeds/image/random')
    joke_data = fetch_public_json('https://official-joke-api.appspot.com/jokes/random')
    makes = makes_data.get('Results', []) if isinstance(makes_data, dict) else []
    dog_image = dog_data.get('message') if isinstance(dog_data, dict) and dog_data.get('status') == 'success' else None
    if not isinstance(dog_image, str) or urlsplit(dog_image).netloc != 'images.dog.ceo' or urlsplit(dog_image).scheme != 'https':
        dog_image = None
    return render(request, 'store/integrations.html', {
        'vehicle_makes': makes[:8] if isinstance(makes, list) else [],
        'dog_image': dog_image,
        'joke': joke_data if isinstance(joke_data, dict)
        and isinstance(joke_data.get('setup'), str)
        and isinstance(joke_data.get('punchline'), str) else None,
    })


@require_GET
def api_random_plate_name(request):
    data = fetch_public_json('https://api.datamuse.com/words?ml=car&max=100&md=p')
    if not isinstance(data, list):
        return JsonResponse({'error': 'No se pudieron encontrar sustantivos ahora mismo.'}, status=503)
    nouns = [
        item['word'].upper()
        for item in data
        if isinstance(item, dict)
        and isinstance(item.get('word'), str)
        and item['word'].isascii()
        and item['word'].isalpha()
        and len(item['word']) <= 8
        and isinstance(item.get('tags'), list)
        and 'n' in item['tags']
    ]
    if len(nouns) < 2:
        return JsonResponse({'error': 'La API no devolvió suficientes sustantivos.'}, status=502)
    return JsonResponse({'name': ' '.join(random.sample(nouns, 2))})


def accessories(request):
    accessory_list = []
    pinturas = Pintura.objects.filter(activo=True)
    sillas = Silla.objects.filter(activo=True)
    ruedas = Rueda.objects.filter(activo=True)
    luces = Luces.objects.filter(activo=True)

    for item in pinturas:
        accessory_list.append({'id': item.id, 'url_name': 'accesorio_detalle', 'kind': 'Pintura', 'name': f'Pintura {item.color}', 'price': f'${item.valor:,.0f}', 'description': item.descripcion})
    for item in sillas:
        accessory_list.append({'id': item.id, 'url_name': 'accesorio_detalle', 'kind': 'Silla', 'name': f'Silla {item.descripcion}', 'price': f'${item.valor:,.0f}', 'description': 'Accesorio interior premium'})
    for item in ruedas:
        accessory_list.append({'id': item.id, 'url_name': 'accesorio_detalle', 'kind': 'Rueda', 'name': f'Rueda {item.descripcion}', 'price': f'${item.valor:,.0f}', 'description': 'Rueda para miniatura especializada'})
    for item in luces:
        accessory_list.append({'id': item.id, 'url_name': 'accesorio_detalle', 'kind': 'Luz', 'name': f'Luz {item.color}', 'price': f'${item.valor:,.0f}', 'description': item.descripcion})

    context = {
        'title': 'Accesorios',
        'items': accessory_list,
    }
    return render(request, 'store/accessories.html', context)


def vehicle_detail(request, vehicle_id):
    vehicle = get_object_or_404(Vehiculo, id=vehicle_id, activo=True)
    estimated_total = vehicle.valor_base + vehicle.pintura.valor + vehicle.silla.valor + vehicle.luces.valor + (vehicle.rueda.valor if vehicle.rueda else 0)
    context = {
        'vehicle': vehicle,
        'base_total': vehicle.valor_base,
        'paint_options': Pintura.objects.filter(activo=True),
        'wheel_options': Rueda.objects.filter(activo=True),
        'seat_options': Silla.objects.filter(activo=True),
        'light_options': Luces.objects.filter(activo=True),
        'selected_paint': vehicle.pintura,
        'selected_wheel': vehicle.rueda,
        'selected_seat': vehicle.silla,
        'selected_light': vehicle.luces,
        'estimated_total': estimated_total,
    }
    return render(request, 'store/vehicle_detail.html', context)


def accessory_detail(request, accessory_id):
    item = None
    item_type = None

    for model, label in [(Pintura, 'Pintura'), (Rueda, 'Rueda'), (Silla, 'Silla'), (Luces, 'Luz')]:
        obj = model.objects.filter(id=accessory_id, activo=True).first()
        if obj:
            item = obj
            item_type = label
            break

    if item is None:
        return redirect('accesorios')

    return render(request, 'store/accessory_detail.html', {'item': item, 'item_type': item_type})


@login_required
def purchase_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(Vehiculo, id=vehicle_id, activo=True)
    role = get_user_role(request.user)
    if role != 'cliente':
        messages.info(request, 'Solo los clientes pueden comprar vehículos.')
        return redirect('home')

    cliente = UsuarioCliente.objects.filter(correo=request.user.email).first()
    if cliente is None:
        messages.info(request, 'Debes tener un perfil de cliente para comprar.')
        return redirect('login')

    if request.method != 'POST':
        return redirect('vehiculo_detalle', vehicle_id=vehicle.id)

    paint_id = request.POST.get('pintura') or vehicle.pintura_id
    wheel_id = request.POST.get('rueda') or (vehicle.rueda_id if vehicle.rueda_id else None)
    seat_id = request.POST.get('silla') or vehicle.silla_id
    light_id = request.POST.get('luces') or vehicle.luces_id

    paint = get_object_or_404(Pintura, id=paint_id, activo=True)
    wheel = get_object_or_404(Rueda, id=wheel_id, activo=True) if wheel_id else None
    seat = get_object_or_404(Silla, id=seat_id, activo=True)
    light = get_object_or_404(Luces, id=light_id, activo=True)

    total = vehicle.valor_base + paint.valor + seat.valor + light.valor + (wheel.valor if wheel else 0)
    Pedido.objects.create(
        cliente=cliente,
        vehiculo=vehicle,
        pintura=paint,
        rueda=wheel,
        silla=seat,
        luces=light,
        total=total,
    )

    messages.success(request, f'Compra confirmada. Total: ${total:,.0f}')
    return redirect('mis_compras')


@login_required
def purchase_accessory(request, accessory_id):
    role = get_user_role(request.user)
    if role != 'cliente':
        messages.info(request, 'Solo los clientes pueden comprar accesorios.')
        return redirect('home')

    cliente = UsuarioCliente.objects.filter(correo=request.user.email).first()
    if cliente is None:
        messages.info(request, 'Debes tener un perfil de cliente para comprar.')
        return redirect('login')

    accessory = None
    item_type = None
    for model, label in [(Pintura, 'pintura'), (Rueda, 'rueda'), (Silla, 'silla'), (Luces, 'luces')]:
        obj = model.objects.filter(id=accessory_id, activo=True).first()
        if obj:
            accessory = obj
            item_type = label
            break

    if accessory is None:
        return redirect('accesorios')

    total = accessory.valor
    Pedido.objects.create(
        cliente=cliente,
        vehiculo=None,
        pintura=accessory if item_type == 'pintura' else None,
        rueda=accessory if item_type == 'rueda' else None,
        silla=accessory if item_type == 'silla' else None,
        luces=accessory if item_type == 'luces' else None,
        total=total,
    )

    messages.success(request, f'Accesorio agregado al pedido. Total: ${total:,.0f}')
    return redirect('mis_compras')


def contact(request):
    return render(request, 'store/contact.html')


def login_page(request):
    if request.user.is_authenticated:
        role = get_user_role(request.user)
        if role in {'admin', 'empleado'}:
            return redirect('panel')
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email__iexact=email).first()
            if user is not None:
                login(request, user)
                role = get_user_role(user)
                messages.success(request, 'Has iniciado sesión correctamente.')
                if role in {'admin', 'empleado'}:
                    return redirect('panel')
                return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'store/login.html', {'form': form})


def register_page(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registro exitoso. Bienvenido a MiniMachines.')
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'store/register.html', {'form': form})


def panel(request):
    if not request.user.is_authenticated:
        return redirect('login')

    role = get_user_role(request.user)
    if role not in {'admin', 'empleado'}:
        messages.info(request, 'Bienvenido a MiniMachines, cliente.')
        return redirect('home')

    selected_client_id = request.GET.get('cliente')
    if selected_client_id and not selected_client_id.isdigit():
        selected_client_id = None
    pedidos = Pedido.objects.select_related(
        'cliente', 'vehiculo', 'pintura', 'rueda', 'silla', 'luces'
    ).order_by('-fecha', '-id')

    if selected_client_id:
        pedidos = pedidos.filter(cliente_id=selected_client_id)

    clientes = UsuarioCliente.objects.order_by('nombre', 'apellido')
    selected_client = None
    if selected_client_id:
        selected_client = clientes.filter(id=selected_client_id).first()

    total_pedidos = pedidos.count()
    total_ventas = sum(p.total for p in pedidos)

    return render(request, 'store/panel.html', {
        'role': role,
        'user_name': request.user.first_name or request.user.username,
        'clientes': clientes,
        'selected_client': selected_client,
        'selected_client_id': selected_client_id,
        'total_pedidos': total_pedidos,
        'total_ventas': total_ventas,
    })


@login_required
def my_orders(request):
    role = get_user_role(request.user)
    if role != 'cliente':
        messages.info(request, 'Esta vista es solo para clientes.')
        return redirect('home')

    cliente = UsuarioCliente.objects.filter(correo=request.user.email).first()
    if cliente is None:
        messages.info(request, 'No encontramos tu perfil de cliente.')
        return redirect('home')

    pedidos = Pedido.objects.filter(cliente=cliente).select_related(
        'vehiculo', 'vehiculo__pintura', 'vehiculo__rueda', 'vehiculo__silla', 'vehiculo__luces',
        'pintura', 'rueda', 'silla', 'luces'
    ).order_by('-fecha')

    return render(request, 'store/my_orders.html', {
        'role': role,
        'pedidos': pedidos,
        'cliente': cliente,
    })


def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('home')
