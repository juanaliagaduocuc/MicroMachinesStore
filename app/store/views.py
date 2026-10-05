import json
from urllib.request import urlopen

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET

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
    exchange_data = fetch_public_json('https://open.er-api.com/v6/latest/USD')
    makes = makes_data.get('Results', []) if isinstance(makes_data, dict) else []
    rates = exchange_data.get('rates', {}) if isinstance(exchange_data, dict) else {}
    return render(request, 'store/integrations.html', {
        'vehicle_makes': makes[:8] if isinstance(makes, list) else [],
        'clp_rate': rates.get('CLP') if isinstance(rates, dict) else None,
        'exchange_updated': exchange_data.get('time_last_update_utc') if isinstance(exchange_data, dict) else None,
    })


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
    pedidos = Pedido.objects.select_related(
        'cliente', 'vehiculo', 'pintura', 'rueda', 'silla', 'luces'
    ).order_by('-fecha')

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
        'pedidos': pedidos,
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
