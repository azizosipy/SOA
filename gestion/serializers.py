from rest_framework import serializers
from .models import Medicament, Client, Commande, Facture, LigneCommande, Paiement

class MedicamentSerializer(serializers.ModelSerializer):
    status_stock = serializers.SerializerMethodField()
    en_rupture = serializers.BooleanField(read_only=True)
    stock_faible = serializers.BooleanField(read_only=True)

    class Meta:
        model = Medicament
        fields = ['id', 'nom', 'categorie', 'prix', 'quantite_en_stock', 
                 'seuil_alerte', 'status_stock', 'en_rupture', 'stock_faible']

    def get_status_stock(self, obj):
        if obj.est_en_rupture():
            return "Rupture de stock"
        elif obj.stock_faible():
            return f"Stock faible ({obj.quantite_en_stock} unités)"
        return f"En stock ({obj.quantite_en_stock} unités)"

class ClientSerializer(serializers.ModelSerializer):
    credit_disponible = serializers.DecimalField(
        source='plafond_credit', 
        read_only=True,
        max_digits=10, 
        decimal_places=2
    )
    
    class Meta:
        model = Client
        fields = ['id', 'nom', 'prenom', 'adresse', 'telephone', 
                 'est_regulier', 'credit', 'plafond_credit', 'credit_disponible']

class LigneCommandeSerializer(serializers.ModelSerializer):
    nom_medicament = serializers.CharField(source='medicament.nom', read_only=True)
    prix_unitaire = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    sous_total = serializers.DecimalField(source='sous_total', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = LigneCommande
        fields = ['id', 'medicament', 'nom_medicament', 'quantite', 'prix_unitaire', 'sous_total']

class CommandeSerializer(serializers.ModelSerializer):
    lignes = LigneCommandeSerializer(many=True)
    total = serializers.DecimalField(source='calculer_total', max_digits=10, decimal_places=2, read_only=True)
    client_nom = serializers.CharField(source='client.__str__', read_only=True)

    class Meta:
        model = Commande
        fields = ['id', 'client', 'client_nom', 'date_commande', 'statut', 'total', 'lignes']

    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes')
        commande = Commande.objects.create(**validated_data)
        
        for ligne_data in lignes_data:
            LigneCommande.objects.create(commande=commande, **ligne_data)
        
        return commande

    def update(self, instance, validated_data):
        lignes_data = validated_data.pop('lignes', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if lignes_data is not None:
            instance.lignes.all().delete()
            for ligne_data in lignes_data:
                LigneCommande.objects.create(commande=instance, **ligne_data)
            
        return instance

class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = ['id', 'facture', 'montant', 'methode', 'date_paiement', 'est_valide']

class FactureSerializer(serializers.ModelSerializer):
    paiements = PaiementSerializer(many=True, read_only=True)
    montant_restant = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Facture
        fields = ['id', 'commande', 'date_facture', 'montant_total', 
                 'remise', 'montant_final', 'montant_paye', 'est_payee',
                 'montant_restant', 'paiements']
