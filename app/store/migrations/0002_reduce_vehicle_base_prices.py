from decimal import Decimal

from django.db import migrations


def reduce_vehicle_prices(apps, schema_editor):
    Vehiculo = apps.get_model('store', 'Vehiculo')
    for vehicle in Vehiculo.objects.using(schema_editor.connection.alias).all().iterator():
        vehicle.valor_base = (Decimal(vehicle.valor_base) / 10).quantize(Decimal('1'))
        vehicle.save(using=schema_editor.connection.alias, update_fields=['valor_base'])


def restore_vehicle_prices(apps, schema_editor):
    Vehiculo = apps.get_model('store', 'Vehiculo')
    for vehicle in Vehiculo.objects.using(schema_editor.connection.alias).all().iterator():
        vehicle.valor_base = Decimal(vehicle.valor_base) * 10
        vehicle.save(using=schema_editor.connection.alias, update_fields=['valor_base'])


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(reduce_vehicle_prices, restore_vehicle_prices),
    ]
