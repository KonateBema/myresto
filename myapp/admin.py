from django.contrib import admin, messages
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.urls import path
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from .models import Product, Category, Supplier, SupplierDetail, HomePage, Commande
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from .models import Commande, CommandeItem  # Vérifie que c'est le dernier Commande
from .models import Slide ,HomeSlide
from django.utils.timezone import now
from django.db.models import Sum
from .models import CaisseProxy
from .models import HistoriqueCommandeProxy
from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required
from .views import export_caisse_jour_pdf
from myapp.views import audit_dashboard
from .models import CashAuditLog
# ==============================
#      PRODUCT ADMIN
# ==============================
@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = (
        'image_tag', 'name', 'price', 'supplier', 'quantity', 'formatted_created_at',
        'stock_status', 'categories_list', 'short_description'
    )
    search_fields = ('name', 'price')
    list_filter = ('created_at', 'price', 'quantity')
    ordering = ('-created_at',)
    fields = ('name', 'price', 'quantity', 'description', 'supplier', 'created_at', 'categories', 'image', 'image_tag')
    readonly_fields = ('created_at', 'image_tag')
    list_per_page = 10
    list_editable = ('quantity',)
    date_hierarchy = 'created_at'
    actions = ['set_price_to_zero', 'duplicate_product', 'apply_discount']
    filter_horizontal = ('categories',)
    autocomplete_fields = ('categories',)

    def formatted_created_at(self, obj):
        return obj.created_at.strftime('%d-%m-%Y %H:%M:%S')
    formatted_created_at.short_description = 'Ajouté le'

    def short_description(self, obj):
        if obj.description:
            return obj.description[:40] + '...' if len(obj.description) > 40 else obj.description
        return 'Aucune description'
    short_description.short_description = 'Description'

    def set_price_to_zero(self, request, queryset):
        updated = queryset.update(price=0)
        self.message_user(request, f"{updated} produit(s) mis à 0.", messages.SUCCESS)
    set_price_to_zero.short_description = 'Mettre le prix à 0'

    def duplicate_product(self, request, queryset):
        count = 0
        for product in queryset:
            product.pk = None
            product.save()
            count += 1
        self.message_user(request, f"{count} produit(s) dupliqué(s).", messages.SUCCESS)
    duplicate_product.short_description = 'Dupliquer les produits'

    def apply_discount(self, request, queryset):
        from decimal import Decimal
        discount_percentage = Decimal("0.9")
        count = 0
        for product in queryset:
            if product.price:
                product.price = Decimal(product.price) * discount_percentage
                product.save()
                count += 1
        self.message_user(request, f"Remise de 10%% appliquée sur {count} produit(s).", messages.SUCCESS)
    apply_discount.short_description = "Appliquer une remise de 10%%"

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" style="border-radius:5px;" />', obj.image.url)
        return "Pas d'image"
    image_tag.short_description = 'Aperçu'


# ==============================
#      CATEGORY ADMIN
# ==============================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'products_count')
    search_fields = ('name',)
    list_filter = ('name',)
    ordering = ('name',)
    fields = ('name',)
    list_per_page = 10

    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = 'Nombre de produits'


# ==============================
#      SUPPLIER ADMIN
# ==============================
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    fields = ('name', 'phone')
    list_display = ('name', 'phone')
    search_fields = ('name',)


@admin.register(SupplierDetail)
class SupplierDetailAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'address', 'contact_email', 'website', 'contact_person')
    search_fields = ('contact_person',)
    list_filter = ('supplier',)
    fields = ('supplier', 'address', 'contact_email', 'website', 'contact_person', 'supplier_type', 
              'country', 'payment_terms', 'bank_account', 'region_served')
    list_per_page = 10


