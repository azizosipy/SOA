from django.contrib import admin
from django.utils.html import format_html
from .models import Medicament, Client, Commande, Facture, LigneCommande
from django.core.exceptions import ValidationError

class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 1
    readonly_fields = ('prix_unitaire', 'sous_total', 'status_stock')
    
    def sous_total(self, instance):
        if instance.pk:
            return instance.sous_total()
        return 0
    
    def status_stock(self, instance):
        if instance.pk:
            med = instance.medicament
            stock_dispo = med.quantite_en_stock + instance.quantite  # Stock total disponible
            if stock_dispo <= 0:
                return format_html('<b style="color: red;">RUPTURE DE STOCK!</b>')
            elif stock_dispo <= med.seuil_alerte:
                return format_html('<b style="color: orange;">Stock faible ({} disponibles)</b>', stock_dispo)
            return format_html('<b style="color: green;">En stock ({} disponibles)</b>', stock_dispo)
        return ""
    status_stock.short_description = "État du stock"

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        form = formset.form
        
        def clean_quantite(self):
            quantite = self.cleaned_data.get('quantite')
            medicament = self.cleaned_data.get('medicament')
            instance = self.instance
            
            if quantite and medicament:
                stock_disponible = medicament.quantite_en_stock
                if instance.pk:  # Si modification
                    stock_disponible += instance.quantite
                if quantite > stock_disponible:
                    raise ValidationError(f"Stock insuffisant. Disponible: {stock_disponible}")
            return quantite
        
        form.clean_quantite = clean_quantite
        return formset

class CommandeAdmin(admin.ModelAdmin):
    inlines = [LigneCommandeInline]
    list_display = ['id', 'client', 'statut', 'date_commande', 'total', 'alerte_stock']
    readonly_fields = ['date_commande']
    list_filter = ['statut']
    search_fields = ['client__nom', 'client__prenom']
    
    def total(self, obj):
        return f"{obj.calculer_total()}€"
    
    def alerte_stock(self, obj):
        alertes = []
        for ligne in obj.lignes.all():
            med = ligne.medicament
            if med.est_en_rupture():
                alertes.append(format_html('<div style="color: red;">❌ {} en rupture!</div>', med.nom))
            elif med.stock_faible():
                alertes.append(format_html('<div style="color: orange;">⚠️ {} stock faible ({} unités)</div>', 
                                        med.nom, med.quantite_en_stock))
        return format_html(''.join(alertes)) if alertes else "✅ Stock OK"
    alerte_stock.short_description = "Alertes Stock"

class MedicamentAdmin(admin.ModelAdmin):
    list_display = ['nom', 'categorie', 'prix', 'quantite_en_stock', 'status_stock']
    list_filter = ['categorie']
    search_fields = ['nom', 'categorie']
    ordering = ['nom']

    def status_stock(self, obj):
        if obj.est_en_rupture():
            return format_html(
                '<div style="background-color: #ffebee; padding: 5px; border-radius: 5px;">'
                '<span style="color: red; font-weight: bold;">⚠️ RUPTURE DE STOCK</span></div>'
            )
        elif obj.stock_faible():
            return format_html(
                '<div style="background-color: #fff3e0; padding: 5px; border-radius: 5px;">'
                '<span style="color: orange; font-weight: bold;">⚠️ Stock Faible ({} unités)</span></div>',
                obj.quantite_en_stock
            )
        return format_html(
            '<div style="background-color: #e8f5e9; padding: 5px; border-radius: 5px;">'
            '<span style="color: green;">✅ En stock ({} unités)</span></div>',
            obj.quantite_en_stock
        )
    status_stock.short_description = "État du stock"

class FactureAdmin(admin.ModelAdmin):
    list_display = ['id', 'commande', 'date_facture', 'get_montant_total', 'remise', 
                    'get_montant_final', 'methode_paiement', 'est_payee']
    readonly_fields = ['date_facture', 'montant_total', 'get_montant_final']
    fields = ['commande', 'remise', 'methode_paiement', 'montant_total', 
             'get_montant_final', 'date_facture', 'est_payee']
    list_filter = ['methode_paiement', 'est_payee']
    
    def get_montant_total(self, obj):
        return f"{obj.montant_total:.2f}€"
    get_montant_total.short_description = "Montant total"
    
    def get_montant_final(self, obj):
        return f"{obj.montant_final():.2f}€"
    get_montant_final.short_description = "Montant après remise"
    
    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            self.message_user(request, str(e), level='ERROR')

admin.site.register(Medicament, MedicamentAdmin)
admin.site.register(Client)
admin.site.register(Commande, CommandeAdmin)
admin.site.register(Facture, FactureAdmin)
