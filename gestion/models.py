from django.db import models
from django.core.exceptions import ValidationError
from django.utils.html import format_html

# Create your models here.
from django.db import models

class Medicament(models.Model):
    nom = models.CharField(max_length=100)
    categorie = models.CharField(max_length=100)
    prix = models.DecimalField(max_digits=8, decimal_places=2)
    quantite_en_stock = models.IntegerField()
    seuil_alerte = models.IntegerField(default=10)  # Seuil d'alerte pour stock bas

    def __str__(self):
        return self.nom

    def est_en_rupture(self):
        return self.quantite_en_stock <= 0

    def stock_faible(self):
        return self.quantite_en_stock <= self.seuil_alerte

    def get_status_stock(self):
        if self.est_en_rupture():
            return format_html('<span style="color: red; font-weight: bold;">Rupture de stock</span>')
        elif self.stock_faible():
            return format_html('<span style="color: orange; font-weight: bold;">Stock faible ({} unités)</span>', self.quantite_en_stock)
        return format_html('<span style="color: green;">En stock ({} unités)</span>', self.quantite_en_stock)

    def ajuster_stock(self, quantite):
        nouvelle_quantite = self.quantite_en_stock - quantite
        if nouvelle_quantite < 0:
            raise ValidationError("Stock insuffisant")
        self.quantite_en_stock = nouvelle_quantite
        self.save()

class Client(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    adresse = models.TextField()
    telephone = models.CharField(max_length=15)
    est_regulier = models.BooleanField(default=False)
    credit = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Crédit disponible
    plafond_credit = models.DecimalField(max_digits=10, decimal_places=2, default=1000)  # Limite de crédit

    def __str__(self):
        return f"{self.nom} {self.prenom}"

    def get_historique_achats(self):
        return self.commande_set.all().order_by('-date_commande')

    def peut_acheter_a_credit(self, montant):
        return (self.credit + montant) <= self.plafond_credit

class Commande(models.Model):
    STATUT_CHOICES = [
        ('En attente', 'En attente'),
        ('Expédiée', 'Expédiée'),
        ('Annulée', 'Annulée')
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    medicaments = models.ManyToManyField(Medicament, through='LigneCommande')
    date_commande = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='En attente')

    def calculer_total(self):
        return sum(ligne.sous_total() for ligne in self.lignes.all())

    def valider_commande(self):
        for ligne in self.lignes.all():
            ligne.medicament.ajuster_stock(ligne.quantite)
        self.statut = 'Expédiée'
        self.save()

    def __str__(self):
        return f"Commande #{self.id} - {self.client} - {self.calculer_total()}€"

class LigneCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='lignes')
    medicament = models.ForeignKey(Medicament, on_delete=models.CASCADE)
    quantite = models.IntegerField(default=1)
    prix_unitaire = models.DecimalField(max_digits=8, decimal_places=2, editable=False, default=0)

    def save(self, *args, **kwargs):
        if not self.prix_unitaire:
            self.prix_unitaire = self.medicament.prix
        
        # Vérifier si c'est une nouvelle ligne
        if not self.pk:
            # Vérifier le stock disponible
            if self.quantite > self.medicament.quantite_en_stock:
                raise ValidationError(f"Stock insuffisant pour {self.medicament.nom}. Disponible: {self.medicament.quantite_en_stock}")
            # Mettre à jour le stock
            self.medicament.quantite_en_stock -= self.quantite
            self.medicament.save()
        else:
            # Pour une mise à jour, récupérer l'ancienne quantité
            ancien = LigneCommande.objects.get(pk=self.pk)
            difference = self.quantite - ancien.quantite
            if difference > 0:  # Si on augmente la quantité
                if difference > self.medicament.quantite_en_stock:
                    raise ValidationError(f"Stock insuffisant pour {self.medicament.nom}. Disponible: {self.medicament.quantite_en_stock}")
                self.medicament.quantite_en_stock -= difference
            else:  # Si on diminue la quantité
                self.medicament.quantite_en_stock += abs(difference)
            self.medicament.save()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Restaurer le stock lors de la suppression
        self.medicament.quantite_en_stock += self.quantite
        self.medicament.save()
        super().delete(*args, **kwargs)

    def sous_total(self):
        return self.quantite * self.prix_unitaire

    def clean(self):
        if self.quantite <= 0:
            raise ValidationError("La quantité doit être supérieure à 0")
        if not self.pk and self.quantite > self.medicament.quantite_en_stock:
            raise ValidationError("Quantité demandée non disponible en stock")

    def __str__(self):
        return f"{self.medicament.nom} x{self.quantite}"

class Facture(models.Model):
    METHODE_PAIEMENT_CHOICES = [
        ('ESP', 'Espèces'),
        ('CB', 'Carte Bancaire'),
        ('CHQ', 'Chèque'),
        ('CRD', 'Crédit')
    ]

    commande = models.OneToOneField(Commande, on_delete=models.CASCADE)
    date_facture = models.DateTimeField(auto_now_add=True)
    remise = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="Remise en pourcentage (ex: 10 pour 10%)")
    montant_total = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    montant_paye = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    methode_paiement = models.CharField(max_length=3, choices=METHODE_PAIEMENT_CHOICES, default='ESP')
    est_payee = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.commande and (not self.pk or not self.montant_total):
            self.montant_total = self.commande.calculer_total() or 0
            
            # Vérifier le plafond de crédit si paiement par crédit
            if self.methode_paiement == 'CRD':
                client = self.commande.client
                montant_final = self.montant_final()
                if client.credit + montant_final > client.plafond_credit:
                    raise ValidationError(
                        f"Le montant dépasse le plafond de crédit disponible. "
                        f"Crédit actuel: {client.credit}€, "
                        f"Plafond: {client.plafond_credit}€, "
                        f"Montant facture: {montant_final}€"
                    )
                # Mettre à jour le crédit du client
                client.credit += montant_final
                client.save()

        super().save(*args, **kwargs)

    def montant_final(self):
        if not self.montant_total:
            return 0
        remise_decimale = float(self.remise or 0) / 100
        montant_remise = float(self.montant_total) * remise_decimale
        return float(self.montant_total) - montant_remise

    def montant_restant(self):
        return self.montant_final() - float(self.montant_paye or 0)

    def __str__(self):
        status = "Payée" if self.est_payee else f"Reste {self.montant_restant():.2f}€"
        methode = dict(self.METHODE_PAIEMENT_CHOICES)[self.methode_paiement]
        return f"Facture #{self.id} - {self.commande.client} - Total: {self.montant_final():.2f}€ ({status}) - {methode}"

class Paiement(models.Model):
    METHODE_CHOICES = [
        ('ESP', 'Espèces'),
        ('CB', 'Carte Bancaire'),
        ('CHQ', 'Chèque'),
        ('CRD', 'Crédit')
    ]

    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, related_name='paiements')
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    methode = models.CharField(max_length=3, choices=METHODE_CHOICES)
    date_paiement = models.DateTimeField(auto_now_add=True)
    est_valide = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.methode == 'CRD':
            client = self.facture.commande.client
            if not client.peut_acheter_a_credit(self.montant):
                raise ValidationError("Limite de crédit dépassée")
            client.credit += self.montant
            client.save()
        super().save(*args, **kwargs)
