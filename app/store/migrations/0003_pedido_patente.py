from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_reduce_vehicle_base_prices'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='patente',
            field=models.CharField(default='patente', max_length=20),
        ),
    ]
