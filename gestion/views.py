from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from .models import Medicament, Client, Commande, Facture, Paiement
from .serializers import (
    MedicamentSerializer, 
    ClientSerializer, 
    CommandeSerializer, 
    FactureSerializer,
    PaiementSerializer
)

class MedicamentViewSet(viewsets.ModelViewSet):
    queryset = Medicament.objects.all()
    serializer_class = MedicamentSerializer

    @action(detail=True, methods=['post'])
    def ajuster_stock(self, request, pk=None):
        medicament = self.get_object()
        quantite = request.data.get('quantite', 0)
        try:
            medicament.ajuster_stock(quantite)
            return Response({'status': 'Stock ajusté'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class StockAlerteView(viewsets.ViewSet):
    def rupture_stock(self, request):
        medicaments = Medicament.objects.filter(quantite_en_stock=0)
        serializer = MedicamentSerializer(medicaments, many=True)
        return Response(serializer.data)

    def stock_faible(self, request):
        medicaments = [med for med in Medicament.objects.all() if med.stock_faible()]
        serializer = MedicamentSerializer(medicaments, many=True)
        return Response(serializer.data)

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    @action(detail=True, methods=['post'])
    def toggle_regulier(self, request, pk=None):
        client = self.get_object()
        client.est_regulier = not client.est_regulier
        client.save()
        return Response({'est_regulier': client.est_regulier})

    @action(detail=True, methods=['get'])
    def credit_info(self, request, pk=None):
        client = self.get_object()
        return Response({
            'credit_actuel': client.credit,
            'plafond_credit': client.plafond_credit,
            'credit_disponible': client.plafond_credit - client.credit
        })

class ClientHistoriqueView(APIView):
    def get(self, request, pk):
        client = Client.objects.get(pk=pk)
        commandes = client.get_historique_achats()
        serializer = CommandeSerializer(commandes, many=True)
        return Response(serializer.data)

class CommandeViewSet(viewsets.ModelViewSet):
    queryset = Commande.objects.all()
    serializer_class = CommandeSerializer

    @action(detail=True, methods=['post'])
    def valider_commande(self, request, pk=None):
        commande = self.get_object()
        try:
            commande.valider_commande()
            return Response({'status': 'Commande validée'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def annuler_commande(self, request, pk=None):
        commande = self.get_object()
        commande.statut = 'Annulée'
        commande.save()
        return Response({'status': 'Commande annulée'})

class FactureViewSet(viewsets.ModelViewSet):
    queryset = Facture.objects.all()
    serializer_class = FactureSerializer

class StatistiquesView(viewsets.ViewSet):
    def ventes(self, request):
        # Statistiques des ventes sur les 30 derniers jours
        date_debut = timezone.now() - timedelta(days=30)
        stats = {
            'total_ventes': Facture.objects.filter(date_facture__gte=date_debut).count(),
            'montant_total': Facture.objects.filter(date_facture__gte=date_debut).aggregate(
                total=Sum('montant_total'))['total'] or 0,
            'ventes_par_jour': Facture.objects.filter(date_facture__gte=date_debut)
                .values('date_facture__date')
                .annotate(total=Count('id'))
        }
        return Response(stats)

    def stock(self, request):
        # Statistiques du stock
        stats = {
            'rupture_stock': Medicament.objects.filter(quantite_en_stock=0).count(),
            'stock_faible': len([med for med in Medicament.objects.all() if med.stock_faible()]),
            'valeur_stock_total': sum(med.prix * med.quantite_en_stock for med in Medicament.objects.all())
        }
        return Response(stats)

class PaiementViewSet(viewsets.ModelViewSet):
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer

    @action(detail=False, methods=['post'])
    def ajouter_paiement(self, request):
        facture_id = request.data.get('facture')
        montant = request.data.get('montant')
        methode = request.data.get('methode')

        try:
            facture = Facture.objects.get(pk=facture_id)
            paiement = facture.ajouter_paiement(montant, methode)
            serializer = self.get_serializer(paiement)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
