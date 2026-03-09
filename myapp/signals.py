# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CommandeItem  # modèle pour chaque produit commandé

@receiver(post_save, sender=CommandeItem)
def update_product_quantity(sender, instance, created, **kwargs):
    """
    Décrémente la quantité du produit après validation d'une ligne de commande.
    """
    if created:
        product = instance.product
        if product.quantity >= instance.quantity:
            product.quantity -= instance.quantity
            product.save()
        else:
            print(f"Stock insuffisant pour {product.name}. Quantité disponible : {product.quantity}")