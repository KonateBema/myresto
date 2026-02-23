# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.admin.models import LogEntry
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth

import os

from .models import Product, HomePage, HomeSlide, Commande 
from .forms import CommandeForm



# =================== HOME ===================


def home(request):
    home_data = HomePage.objects.first()
    slides = HomeSlide.objects.all()

    query = request.GET.get('q')

    products = Product.objects.filter(quantity__gt=0)

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    return render(request, 'home.html', {
        'home_data': home_data,
        'products': products,
        'slides': slides,
        'query': query,
    })

# =================== COMMANDE ===================
def commande(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        form = CommandeForm(request.POST)
        quantity = int(request.POST.get('quantity', 1))

        if form.is_valid():
            cmd = form.save(commit=False)
            cmd.product = product
            cmd.quantity = quantity
            cmd.total_amount = product.price * quantity
            cmd.save()

            messages.success(request, "Commande enregistrée avec succès !")
            return redirect('commande_confirmation', cmd.id)
    else:
        form = CommandeForm()

    return render(request, 'commande.html', {
        'product': product,
        'form': form
    })


def commande_confirmation(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)
    return render(request, 'commande_confirmation.html', {'commande': commande})


# =================== GENERATION PDF ===================
def generate_pdf(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="commande_{commande.id}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    logo_path = os.path.join(settings.MEDIA_ROOT, 'logo.png')
    if os.path.exists(logo_path):
        p.drawImage(ImageReader(logo_path), 50, height - 47, width=80, height=25)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(180, height - 50, f"Confirmation de Commande - #{commande.id}")

    p.line(50, height - 60, 550, height - 60)

    y = height - 100
    details = [
        ("Client", commande.customer_name),
        ("Produit", commande.product.name),
        ("Quantité", str(commande.quantity)),
        ("Adresse", commande.customer_address),
        ("Paiement", commande.payment),
        ("Date", commande.created_at.strftime("%d/%m/%Y %H:%M")),
        ("Total", f"{commande.total_amount} €"),
    ]

    for label, value in details:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y, f"{label} :")
        p.setFont("Helvetica", 12)
        p.drawString(250, y, value)
        y -= 25

    p.drawString(100, y - 30, "Merci pour votre confiance 🚀")
    p.showPage()
    p.save()

    return response

def dashboard_view(self, request):
    # 5 dernières commandes
    if request.user.has_perm('myapp.view_commande'):
        commandes = Commande.objects.order_by('-created_at')[:5]
    else:
        commandes = []
       
    # Stats mensuelles
    monthly_orders = (
        Commande.objects
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            total=Count("id"),
            delivered_count=Count("id", filter=Q(is_delivered=True)),
            pending_count=Count("id", filter=Q(is_delivered=False)),
        )
        .order_by("month")
    )
# Statistiques globales
    orders_pending_count = Commande.objects.filter(is_delivered=False).count()
    orders_delivered_count = Commande.objects.filter(is_delivered=True).count()
    context = dict(
        self.each_context(request),
        products_count=Product.objects.count(),
        orders_pending=Commande.objects.filter(is_delivered=False).count(),
        orders_delivered=Commande.objects.filter(is_delivered=True).count(),
        commande=last_commands,
        monthly_orders=monthly_orders,
    )

    return TemplateResponse(request, "admin/dashboard.html", context)


def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
  
    # 🔁 Produits similaires (même catégorie)
    similar_products = Product.objects.filter(
       
    ).exclude(id=product.id)[:4]

    return render(request, 'product_detail.html', {
        'product': product,
       
        'similar_products': similar_products,
    })

def panier_view(request):
    """
    Affiche le panier (commande) de l'utilisateur.
    Les produits sont récupérés depuis le localStorage côté front via JS
    ou depuis la session côté backend.
    """
    # Si tu veux gérer côté serveur, tu peux utiliser session
    cart = request.session.get('cart', [])  # par défaut vide
    total = sum(item['price'] * item['qty'] for item in cart)
    
    context = {
        'cart': cart,
        'total': total
    }
    return render(request, 'panier.html', context)


@login_required
def checkout(request):
    """
    Crée une commande à partir du panier envoyé depuis le frontend (JSON)
    """
    if request.method == "POST":
        data = json.loads(request.body)
        cart = data.get("cart", [])

        if not cart:
            return JsonResponse({"error": "Panier vide"}, status=400)

        order = Order.objects.create(user=request.user)
        total = 0

        for item in cart:
            product = Product.objects.get(id=item["id"])
            quantity = int(item["qty"])
            price = product.price
            OrderItem.objects.create(order=order, product=product, quantity=quantity, price=price)
            total += price * quantity

            # Décrémenter le stock
            if product.quantity >= quantity:
                product.quantity -= quantity
                product.save()

        order.total = total
        order.save()

        return JsonResponse({"message": "Commande passée avec succès!", "order_id": order.id})

    # GET request
    return render(request, "checkout.html")