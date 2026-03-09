# views.py
import json
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
import qrcode
import base64
from io import BytesIO
from .models import Product, HomePage, HomeSlide, Commande 
from .forms import CommandeForm



# =================== HOME ===================


def home(request):
    home_data = HomePage.objects.first()
    slides = HomeSlide.objects.all()

    query = request.GET.get('q')

    products = Product.objects.filter(quantity__gt=0)
# Générer QR code pour accéder à la boutique (ou page spécifique)
    url = request.build_absolute_uri('/')  # lien vers la home
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=4,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
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
        "qr_code": qr_code_base64
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

# views.py
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

    # Infos client
    client_info = [
        ("Client", commande.customer_name),
        ("Email", commande.customer_email),
        ("Téléphone", commande.customer_phone),
        ("Adresse", commande.customer_address),
        ("Date", commande.created_at.strftime("%d/%m/%Y %H:%M")),
    ]
    for label, value in client_info:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y, f"{label} :")
        p.setFont("Helvetica", 12)
        p.drawString(250, y, str(value))
        y -= 20

    p.drawString(100, y - 10, "Produits commandés :")
    y -= 30

    # Produits
    total = 0
    for item in commande.items.all():
        subtotal = item.subtotal()
        total += subtotal
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y, f"{item.product.name} x {item.quantity}")
        p.setFont("Helvetica", 12)
        p.drawString(250, y, f"{subtotal} FCFA")
        y -= 20

    # Total général
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y - 20, f"Total : {total} FCFA")
    p.drawString(100, y - 50, "Merci pour votre confiance 🚀")

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


# @login_required
# def checkout(request):
#     """
#     Crée une commande à partir du panier envoyé depuis le frontend (JSON)
#     """
#     if request.method == "POST":
#         data = json.loads(request.body)
#         cart = data.get("cart", [])

#         if not cart:
#             return JsonResponse({"error": "Panier vide"}, status=400)

#         order = Order.objects.create(user=request.user)
#         total = 0
#         for item in cart:
#             product = Product.objects.get(id=item["id"])
#             quantity = int(item["qty"])
#             price = product.price
#             OrderItem.objects.create(order=order, product=product, quantity=quantity, price=price)
#             total += price * quantity
#             if product.quantity >= quantity:
#                 product.quantity -= quantity
#                 product.save()
#         order.total = total
#         order.save()
#         return JsonResponse({"message": "Commande passée avec succès!", "order_id": order.id})
#     return render(request, "checkout.html")




def checkout_view(request):

    # ===================== GET =====================
    if request.method == "GET":
        return render(request, "checkout.html")

    # ===================== POST =====================
    if request.method == "POST":

        cart_items_raw = request.POST.get("cart_items")

        try:
            cart_items = json.loads(cart_items_raw) if cart_items_raw else []
        except json.JSONDecodeError:
            messages.error(request, "Erreur panier invalide.")
            return redirect("panier")

        if not cart_items:
            messages.error(request, "Panier vide.")
            return redirect("panier")

        # Infos client
        customer_name = request.POST.get("customer_name")
        customer_email = request.POST.get("customer_email")
        customer_phone = request.POST.get("customer_phone")
        customer_address = request.POST.get("customer_address")

        if not customer_name or not customer_phone:
            messages.error(request, "Informations client manquantes.")
            return redirect("checkout")

        total_general = 0

        # calcul total
        for item in cart_items:

            product = get_object_or_404(Product, id=item["id"])
            quantity = int(item["qty"])

            if product.quantity < quantity:
                messages.error(request, f"Stock insuffisant pour {product.name}")
                return redirect("panier")

            total_item = float(product.price) * quantity
            total_general += total_item

            # mise à jour stock
            product.quantity -= quantity
            product.save()

        # création commande
        commande = Commande.objects.create(
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            customer_address=customer_address,
            total=total_general
        )
           # Vider le panier dans la session
        if 'panier' in request.session:
            del request.session['panier']

        messages.success(request, "Commande validée avec succès ✅")

        return redirect("commande_confirmation", commande.id)

def panier_ajouter(request, product_id):
    panier = request.session.get('panier', {})
    produit = get_object_or_404(Product, id=product_id)

    if str(product_id) in panier:
        panier[str(product_id)]['quantite'] += 1
    else:
        panier[str(product_id)] = {
            'nom': produit.name,
            'prix': float(produit.price),
            'quantite': 1,
            'image': produit.image.url if produit.image else ''
        }

    request.session['panier'] = panier
    return redirect('panier')

def panier_supprimer(request, product_id):
    panier = request.session.get('panier', {})
    panier.pop(str(product_id), None)
    request.session['panier'] = panier
    return redirect('panier')


def panier_detail(request):
    panier = request.session.get('panier', {})
    total = sum(item['prix'] * item['quantite'] for item in panier.values())

    return render(request, 'panier.html', {
        'panier': panier,
        'total': total
    })
