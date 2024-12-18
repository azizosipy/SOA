from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicament',
            name='seuil_alerte',
            field=models.IntegerField(default=10),
        ),
        migrations.AddField(
            model_name='client',
            name='est_regulier',
            field=models.BooleanField(default=False),
        ),
    ] 