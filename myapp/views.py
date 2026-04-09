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
# from reportlab.platypus import Table, TableStyle  # ✅ IMPORT manquant
from .models import Table
# myapp/views.py
from django.core.mail import send_mail
# Pour WebSocket
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from reportlab.platypus import  Paragraph, SimpleDocTemplate, Spacer,Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table as PDFTable, TableStyle
import requests
import uuid
from django.http import JsonResponse
# =================== HOME ===================

def home(request):
    # 🔹 Récupération du numéro de table depuis l'URL
    table_number = request.GET.get("table")
    if table_number:
        try:
            table_number = int(table_number)
            request.session["table"] = table_number
        except ValueError:
            table_number = None

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

    # 🔹 Récupération ou création d'une commande pour l'utilisateur (optionnel)
    commande = None

    # 🔹 Contexte à passer au template
    context = {
        "home_data": home_data,
        "slides": slides,
        "products": products,
        "query": query,
        "qr_code": qr_code_base64,
        "table": request.session.get("table"),
        "commande": commande,
    }

    # 🔹 Rendu du template
    return render(request, 'home.html', context)
    
def home1(request):
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

# récupère ou crée une commande pour l'utilisateur (exemple)
    commande = None
    context = {
        "products": Product.objects.all(),
        "slides": Slide.objects.all(),
        "home_data": HomeData.objects.first(),
        "commande": commande,  # <-- passe la commande au template
    }
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
from reportlab.lib.units import cm
from reportlab.platypus import Image
def generate_pdf(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)

    # Réponse HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="commande_{commande.id}.pdf"'

    # Création du document
    doc = SimpleDocTemplate(
        response,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    elements = []
    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]
    style_bold = styles["Heading4"]

    # Logo
    logo_path = os.path.join(settings.MEDIA_ROOT, 'logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=6*cm, height=3*cm)
        elements.append(logo)
        elements.append(Spacer(1, 12))

    # Titre
    elements.append(Paragraph(f"<b>Confirmation de Commande - #{commande.id}</b>", styles["Title"]))
    elements.append(Spacer(1, 20))

    # Infos client
    client_info = [
        ("Client", commande.customer_name),
        ("Email", commande.customer_email),
        ("Téléphone", commande.customer_phone),
        ("Adresse de livraison", commande.customer_address),
        ("Date", commande.created_at.strftime("%d/%m/%Y %H:%M")),
    ]
    for label, value in client_info:
        elements.append(Paragraph(f"<b>{label} :</b> {value}", style_normal))
        elements.append(Spacer(1, 5))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>Produits commandés :</b>", style_bold))
    elements.append(Spacer(1, 10))

    # Construire le tableau des produits
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

    # Style du tableau
    table = PDFTable(table_data, colWidths=[8*cm, 3*cm, 4*cm, 4*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey])
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Total général
    elements.append(Paragraph(f"<b>Total :</b> {total:,.0f} FCFA", style_bold))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Merci pour votre confiance 🚀", style_normal))

    # Générer le PDF
    doc.build(elements)

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

# views.py  ne depoiement 

# def checkout_view(request):
#     # ===================== GET =====================
#     if request.method == "GET":
#         return render(request, "checkout.html")

#     # ===================== POST =====================
#     if request.method == "POST":

#         # Récupérer le panier envoyé depuis le front (localStorage)
#         cart_items_raw = request.POST.get("cart_items")
#         try:
#             cart_items = json.loads(cart_items_raw) if cart_items_raw else []
#         except json.JSONDecodeError:
#             messages.error(request, "Erreur : panier invalide.")
#             return redirect("panier")

#         if not cart_items:
#             messages.error(request, "Votre panier est vide.")
#             return redirect("panier")

#         # Infos client
#         customer_name = request.POST.get("customer_name")
#         customer_email = request.POST.get("customer_email")
#         customer_phone = request.POST.get("customer_phone")
#         customer_address = request.POST.get("customer_address")

#         if not customer_name or not customer_phone or not customer_address:
#             messages.error(request, "Informations client manquantes.")
#             return redirect("checkout")

#         total_general = 0

#         # ===================== Calcul total et mise à jour stock =====================
#         for item in cart_items:
#             product = get_object_or_404(Product, id=item["id"])
#             quantity = int(item["qty"])

#             if product.quantity < quantity:
#                 messages.error(request, f"Stock insuffisant pour {product.name}")
#                 return redirect("panier")

#             total_item = float(product.price) * quantity
#             total_general += total_item

#             # Mise à jour stock
#             product.quantity -= quantity
#             product.save()

#         # ===================== Création commande =====================
#         commande = Commande.objects.create(
#             customer_name=customer_name,
#             customer_email=customer_email,
#             customer_phone=customer_phone,
#             customer_address=customer_address,
#             total=total_general
#         )

#         # Ajouter les items à la commande
#         for item in cart_items:
#             product = get_object_or_404(Product, id=item["id"])
#             CommandeItem.objects.create(
#                 commande=commande,
#                 product=product,
#                 quantity=int(item["qty"]),
#                 price=product.price
#             )

#         # ===================== Envoi email =====================
#         # Au propriétaire
#         send_mail(
#             subject=f"Nouvelle commande #{commande.id}",
#             message=f"Une nouvelle commande a été passée par {customer_name}.\nTotal: {total_general} FCFA",
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[settings.OWNER_EMAIL],
#         )

#         # Au livreur
#         send_mail(
#             subject=f"Nouvelle commande à livrer #{commande.id}",
#             message=f"Commande #{commande.id} à livrer.\nAdresse client: {customer_address}\nTéléphone: {customer_phone}",
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[settings.DELIVERY_EMAIL],
#         )

#         # ===================== Notification WebSocket =====================
#         try:
#             channel_layer = get_channel_layer()
#             async_to_sync(channel_layer.group_send)(
#                 "notifications",
#                 {
#                     "type": "send_notification",
#                     "message": f"Nouvelle commande #{commande.id} passée par {customer_name}"
#                 }
#             )
#         except Exception as e:
#             print("Erreur notification WebSocket:", e)

#         # ===================== Retour et vidage panier =====================
#         # Ici on n’utilise plus la session Django, car le panier vient de localStorage
#         messages.success(request, "Commande validée avec succès ✅")
#         return redirect("commande_confirmation", commande.id)



# def checkout_view(request):
#     # 🔹 Récupérer le numéro de table depuis la session
#     table_number = request.session.get("table")
#     table = None
#     if table_number:
#         try:
#             table = Table.objects.get(number=table_number)
#         except Table.DoesNotExist:
#             table = None  # Ignore si la table n'existe pas

#     # ===================== GET =====================
#     if request.method == "GET":
#         return render(request, "checkout.html", {"table": table})

#     # ===================== POST =====================
#     if request.method == "POST":

#         # Récupérer le panier envoyé depuis le front (localStorage)
#         cart_items_raw = request.POST.get("cart_items")

#         try:
#             cart_items = json.loads(cart_items_raw) if cart_items_raw else []
#         except json.JSONDecodeError:
#             messages.error(request, "Erreur : panier invalide.")
#             return redirect("panier")

#         if not cart_items:
#             messages.error(request, "Votre panier est vide.")
#             return redirect("panier")

#         # ===================== Infos client =====================
#         customer_name = request.POST.get("customer_name")
#         customer_email = request.POST.get("customer_email")
#         customer_phone = request.POST.get("customer_phone")
#         customer_address = request.POST.get("customer_address")

#         if not customer_name or not customer_phone or not customer_address:
#             messages.error(request, "Informations client manquantes.")
#             return redirect("checkout")

#         total_general = 0
#         details_produits = ""
#         produits_valides = []

#         # ===================== Vérification stock =====================
#         for item in cart_items:
#             product = get_object_or_404(Product, id=item["id"])
#             quantity = int(item["qty"])

#             if product.quantity < quantity:
#                 messages.error(request, f"Stock insuffisant pour {product.name}")
#                 return redirect("panier")

#             total_general += product.price * quantity

#             produits_valides.append({
#                 "product": product,
#                 "quantity": quantity
#             })

#             details_produits += f"{product.name} - Quantité: {quantity}\n"

#         # ===================== Création commande =====================
#         commande = Commande.objects.create(
#             table=table,
#             customer_name=customer_name,
#             customer_email=customer_email,
#             customer_phone=customer_phone,
#             customer_address=customer_address,
#             total=total_general
#         )

#         # ===================== Enregistrer produits + réduire stock =====================
#         for item in produits_valides:
#             product = item["product"]
#             quantity = item["quantity"]

#             CommandeItem.objects.create(
#                 commande=commande,
#                 product=product,
#                 quantity=quantity,
#                 price=product.price
#             )

#             # product.quantity -= quantity
#             # product.save()
#             if product.quantity >= quantity:
#                product.quantity -= quantity
#                product.save()
#             else:
#                messages.error(request, f"Stock insuffisant pour {product.name}")
#                return redirect("panier")
#         # ===================== Email propriétaire =====================
#         send_mail(
#             subject=f"Nouvelle commande #{commande.id}",
#             message=(
#                 f"Une nouvelle commande a été passée par {customer_name}\n"
#                 f"Téléphone: {customer_phone}\n"
#                 f"Adresse: {customer_address}\n\n"
#                 f"Produits commandés:\n{details_produits}\n"
#                 f"Total: {total_general} FCFA"
#             ),
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[settings.OWNER_EMAIL],
#         )

#         # ===================== Email livreur =====================
#         send_mail(
#             subject=f"Nouvelle commande à livrer #{commande.id}",
#             message=(
#                 f"Commande #{commande.id}\n"
#                 f"Client: {customer_name}\n"
#                 f"Téléphone: {customer_phone}\n"
#                 f"Adresse: {customer_address}\n\n"
#                 f"Produits:\n{details_produits}"
#             ),
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[settings.DELIVERY_EMAIL],
#         )

#         # ===================== Notification WebSocket =====================
#         try:
#             channel_layer = get_channel_layer()
#             async_to_sync(channel_layer.group_send)(
#                 "notifications",
#                 {
#                     "type": "send_notification",
#                     "message": f"Nouvelle commande #{commande.id} passée par {customer_name}"
#                 }
#             )
#         except Exception as e:
#             print("Erreur notification WebSocket:", e)

#         # ===================== Retour =====================
#         messages.success(request, "Commande validée avec succès ✅")
#         return redirect("commande_confirmation", commande.id)

# def checkout_view(request):

    # ================= TABLE =================
    table_number = request.session.get("table")
    table = None

    if table_number:
        try:
            table = Table.objects.get(number=table_number)
        except Table.DoesNotExist:
            table = None

    # ================= GET =================
    if request.method == "GET":
        return render(request, "checkout.html", {"table": table})

    # ================= POST =================
    cart_items_raw = request.POST.get("cart_items")

    try:
        cart_items = json.loads(cart_items_raw) if cart_items_raw else []
    except json.JSONDecodeError:
        messages.error(request, "Panier invalide.")
        return redirect("panier")

    if not cart_items:
        messages.error(request, "Votre panier est vide.")
        return redirect("panier")

    # ================= CLIENT =================
    customer_name = request.POST.get("customer_name")
    customer_email = request.POST.get("customer_email")
    customer_phone = request.POST.get("customer_phone")
    customer_address = request.POST.get("customer_address")
    commune = request.POST.get("commune")

    if not customer_name or not customer_phone or not customer_address or not commune:
        messages.error(request, "Informations manquantes.")
        return redirect("checkout")

    # ================= LIVRAISON =================
    delivery_fees = {
        "cocody": 1500,
        "yopougon": 2000,
        "abobo": 2500,
        "plateau": 1000,
        "marcory": 1200
    }

    delivery_fee = delivery_fees.get(commune, 0)

    total_general = 0
    details_produits = ""
    produits_valides = []

    # ================= STOCK =================
    for item in cart_items:
        product = get_object_or_404(Product, id=item["id"])
        quantity = int(item["qty"])

        if product.quantity < quantity:
            messages.error(request, f"Stock insuffisant pour {product.name}")
            return redirect("panier")

        total_general += product.price * quantity

        produits_valides.append({
            "product": product,
            "quantity": quantity
        })

        details_produits += f"{product.name} - Quantité: {quantity}\n"

    # ✅ Ajouter frais de livraison
    total_general += delivery_fee

    # ================= COMMANDE =================
    commande = Commande.objects.create(
        table=table,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        customer_address=customer_address,
        total=total_general
    )

    # ================= ITEMS + STOCK =================
    for item in produits_valides:
        product = item["product"]
        quantity = item["quantity"]

        CommandeItem.objects.create(
            commande=commande,
            product=product,
            quantity=quantity,
            price=product.price
        )

        # sécurité stock
        if product.quantity >= quantity:
            product.quantity -= quantity
            product.save()
        else:
            messages.error(request, f"Stock insuffisant pour {product.name}")
            return redirect("panier")

    # ================= EMAIL PROPRIÉTAIRE =================
    send_mail(
        subject=f"Nouvelle commande #{commande.id}",
        message=(
            f"Client: {customer_name}\n"
            f"Téléphone: {customer_phone}\n"
            f"Adresse: {customer_address}\n"
            f"Commune: {commune}\n\n"
            f"Produits:\n{details_produits}\n"
            f"Livraison: {delivery_fee} FCFA\n"
            f"Total: {total_general} FCFA"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.OWNER_EMAIL],
    )

    # ================= EMAIL LIVREUR =================
    send_mail(
        subject=f"Commande à livrer #{commande.id}",
        message=(
            f"Commande #{commande.id}\n"
            f"Client: {customer_name}\n"
            f"Téléphone: {customer_phone}\n"
            f"Commune: {commune}\n\n"
            f"Adresse: {customer_address}\n"
            f"Produits:\n{details_produits}"
            f"\nLivraison: {delivery_fee} FCFA"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.DELIVERY_EMAIL],
    )

    # ================= WEBSOCKET =================
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "notifications",
            {
                "type": "send_notification",
                "message": f"Nouvelle commande #{commande.id} - {customer_name}"
            }
        )
    except Exception as e:
        print("Erreur WebSocket:", e)

    # ================= SUCCESS =================
    messages.success(
        request,
        f"Commande validée ✅ (Livraison: {delivery_fee} FCFA)"
    )

    return redirect("commande_confirmation", commande.id)


