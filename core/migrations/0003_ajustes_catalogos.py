from django.db import migrations, models
import django.db.models.deletion

def seed_estados_iniciales(apps, schema_editor):
    EstadoDispositivo = apps.get_model('core', 'EstadoDispositivo')
    estados = [
        ('Disponible', '#10B981'),      # Verde
        ('Asignado', '#3B82F6'),        # Azul
        ('En Reparación', '#F59E0B'),  # Ámbar
        ('De Baja', '#EF4444'),         # Rojo
    ]
    for nombre, color in estados:
        EstadoDispositivo.objects.get_or_create(nombre=nombre, defaults={'color': color})

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_tipodispositivo_sigla'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Estado',
            new_name='EstadoDispositivo',
        ),
        migrations.AlterModelOptions(
            name='estadodispositivo',
            options={'verbose_name': 'Estado de Dispositivo', 'verbose_name_plural': 'Estados de Dispositivo'},
        ),
        migrations.AddField(
            model_name='estadodispositivo',
            name='color',
            field=models.CharField(default='#6B7280', help_text='Hex color para el badge', max_length=7),
        ),
        migrations.AlterField(
            model_name='modelo',
            name='fabricante',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='modelos', to='core.fabricante'),
        ),
        migrations.RunPython(seed_estados_iniciales),
    ]
