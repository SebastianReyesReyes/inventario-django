from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('dispositivos', '0001_initial'),
        ('core', '0003_ajustes_catalogos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dispositivo',
            name='estado',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.estadodispositivo'),
        ),
    ]