import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def checkout_view(request):

    # ================= TABLE =================
    table_number = request.session.get("table")
    table = None

    if table_number:
        table = Table.objects.filter(number=table_number).first()

    # ================= GET =================
    if request.method == "GET":
        return render(request, "checkout.html", {"table": table})

    # ================= POST =================
    cart_items_raw = request.POST.get("cart_items")

    try:
        cart_items = json.loads(cart_items_raw) if cart_items_raw else []
    except json.JSONDecodeError:
        messages.error(request, "Panier invalide.")
        return redirect("panier")

    if not cart_items:
        messages.error(request, "Votre panier est vide.")
        return redirect("panier")

    # ================= CLIENT =================
    customer_name = request.POST.get("customer_name")
    customer_email = request.POST.get("customer_email")
    customer_phone = request.POST.get("customer_phone")
    customer_address = request.POST.get("customer_address")
    commune = request.POST.get("commune")

    if not all([customer_name, customer_phone, customer_address, commune]):
        messages.error(request, "Informations manquantes.")
        return redirect("checkout")

    # ================= LIVRAISON =================
    delivery_fees = {
        "cocody": 1500,
        "yopougon": 2000,
        "abobo": 2500,
        "plateau": 1000,
        "marcory": 1200
    }

    delivery_fee = delivery_fees.get(commune, 0)

    total_general = 0
    details_produits = ""
    produits_valides = []

    # ================= STOCK =================
    for item in cart_items:
        product = get_object_or_404(Product, id=item["id"])
        quantity = int(item["qty"])

        if product.quantity < quantity:
            messages.error(request, f"Stock insuffisant pour {product.name}")
            return redirect("panier")

        subtotal = product.price * quantity
        total_general += subtotal

        produits_valides.append({
            "product": product,
            "quantity": quantity
        })

        details_produits += f"{product.name} - Quantité: {quantity} - {subtotal} FCFA\n"

    # ✅ Ajouter livraison
    total_general += delivery_fee

    # ================= COMMANDE =================
    commande = Commande.objects.create(
        table=table,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        customer_address=customer_address,
        total=total_general,
        is_paid=False  # important pour paiement
    )

    # ================= ITEMS + STOCK =================
    for item in produits_valides:
        product = item["product"]
        quantity = item["quantity"]

        CommandeItem.objects.create(
            commande=commande,
            product=product,
            quantity=quantity,
            price=product.price
        )

        product.quantity -= quantity
        product.save()

    # ================= EMAIL PROPRIÉTAIRE =================
    # send_mail(
    #     subject=f"Nouvelle commande #{commande.id}",
    #     message=(
    #         f"Client: {customer_name}\n"
    #         f"Téléphone: {customer_phone}\n"
    #         f"Adresse: {customer_address}\n"
    #         f"Commune: {commune}\n\n"
    #         f"Produits:\n{details_produits}\n"
    #         f"Livraison: {delivery_fee} FCFA\n"
    #         f"Total: {total_general} FCFA"
    #     ),
    #     from_email=settings.DEFAULT_FROM_EMAIL,
    #     recipient_list=[settings.OWNER_EMAIL],
    # )

    # # ================= EMAIL LIVREUR =================
    # send_mail(
    #     subject=f"Commande à livrer #{commande.id}",
    #     message=(
    #         f"Commande #{commande.id}\n"
    #         f"Client: {customer_name}\n"
    #         f"Téléphone: {customer_phone}\n"
    #         f"Commune: {commune}\n\n"
    #         f"Adresse: {customer_address}\n"
    #         f"Produits:\n{details_produits}\n"
    #         f"Livraison: {delivery_fee} FCFA"
    #     ),
    #     from_email=settings.DEFAULT_FROM_EMAIL,
    #     recipient_list=[settings.DELIVERY_EMAIL],
    # )

    # ================= WEBSOCKET =================
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "notifications",
            {
                "type": "send_notification",
                "message": f"Nouvelle commande #{commande.id} - {customer_name}"
            }
        )
    except Exception as e:
        print("Erreur WebSocket:", e)

    # ================= SUCCESS =================
    messages.success(
        request,
        f"Commande enregistrée ✅ Choisissez votre mode de paiement"
    )

    # 🔥 REDIRECTION VERS PAIEMENT
    return redirect("payment", commande.id)

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