# ==============================
#      HOMEPAGE ADMIN
# ==============================
@admin.register(HomePage)
class HomePageAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'logo_tag', 'formatted_welcome_message', 'action1_message', 'action1_lien', 
                    'action2_message', 'action2_lien', 'formatted_contact_message', 'formatted_about_message',
                    'formatted_footer_message', 'footer_bouton_message')
    fields = ('logo_tag', 'logo', 'site_name', 'welcome_titre', 'welcome_message',
              'action1_message', 'action1_lien', 'action2_message', 'action2_lien',
              'contact_message', 'about_message', 'footer_message', 'footer_bouton_message')
    readonly_fields = ('logo_tag',)

    def logo_tag(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="100px" style="border-radius:5px;" />', obj.logo.url)
        return "Pas d'image"
    logo_tag.short_description = 'Logo'

    def formatted_welcome_message(self, obj):
        return format_html(obj.welcome_message)
    formatted_welcome_message.short_description = 'Message de bienvenue'

    def formatted_contact_message(self, obj):
        return format_html(obj.contact_message)
    formatted_contact_message.short_description = 'Message de contact'

    def formatted_about_message(self, obj):
        return format_html(obj.about_message)
    formatted_about_message.short_description = 'Message à propos'

    def formatted_footer_message(self, obj):
        return format_html(obj.footer_message)
    formatted_footer_message.short_description = 'Message du pied de page'

    def has_add_permission(self, request):
        return not HomePage.objects.exists()

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'customer_name',
        'total',
        'payment_status_colored',
        'status_colored',
        "payment_method",
        "payment_status",
        'created_at',
    )

    list_filter = (
        'payment_status',
        "payment_method",
        'status',
        'created_at',
    )

    search_fields = (
        'customer_name',
        'customer_email',
        'customer_phone',
    )

    ordering = ('-created_at',)
    list_per_page = 10
    # ================= PAIEMENT =================
    def payment_status_colored(self, obj):
        colors = {
            "paid": "green",
            "pending": "orange",
            "failed": "red"
        }
        color = colors.get(obj.payment_status, "gray")
        return format_html(
            '<strong style="color:{};">{}</strong>',
            color,
            obj.get_payment_status_display()
        )
    payment_status_colored.short_description = "Paiement"

    # ================= STATUT COMMANDE =================
    def status_colored(self, obj):
        colors = {
            "pending": "orange",
            "processing": "blue",
            "delivered": "green"
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<strong style="color:{};">{}</strong>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = "Statut"

    # ================= ACTION ADMIN =================
    actions = ["mark_as_paid"]

    def mark_as_paid(self, request, queryset):
        queryset.update(payment_status="paid")
        mark_as_paid.short_description = "✅ Marquer comme payé"


    actions = ["mark_as_paid", "mark_cash_paid"]

    def mark_cash_paid(self, request, queryset):
      queryset.update(payment_status="paid", status="processing")

      mark_cash_paid.short_description = "💵 Valider paiement cash"


class CashAuditLogAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return redirect(reverse("admin:audit_dashboard"))     
# ==============================
#      ADMIN PERSONNALISÉ
# ==============================
class MyAdminSite(admin.AdminSite):
    site_header = "MvShop Dashboard"

    # ================= DASHBOARD =================
    def dashboard_view(self, request):
        last_commands = Commande.objects.order_by('-created_at')[:5]

        context = dict(
            self.each_context(request),
            commande=last_commands,
            products_count=Product.objects.count(),
            orders_pending=Commande.objects.filter(payment_status="pending").count(),
            orders_delivered=Commande.objects.filter(payment_status="paid").count(),
        )

        return TemplateResponse(request, "admin/dashboard.html", context)

    # ================= CAISSE =================
    def caisse_view(self, request):

        commandes = Commande.objects.filter(
            payment_method="cash",
            payment_status="pending"
        )

        historique = Commande.objects.filter(
            payment_method="cash",
            payment_status="paid"
        )

        total_jour = Commande.objects.filter(
            payment_method="cash",
            payment_status="paid"
        ).aggregate(total=Sum("total"))["total"] or 0

        context = dict(
            self.each_context(request),
            en_attente_cash=commandes,
            historique=historique,
            total_jour=total_jour,
            nb_commandes=historique.count(),
            en_attente=commandes.count(),
        )

        return TemplateResponse(request, "admin/caisse_dashboard.html", context)

    # ================= HISTORIQUE =================
    # ================= HISTORIQUE =================
    def historique_commandes_view(self, request):

        commandes = Commande.objects.all().order_by('-created_at')
        total = commandes.aggregate(total=Sum("total"))["total"] or 0

        context = dict(
            self.each_context(request),
            commandes=commandes,
            total=total,
            count=commandes.count(),
        )

        return TemplateResponse(request, "admin/historique_commandes.html", context)

     # 🔥 AJOUTE ÇA ICI
    def audit_dashboard_view(self, request):

        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        action = request.GET.get("action")

        logs = CashAuditLog.objects.all().order_by("-created_at")

        if start_date:
            logs = logs.filter(created_at__date__gte=start_date)

        if end_date:
            logs = logs.filter(created_at__date__lte=end_date)

        if action:
            logs = logs.filter(action=action)

        total = logs.aggregate(total=Sum("amount_after"))["total"] or 0

        context = dict(
            self.each_context(request),
            logs=logs,
            total=total,
        )

        return TemplateResponse(request, "admin/audit_dashboard.html", context)


    # ================= URLS =================
    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path('', self.admin_view(self.dashboard_view), name='dashboard'),
            path('caisse/', self.admin_view(self.caisse_view), name='caisse_dashboard'),
            path('caisse/pdf/', self.admin_view(export_caisse_jour_pdf), name='caisse_pdf'),
            path('historique-commandes/', self.admin_view(self.historique_commandes_view), name='historique_commandes'),
            path('historique-commandes/pdf/', self.admin_view(export_caisse_jour_pdf), name='historique_pdf'),
            # path('audit/', self.admin_view(self.audit_dashboard_view), name='audit_dashboard'),
            # path("admin/audit/", audit_dashboard, name="audit_dashboard"),
            path('audit/', self.admin_view(self.audit_dashboard_view), name='audit_dashboard'),
        ]
        return custom_urls + urls

class SlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'image')

@admin.register(HomeSlide)
class HomeSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "image")


class CaisseAdmindddd(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return self.admin_site.caisse_view(request)

class CaisseAdminAA(admin.ModelAdmin):

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff  # ou permission custom

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return self.admin_site.caisse_view(request)

class CaisseAdmin(admin.ModelAdmin):

    def has_view_permission(self, request, obj=None):
        return (
            request.user.is_staff or
            request.user.groups.filter(name="Caissier").exists()
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return self.admin_site.caisse_view(request)


class HistoriqueCommandeAdmin(admin.ModelAdmin):

    def changelist_view(self, request, extra_context=None):
        return redirect("/admin/historique-commandes/")



# from .models import CashAuditLog

# @admin.register(CashAuditLog)
# class CashAuditLogAdmin(admin.ModelAdmin):
#     list_display = (
#         "cashier",
#         "action",
#         "commande_id",
#         "amount_before",
#         "amount_after",
#         "created_at"
#     )

#     list_filter = ("action", "cashier", "created_at")

#     search_fields = ("cashier__username", "commande_id")

# admin_site.register(Slide, SlideAdmin)
# ==============================
#      INSTANTIATION DE L'ADMIN PERSONNALISÉ

# ==============================
admin_site = MyAdminSite(name='admin')  # remplace l'admin standard

# Enregistrer les modèles sur l'admin personnalisé
# Auth Django (OBLIGATOIRE)
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)
admin_site.register(Product, ProductAdmin)
admin_site.register(Category, CategoryAdmin)
admin_site.register(Supplier, SupplierAdmin)
admin_site.register(SupplierDetail, SupplierDetailAdmin)
admin_site.register(HomePage, HomePageAdmin)
admin_site.register(Commande, CommandeAdmin)
admin_site.register(Slide, SlideAdmin)
admin_site.register(HomeSlide, HomeSlideAdmin)  # <-- nouveau modèle ----->
admin_site.register(CaisseProxy, CaisseAdmin)
admin_site.register(HistoriqueCommandeProxy, HistoriqueCommandeAdmin)
# admin_site.register(CaisseLog, CaisseLogAdmin)
# admin_site.register(CashAuditLog, CashAuditLogAdmin)
