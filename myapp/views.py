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
from .models import Product, HomePage, HomeSlide, Commande ,CommandeItem
from .forms import CommandeForm
from reportlab.platypus import Table, TableStyle  # ✅ IMPORT manquant

# myapp/views.py
from django.core.mail import send_mail
# Pour WebSocket
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
# =================== HOME ===================
def home(request):
    # 🔹 Récupération du numéro de table depuis l'URL
    table_number = request.GET.get("table")
    if table_number:
        try:
            # On s'assure que c'est bien un entier
            table_number = int(table_number)
            request.session["table"] = table_number
        except ValueError:
            table_number = None  # Ignore si ce n'est pas un nombre

    # 🔹 Données pour la page d'accueil
    home_data = HomePage.objects.first()
    slides = HomeSlide.objects.all()
    query = request.GET.get('q')
    products = Product.objects.filter(quantity__gt=0)

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    # 🔹 Génération QR code pour la page d'accueil
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

    # 🔹 Rendu du template
    return render(request, 'home.html', {
        'home_data': home_data,
        'products': products,
        'slides': slides,
        'query': query,
        'qr_code': qr_code_base64,
        'table': request.session.get("table")  # récupère la table en session
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

    # Logo
    logo_path = os.path.join(settings.MEDIA_ROOT, 'logo.png')
    if os.path.exists(logo_path):
        p.drawImage(ImageReader(logo_path), 50, height - 60, width=80, height=30)

    # Titre
    p.setFont("Helvetica-Bold", 16)
    p.drawString(180, height - 50, f"Confirmation de Commande - #{commande.id}")
    p.line(50, height - 65, 550, height - 65)

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

    y -= 10
    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, y, "Produits commandés :")
    y -= 20

    # Construire le tableau
    table_data = [["Produit", "Quantité", "Prix Unitaire", "Sous-total"]]
    total = 0
    for item in commande.items.all():
        subtotal = item.quantity * item.price
        total += subtotal
        table_data.append([
            item.product.name,
            str(item.quantity),
            f"{item.price:,.0f} FCFA",
            f"{subtotal:,.0f} FCFA"
        ])

    # Créer le tableau avec ReportLab
    table = Table(table_data, colWidths=[200, 70, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
    ]))

    # Dessiner le tableau
    table.wrapOn(p, width, height)
    table_height = len(table_data) * 20
    table.drawOn(p, 50, y - table_height)

    y = y - table_height - 30

    # Total général
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, f"Total : {total:,.0f} FCFA")
    y -= 30
    p.setFont("Helvetica", 12)
    p.drawString(100, y, "Merci pour votre confiance 🚀")

    # Fin du PDF
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

# views.py
def checkout_view(request):
    # 🔹 Récupérer le numéro de table depuis la session
    table_number = request.session.get("table")
    table = None
    if table_number:
        try:
            table = Table.objects.get(number=table_number)
        except Table.DoesNotExist:
            table = None  # Ignore si la table n'existe pas

    # ===================== GET =====================
    if request.method == "GET":
        return render(request, "checkout.html", {"table": table})

    # ===================== POST =====================
    if request.method == "POST":
        # Récupérer le panier envoyé depuis le front (localStorage)
        cart_items_raw = request.POST.get("cart_items")
        try:
            cart_items = json.loads(cart_items_raw) if cart_items_raw else []
        except json.JSONDecodeError:
            messages.error(request, "Erreur : panier invalide.")
            return redirect("panier")

        if not cart_items:
            messages.error(request, "Votre panier est vide.")
            return redirect("panier")

        # Infos client
        customer_name = request.POST.get("customer_name")
        customer_email = request.POST.get("customer_email")
        customer_phone = request.POST.get("customer_phone")
        customer_address = request.POST.get("customer_address")

        if not customer_name or not customer_phone or not customer_address:
            messages.error(request, "Informations client manquantes.")
            return redirect("checkout")

        total_general = 0

        # ===================== Calcul total et mise à jour stock =====================
        for item in cart_items:
            product = get_object_or_404(Product, id=item["id"])
            quantity = int(item["qty"])

            if product.quantity < quantity:
                messages.error(request, f"Stock insuffisant pour {product.name}")
                return redirect("panier")

            total_general += product.price * quantity

            # Mise à jour stock
            product.quantity -= quantity
            product.save()

        # ===================== Création commande =====================
        commande = Commande.objects.create(
            table=table,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            customer_address=customer_address,
            total=total_general
        )

        # Ajouter les items à la commande
        for item in cart_items:
            product = get_object_or_404(Product, id=item["id"])
            CommandeItem.objects.create(
                commande=commande,
                product=product,
                quantity=int(item["qty"]),
                price=product.price
            )

        # ===================== Envoi email =====================
        try:
            # Propriétaire
            send_mail(
                subject=f"Nouvelle commande #{commande.id}",
                message=f"Une nouvelle commande a été passée par {customer_name}.\nTotal: {total_general} FCFA",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.OWNER_EMAIL],
            )

            # Livreur
            send_mail(
                subject=f"Nouvelle commande à livrer #{commande.id}",
                message=f"Commande #{commande.id} à livrer.\nAdresse client: {customer_address}\nTéléphone: {customer_phone}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DELIVERY_EMAIL],
            )
        except Exception as e:
            print("Erreur envoi mail:", e)

        # ===================== Notification WebSocket =====================
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "notifications",
                {
                    "type": "send_notification",
                    "message": f"Nouvelle commande #{commande.id} passée par {customer_name}"
                }
            )
        except Exception as e:
            print("Erreur notification WebSocket:", e)

        # ===================== Retour et vidage panier =====================
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

def kitchen(request):

    commandes = Commande.objects.filter(is_delivered=False).order_by("-created_at")

    return render(request, "kitchen.html", {
        "commandes": commandes
    })