# def payer_commande(request, commande_id):
#     commande = get_object_or_404(Commande, id=commande_id)

#     transaction_id = str(uuid.uuid4())

#     url = "https://api-checkout.cinetpay.com/v2/payment"

#     data = {
#         "apikey": settings.CINETPAY_API_KEY,
#         "site_id": settings.CINETPAY_SITE_ID,
#         "transaction_id": transaction_id,
#         "amount": int(commande.total),
#         "currency": "XOF",
#         "description": f"Commande #{commande.id}",
#         "return_url": settings.CINETPAY_RETURN_URL,
#         "notify_url": settings.CINETPAY_NOTIFY_URL,
#         "customer_name": commande.customer_name,
#         "customer_surname": "",
#         "customer_email": commande.customer_email,
#         "customer_phone_number": commande.customer_phone,
#         "customer_address": commande.customer_address,
#         "customer_city": "Abidjan",
#         "customer_country": "CI"
#     }

#     response = requests.post(url, json=data)
#     response_data = response.json()

#     if response_data.get("code") == "201":
#         payment_url = response_data["data"]["payment_url"]
#         return redirect(payment_url)
#     else:
#         return redirect("commande_confirmation", commande.id)

import requests
import uuid


def payment(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")

        transaction_id = str(uuid.uuid4())

        data = {
            "apikey": settings.CINETPAY_API_KEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": transaction_id,
            "amount": int(commande.total),
            "currency": "XOF",
            "description": f"Commande #{commande.id}",
            "return_url": request.build_absolute_uri("/payment/success/"),
            "notify_url": request.build_absolute_uri("/payment/notify/"),
            "customer_name": commande.customer_name,
            "customer_phone_number": commande.customer_phone,
            "customer_email": commande.customer_email,
            "channels": "ALL"
        }

        response = requests.post(
            "https://api-checkout.cinetpay.com/v2/payment",
            json=data
        )

        res = response.json()

        if res.get("code") == "201":
            return redirect(res["data"]["payment_url"])
        else:
            messages.error(request, "Erreur paiement")
            return redirect("payment", commande.id)

    return render(request, "payment.html", {"commande": commande})

def payment_notify(request):
    transaction_id = request.POST.get("transaction_id")

    # ici tu peux vérifier le paiement avec l’API CinetPay

    return JsonResponse({"status": "ok"})

def payment_success(request):
    return render(request, "payment_success.html")


def payer_commande(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)

    if request.method == "POST":
        mode = request.POST.get("payment_method")

        commande.payment_method = mode
        commande.is_paid = (mode != "cash")
        commande.save()

        messages.success(request, "Paiement effectué avec succès ✅")
        return redirect("commande_confirmation", commande.id)

    return render(request, "payment.html", {"commande": commande})



def wave_payment(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)

    if request.method == "POST":
        proof = request.FILES.get("payment_proof")

        if not proof:
            messages.error(request, "Ajoute la preuve de paiement")
            return redirect("wave_payment", commande.id)

        # sauvegarde image
        fs = FileSystemStorage()
        filename = fs.save(proof.name, proof)

        commande.payment_proof = filename
        commande.payment_method = "wave"
        commande.payment_status = "pending"
        commande.save()

        messages.success(request, "Preuve envoyée ✅ En attente de validation")
        return redirect("commande_confirmation", commande.id)

    return render(request, "wave_payment.html", {
        "commande": commande,
        "wave_number": "0700000000"
    })