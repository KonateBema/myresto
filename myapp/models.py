from django.db import models
from ckeditor.fields import RichTextField
from PIL import Image


# ================= CATEGORY =================
class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Categorie"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    @property
    def products_count(self):
        return self.products.count()

    products_count.fget.short_description = "Nombre de produits"


# ================= SUPPLIER =================
class Supplier(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Fournisseur"

    def __str__(self):
        return self.name


# ================= PRODUCT =================
class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    quantity = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    categories = models.ManyToManyField(Category, related_name="products", blank=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    image = models.ImageField(upload_to="products/", blank=True, null=True)

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"

    def __str__(self):
        return self.name

    @property
    def categories_list(self):
        cats = self.categories.all()
        if cats.exists():
            return ", ".join(cat.name for cat in cats)
        return "Aucune catégorie"

    categories_list.fget.short_description = "Catégories"

    @property
    def stock_status(self):
        return "En stock" if self.quantity > 0 else "Rupture de stock"

    stock_status.fget.short_description = "Stock"

    @property
    def is_low_stock(self):
        return self.quantity <= 5


# ================= SUPPLIER DETAIL =================
class SupplierDetail(models.Model):
    supplier = models.OneToOneField(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="details"
    )
    address = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    supplier_type = models.CharField(
        max_length=50,
        choices=[
            ("distributeur", "Distributeur"),
            ("fabricant", "Fabricant"),
            ("revendeur", "Revendeur"),
        ],
        blank=True,
        null=True,
    )
    country = models.CharField(max_length=100, blank=True, null=True)
    payment_terms = models.CharField(max_length=100, blank=True, null=True)
    bank_account = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    region_served = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Détail Fournisseur"
        verbose_name_plural = "Détails Fournisseurs"

    def __str__(self):
        return f"Détails de {self.supplier}"

# ================= HOME PAGE =================
class HomePage(models.Model):
    site_name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="logos/")
    welcome_titre = models.CharField(max_length=255)
    welcome_message = RichTextField(default="Bienvenue sur notre site")

    action1_message = models.CharField(max_length=255)
    action1_lien = models.CharField(max_length=255)

    action2_message = models.CharField(max_length=255)
    action2_lien = models.CharField(max_length=255)

    contact_message = RichTextField(default="Contactez-nous")
    about_message = RichTextField(default="Bienvenue sur notre site")

    footer_message = RichTextField(default="© 2025 – Tous droits réservés")
    footer_bouton_message = models.CharField(max_length=255, default="En savoir plus")

    class Meta:
        verbose_name = "Page d'accueil"
        verbose_name_plural = "Pages d'accueil"

    def __str__(self):
        return "Page d'accueil"


# ================= COMMANDE =================
# class Commande(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField()
#     customer_name = models.CharField(max_length=255)
#     customer_email = models.EmailField()
#     customer_phone = models.CharField(max_length=20)
#     customer_address = models.TextField()
#     payment = models.CharField(
#         max_length=50,
#         choices=[
#             ("LIVRAISON", "Paiement à la livraison"),
#             ("ORANGE", "Orange Money"),
#             ("MTN", "MTN Mobile Money"),
#             ("WAVE", "Wave"),
#         ],
#     )
#     is_delivered = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         verbose_name = "Commande"
#         verbose_name_plural = "Commandes"

#     def __str__(self):
#         return f"Commande {self.id} - {self.customer_name}"

#     def save(self, *args, **kwargs):
#         if not self.pk:
#             if self.product.quantity >= self.quantity:
#                 self.product.quantity -= self.quantity
#                 self.product.save()
#             else:
#                 raise ValueError("Stock insuffisant")
#         super().save(*args, **kwargs)
# ++++++++++++++++++++++++++++++++++
# class Commande(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField()
#     customer_name = models.CharField(max_length=255)
#     customer_email = models.EmailField()
#     customer_phone = models.CharField(max_length=20)
#     customer_address = models.TextField()
#     payment = models.CharField(
#         max_length=50,
#         choices=[
#             ("LIVRAISON", "Paiement à la livraison"),
#             ("ORANGE", "Orange Money"),
#             ("MTN", "MTN Mobile Money"),
#             ("WAVE", "Wave"),
#         ],
#     )
#     is_delivered = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         verbose_name = "Commande"
#         verbose_name_plural = "Commandes"

#     def __str__(self):
#         return f"Commande {self.id} - {self.customer_name}"

#     @property
#     def status(self):
#         return "delivered" if self.is_delivered else "pending"

#     @property
#     def status_display(self):
#         return "Livrée" if self.is_delivered else "En attente"
# ================= COMMANDE =================
class Commande(models.Model):
    PAYMENT_CHOICES = [
        ("LIVRAISON", "Paiement à la livraison"),
        ("ORANGE", "Orange Money"),
        ("MTN", "MTN Mobile Money"),
        ("WAVE", "Wave"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    customer_address = models.TextField()

    payment = models.CharField(max_length=20, choices=PAYMENT_CHOICES)

    # total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_delivered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Commande #{self.id} - {self.customer_name}"

    @property
    def status(self):
        return "Livrée" if self.is_delivered else "En attente"

# ================= SLIDES =================
class HomeSlide(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    image = models.ImageField(upload_to="slides/", blank=True, null=True)
    action_text = models.CharField(max_length=100, blank=True, null=True)
    action_link = models.URLField(blank=True, null=True)


class Slide(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to="slides/", blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            img = Image.open(self.image.path)
            img.thumbnail((1200, 400))
            img.save(self.image.path, optimize=True, quality=85)
