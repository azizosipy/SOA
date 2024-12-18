from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0002_add_seuil_alerte'),
    ]

    operations = [
        migrations.CreateModel(
            name='LigneFacture',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantite', models.IntegerField()),
                ('prix_unitaire', models.DecimalField(decimal_places=2, max_digits=8)),
                ('facture', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lignes', to='gestion.facture')),
                ('medicament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gestion.medicament')),
            ],
        ),
        migrations.AddField(
            model_name='facture',
            name='medicaments',
            field=models.ManyToManyField(through='gestion.LigneFacture', to='gestion.medicament'),
        ),
    ] 