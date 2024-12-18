# gestion/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MedicamentViewSet, 
    ClientViewSet, 
    CommandeViewSet, 
    FactureViewSet,
    StockAlerteView,
    ClientHistoriqueView,
    StatistiquesView,
    PaiementViewSet
)

router = DefaultRouter()
router.register(r'medicaments', MedicamentViewSet)
router.register(r'clients', ClientViewSet)
router.register(r'commandes', CommandeViewSet)
router.register(r'factures', FactureViewSet)
router.register(r'paiements', PaiementViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    
    # URLs pour la gestion des médicaments
    path('api/medicaments/rupture/', StockAlerteView.as_view({'get': 'rupture_stock'}), name='rupture-stock'),
    path('api/medicaments/stock-faible/', StockAlerteView.as_view({'get': 'stock_faible'}), name='stock-faible'),
    path('api/medicaments/<int:pk>/ajuster-stock/', MedicamentViewSet.as_view({'post': 'ajuster_stock'}), name='ajuster-stock'),
    
    # URLs pour la gestion des clients
    path('api/clients/<int:pk>/historique/', ClientHistoriqueView.as_view(), name='client-historique'),
    path('api/clients/<int:pk>/toggle-regulier/', ClientViewSet.as_view({'post': 'toggle_regulier'}), name='toggle-regulier'),
    path('api/clients/<int:pk>/credit/', ClientViewSet.as_view({'get': 'credit_info'}), name='credit-client'),
    
    # URLs pour les commandes
    path('api/commandes/<int:pk>/valider/', CommandeViewSet.as_view({'post': 'valider_commande'}), name='valider-commande'),
    path('api/commandes/<int:pk>/annuler/', CommandeViewSet.as_view({'post': 'annuler_commande'}), name='annuler-commande'),
    
    # URLs pour les statistiques
    path('api/statistiques/ventes/', StatistiquesView.as_view({'get': 'ventes'}), name='stats-ventes'),
    path('api/statistiques/stock/', StatistiquesView.as_view({'get': 'stock'}), name='stats-stock'),
    path('api/factures/<int:pk>/paiement/', PaiementViewSet.as_view({'post': 'ajouter_paiement'}), name='ajouter-paiement'),
]
