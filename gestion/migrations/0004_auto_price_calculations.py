from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0003_add_ligne_facture'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lignefacture',
            name='prix_unitaire',
            field=models.DecimalField(decimal_places=2, max_digits=8, editable=False),
        ),
        migrations.AlterField(
            model_name='facture',
            name='montant_total',
            field=models.DecimalField(decimal_places=2, max_digits=8, editable=False),
        ),
    ] 