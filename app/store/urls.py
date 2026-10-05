from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('store/', views.store, name='store'),
    path('vehiculos/', views.vehicles, name='vehiculos'),
    path('api/vehiculos/', views.api_vehicles, name='api_vehiculos'),
    path('api/accesorios/', views.api_accessories, name='api_accesorios'),
    path('integraciones/', views.integrations, name='integraciones'),
    path('vehiculos/<int:vehicle_id>/', views.vehicle_detail, name='vehiculo_detalle'),
    path('accesorios/', views.accessories, name='accesorios'),
    path('accesorios/<int:accessory_id>/', views.accessory_detail, name='accesorio_detalle'),
    path('comprar-vehiculo/<int:vehicle_id>/', views.purchase_vehicle, name='comprar_vehiculo'),
    path('comprar-accesorio/<int:accessory_id>/', views.purchase_accessory, name='comprar_accesorio'),
    path('contacto/', views.contact, name='contacto'),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.register_page, name='register'),
    path('panel/', views.panel, name='panel'),
    path('mis-compras/', views.my_orders, name='mis_compras'),
]