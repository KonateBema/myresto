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


# ==============================
#      COMMANDE ADMIN
# ==============================
@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = (
        'product', 'quantity', 'total_commande', 'customer_name', 'status_colored',
        'customer_email', 'customer_phone', 'created_at', 'payment', 'is_delivered'
    )
    list_editable = ('is_delivered',)
    search_fields = ('customer_name', 'customer_email', 'customer_phone', 'customer_address')
    list_filter = ('payment', 'is_delivered')
    fields = ('product', 'quantity', 'customer_name', 'customer_email', 'customer_phone',
              'customer_address', 'payment', 'is_delivered')
    list_per_page = 5

    def total_commande(self, obj):
        if obj.product and obj.product.price:
            return obj.quantity * obj.product.price
        return 0
    total_commande.short_description = 'Total (€)'

    def status_colored(self, obj):
        color = 'green' if obj.is_delivered else 'red'
        text = 'Livrée' if obj.is_delivered else 'En attente'
        return format_html('<strong style="color:{};">{}</strong>', color, text)
    status_colored.short_description = 'Statut'


# ==============================
#      ADMIN PERSONNALISÉ
# ==============================
class MyAdminSite(admin.AdminSite):
    site_header = "MvShop Dashboard"

    def get_urls(self):
        urls = super().get_urls()
        # Dashboard à la racine de l'admin
        custom_urls = [
            path('', self.admin_view(self.dashboard_view), name='dashboard'),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        last_commands = (
            Commande.objects
            .select_related('product')
            .order_by('-created_at')[:5]
        )
        monthly_orders = (
            Commande.objects
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )

        context = dict(
            self.each_context(request),
             commande=last_commands,  # 🔥 OBLIGATOIRE
            products_count=Product.objects.count(),
            orders_pending=Commande.objects.filter(is_delivered=False).count(),
            orders_delivered=Commande.objects.filter(is_delivered=True).count(),
            monthly_orders=monthly_orders,
        )
        return TemplateResponse(request, "admin/dashboard.html", context)


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
