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
from .models import Table
from .models import Category
# myapp/views.py
import time
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
from django.views.decorators.csrf import csrf_exempt
# from cinetpay import CinetPay
from cinetpay import Client
from cinetpay import Config, Credential, Order
from datetime import date
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# from cinetpay.cinetpay import CinetPay
# =================== HOME ===================
import qrcode
import base64
from io import BytesIO
from django.db.models import Q
from django.shortcuts import render

def home(request):

    categories = Category.objects.all()
    # =========================
    # TABLE (URL + SESSION)
    # =========================
    table_number = request.GET.get("table")

    if table_number:
        try:
            table_number = int(table_number)
            request.session["table"] = table_number
        except (ValueError, TypeError):
            request.session.pop("table", None)
            table_number = None

    table_session = request.session.get("table")

    # =========================
    # HOME DATA
    # =========================
    home_data = HomePage.objects.first()

    # fallback sécurité
    if not home_data:
        home_data = None

    slides = HomeSlide.objects.all()

    # =========================
    # PRODUCTS
    # =========================
    query = request.GET.get("q")

    products = Product.objects.filter(quantity__gt=0)

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    # =========================
    # QR CODE (IMPORTANT FIX)
    # =========================
    # 👉 on encode la table dans l'URL si elle existe
    base_url = request.build_absolute_uri("/")

    if table_session:
        qr_url = f"{base_url}?table={table_session}"
    else:
        qr_url = base_url

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=4,
        border=2,
    )

    qr.add_data(qr_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

    # =========================
    # CONTEXT
    # =========================
    context = {
        "home_data": home_data,
        "slides": slides,
        "products": products,
        "query": query,
        "qr_code": qr_code_base64,
        "table": table_session,
        "categories": categories,
    }

    return render(request, "home.html", context)

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
        "marcory": 1200,
        "livraison":0
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


from django.db import transaction

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
        "marcory": 1200,
        "livraison":0
    }

    delivery_fee = delivery_fees.get(commune, 0)

    total_general = 0
    details_produits = ""
    produits_valides = []

    # ================= STOCK (PRÉ-VÉRIFICATION) =================
    for item in cart_items:
        product = get_object_or_404(Product, id=item["id"])
        quantity = int(item["qty"])

        if quantity <= 0:
            messages.error(request, "Quantité invalide.")
            return redirect("panier")

        if product.quantity < quantity:
            messages.error(request, f"Stock insuffisant pour {product.name}")
            return redirect("panier")

        subtotal = product.price * quantity
        total_general += subtotal

        produits_valides.append({
            "product_id": product.id,
            "quantity": quantity
        })

        details_produits += f"{product.name} - Quantité: {quantity} - {subtotal} FCFA\n"

    total_general += delivery_fee

    # ================= TRANSACTION 🔥 =================
    try:
        with transaction.atomic():

            # Création commande
            commande = Commande.objects.create(
                table=table,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                customer_address=customer_address,
                total=total_general,
                is_paid=False
            )

            # ================= ITEMS + STOCK =================
            for item in produits_valides:
                product = Product.objects.select_for_update().get(id=item["product_id"])
                quantity = item["quantity"]

                # 🔥 Vérification CRITIQUE (anti bug concurrent)
                if product.quantity < quantity:
                    raise Exception(f"Stock insuffisant pour {product.name}")

                CommandeItem.objects.create(
                    commande=commande,
                    product=product,
                    quantity=quantity,
                    price=product.price
                )

                product.quantity -= quantity
                product.save()

    except Exception as e:
        messages.error(request, str(e))
        return redirect("panier")

    # ================= EMAIL =================
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

    send_mail(
        subject=f"Commande à livrer #{commande.id}",
        message=(
            f"Commande #{commande.id}\n"
            f"Client: {customer_name}\n"
            f"Téléphone: {customer_phone}\n"
            f"Commune: {commune}\n\n"
            f"Adresse: {customer_address}\n"
            f"Produits:\n{details_produits}\n"
            f"Livraison: {delivery_fee} FCFA"
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
        "Commande enregistrée ✅ Choisissez votre mode de paiement"
    )

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


import uuid
from django.views.decorators.csrf import csrf_exempt
# FORMULAIRE DE PAIEMENT

def payment_view(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")
        if not payment_method:
            return redirect("payment", commande_id=commande.id)
            
        if payment_method == "cash":
            # Paiement à la livraison
            commande.is_paid = False
            commande.save()
            return render(request, "payment_success.html", {"commande": commande, "method": "Cash"})

        elif payment_method in ["mobile_money", "wave"]:
            # Sandbox CinetPay
            payload = {
                "site_id": "100123",            # Sandbox site_id
                # "password": "Konate@5346",
                "api_key": "sk_test_SeIIUz8iFS74xVJnsDefYAzU",  # Sandbox api_key
                "transaction_id": f"CMD-{commande.id}",
                "amount": commande.total,
                "currency": "CFA",
                "customer_email": commande.customer_email,
                "customer_phone": commande.customer_phone,
                "description": f"Paiement commande #{commande.id}",
                "notify_url": "http://127.0.0.1:8000/payment/notify/",
                "return_url": f"http://127.0.0.1:8000/payment/success/{commande.id}/",
            }

            url = "https://sandbox.cinetpay.com/v1/?method=checkPayment"
            response = requests.post(url, json=payload)
            data = response.json()
            print(data)  # Debug

            if data.get("code") == "201":
                return redirect(data["data"]["payment_url"])
            else:
                return render(request, "payment_error.html", {"error": data})

    # GET → Afficher formulaire
    return render(request, "payment.html", {"commande": commande})

# =========================
# NOTIFICATION CINETPAY 
# =========================
@csrf_exempt
def payment_notify(request):
    if request.method == "POST":
        transaction_id = request.POST.get("transaction_id")
        if not transaction_id:
            return HttpResponse("Transaction ID manquant", status=400)

        payload = {
          "apikey": settings.CINETPAY_API_KEY,
          "site_id": settings.CINETPAY_SITE_ID,
          "transaction_id": transaction_id
         }
        try:
            response = requests.post(
                "https://api-checkout.cinetpay.com/v2/payment",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            res = response.json()
        except Exception:
            return HttpResponse("Erreur CinetPay", status=500)

        if res.get("data", {}).get("status") == "ACCEPTED":
            commande_id = res["data"]["metadata"]
            commande = Commande.objects.filter(id=commande_id).first()
            if commande:
                commande.is_paid = True
                commande.save()
            return HttpResponse("OK")

    return HttpResponse("Méthode non autorisée", status=405)


# =========================
# SUCCÈS PAIEMENT
# =========================
def payment_success_view(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)
    method_param = request.GET.get('method', 'cash')
    method = "Cash" if method_param == "cash" else "Mobile Money / Wave"
    return render(request, "payment_success.html", {"commande": commande, "method": method})

def process_payment(request, commande_id, method):
    # Récupération de la commande
    commande = get_object_or_404(Commande, id=commande_id)

    # Ici tu implémentes la logique de paiement selon la méthode choisie
    # Par exemple, si "mobile_money" ou "card"
    if method == "mobile_money":
        # TODO: appeler l'API de paiement Mobile Money
        commande.is_paid = True  # ou False selon l'API
        commande.save()
        # Redirection vers confirmation
        return redirect('commande_confirmation', commande.id)

    elif method == "card":
        # TODO: intégrer Stripe ou autre
        commande.is_paid = True
        commande.save()
        return redirect('commande_confirmation', commande.id)

    else:
        # méthode inconnue
        messages.error(request, "Méthode de paiement invalide.")
        return redirect('checkout')


# ⚡ Clés CinetPay (test ou prod)
# CINETPAY_API_KEY = "TON_API_KEY"
# CINETPAY_SITE_ID = "TON_SITE_ID"
# CINETPAY_MODE = "TEST"  # TEST ou PROD


from cinetpay import Client, Config, Credential


# =========================
# Paiement Mobile Money
# =========================
@csrf_exempt
def process_mobile_money(request, commande_id):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)
        operator = data.get("operator")
        if not operator:
            return JsonResponse({"error": "Aucun opérateur sélectionné"}, status=400)

        # Récupération de la commande
        commande = get_object_or_404(Commande, id=commande_id)

        # 🔹 Config CinetPay
        CINETPAY_SITE_ID = "TON_SITE_ID"
        # CINETPAY_API_PASSWORD = "Konate@5346"  # très important
        CINETPAY_API_KEY = "sk_test_SeIIUz8iFS74xVJnsDefYAzU"
        CINETPAY_MODE = "TEST"  # "PROD" en production

        configs = Config(
            credentials=Credential(
                site_id=CINETPAY_SITE_ID,
                apikey=CINETPAY_API_KEY
            )),
        cp = Client(configs=configs)

        # 🔹 Création de la transaction Mobile Money
        order = cp.Order()  # objet Order pour créer le paiement

        response = order.create(
            amount=int(commande.total),
            trans_id=f"COM{commande.id}",
            description=f"Paiement commande #{commande.id}",
            customer_name=commande.customer_name,
            customer_email=commande.customer_email,
            customer_phone=commande.customer_phone,
            channel=operator.upper(),  # MTN / ORANGE / MOOV
            return_url=f"http://127.0.0.1:8000/payment/success/{commande.id}/"
        )

        if "payment_url" in response:
            return JsonResponse({"payment_url": response["payment_url"]})
        else:
            return JsonResponse({"error": response}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Données JSON invalides"}, status=400)
    except Exception as e:
        print("ERROR:", str(e))
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


# =========================
# Paiement Wave
# =========================

from cinetpay import Client, Config, Credential

# =========================
# Paiement Mobile Money
# =========================

import json

import traceback
# Paiement Wave
# =========================

@csrf_exempt
def process_mobile_money(request, commande_id):

 

    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)
        operator = data.get("operator")
        phone = data.get("phone")

        commande = get_object_or_404(Commande, id=commande_id)

        trans_id = f"CMD{commande.id}_{int(time.time())}"


  # 🔥 SAUVEGARDE AVANT ENVOI
        commande.payment_method = operator
        commande.transaction_id = trans_id
        commande.payment_status = "PENDING"
        commande.save()
        payload = {
            "apikey": "TON_API_KEY",
            "site_id": "TON_SITE_ID",
            "transaction_id": trans_id,
            "amount": int(commande.total),
            "currency": "XOF",
            "channels": operator.upper(),

            "description": f"Commande #{commande.id}",

            "customer_name": commande.customer_name,
            "customer_surname": commande.customer_name,
            "customer_phone_number": phone,
            "customer_email": commande.customer_email,

            "notify_url": "http://127.0.0.1:8000/payment/notify/",
            "return_url": f"http://127.0.0.1:8000/payment/success/{commande.id}/"
        }

        response = requests.post(
            "https://api-checkout.cinetpay.com/v2/payment",
            json=payload
        )

        result = response.json()
        print("CINETPAY:", result)

        if result.get("code") != "201":
            return JsonResponse({
                "error": "Erreur paiement",
                "details": result
            }, status=400)

        return JsonResponse({
            "trans_id": trans_id
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



@csrf_exempt
def process_wave_payment(request, commande_id):

    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    try:
        commande = get_object_or_404(Commande, id=commande_id)

        trans_id = f"WAVE{commande.id}_{int(time.time())}"
 # 🔥 SAUVEGARDE
        commande.payment_method = "WAVE"
        commande.transaction_id = trans_id
        commande.payment_status = "PENDING"
        commande.save()

        payload = {
            "apikey": "sk_test_SeIIUz8iFS74xVJnsDefYAzU",
            # "password": "Konate@5346",
             "site_id": "XXXX",  
            "transaction_id": trans_id,
            "amount": int(commande.total),
            "currency": "XOF",
            "channels": "WALLET",

            "description": f"Paiement Wave #{commande.id}",

            "customer_name": commande.customer_name,
            "customer_surname": commande.customer_name,
            "customer_phone_number": commande.customer_phone,
            "customer_email": commande.customer_email,

            "notify_url": "http://127.0.0.1:8000/payment/notify/",
            "return_url": f"http://127.0.0.1:8000/payment/success/{commande.id}/"
        }

        response = requests.post(
            "https://api-checkout.cinetpay.com/v2/payment",
            json=payload
        )

        result = response.json()
        print("WAVE RESULT:", result)

        if result.get("code") != "201":
            return JsonResponse({
                "error": "Erreur Wave",
                "details": result
            }, status=400)

        return JsonResponse({
            "status": "success",
            "payment_url": result["data"]["payment_url"]
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def check_payment_status(request, trans_id):
    try:
        payload = {
            "apikey": settings.CINETPAY_API_KEY,
            # "password": settings.CINETPAY_API_PASSWORD,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": trans_id
        }

        response = requests.post(
            "https://api-checkout.cinetpay.com/v2/payment/check",
            json=payload
        )

        result = response.json()
        print("CHECK PAYMENT:", result)

        # 🔹 Vérification du statut
        status = result.get("data", {}).get("status")

        return JsonResponse({
            "status": status,
            "full_response": result
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



from django.http import JsonResponse


def wave_payment(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)

    amount = commande.total

    url = f"https://pay.wave.com/m/M_ci_r3vEPsG6pQsB/c/ci/?amount={amount}"

    return JsonResponse({"url": url})


def category_products(request, id):

    categories = Category.objects.all()
    category = get_object_or_404(Category, id=id)

    products = Product.objects.filter(categories=category)

    # 🔥 SLIDER DYNAMIQUE
    # slides = Slide.objects.filter(
    #     Q(categories=category) | Q(categories__isnull=True),
    #     is_active=True
    # ).distinct()


    slides = HomeSlide.objects.filter(
    Q(categories=category) |
    Q(categories__isnull=True)
    ).distinct()

    table = request.session.get("table")

    # QR CODE
    url = request.build_absolute_uri('/')

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

    return render(request, "category_products.html", {
        "products": products,
        "categories": categories,
        "category": category,
        "slides": slides,
        "qr_code": qr_code_base64,
        "table": table
    })

def generate_qr(table_id):
    url = f"http://127.0.0.1:8000/?table={table_id}"

    qr = qrcode.make(url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")

    return base64.b64encode(buffer.getvalue()).decode()

def cash_payment(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)

    # ✅ Mettre à jour la commande
    commande.payment_method = "CASH"
    commande.payment_status = "PENDING"
    commande.save()

    return render(request, "cash_payment.html", {
        "commande": commande
    })


def cash_paymentzzz(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)

    # ✅ CORRECT
    commande.payment_method = "cash"
    commande.payment_status = "pending"

    # optionnel mais recommandé
    commande.status = "processing"

    commande.save()



    queryset.update(
        payment_status="paid",
        status="processing",
        cashier=request.user  # 🔥 important
        
    )

    return render(request, "cash_payment.html", {
        "commande": commande
    })


from .models import Commande, CashAuditLog, CashShift


def cash_paymentdddd(request, commande_id):

    commande = get_object_or_404(Commande, id=commande_id)

    # 🔥 sécurité
    if not request.user.is_staff:
        return HttpResponse("Accès refusé", status=403)

    # # 🔥 récupérer shift actif
    # shift = CashShift.objects.filter(
    #     cashier=request.user,
    #     is_active=True
    # ).first()

    # if not shift:
    #     return HttpResponse("Aucune caisse ouverte", status=400)

    # 💰 montant avant
    amount_before = commande.total

    # 🔥 mise à jour commande (UNE SEULE FOIS)
    commande.payment_method = "cash"
    commande.payment_status = "paid"
    commande.status = "processing"
    commande.cashier = request.user
    commande.cash_shift = shift
    commande.save()

    # 🧾 LOG paiement
    CashAuditLog.objects.create(
        cashier=request.user,
        action="PAYMENT",
        commande_id=commande.id,
        amount_before=amount_before,
        amount_after=commande.total,
        description=f"Encaissement commande #{commande.id}"
    )

    return render(request, "cash_payment.html", {
        "commande": commande
    })

from datetime import datetime

def caissedd(self, request):

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    commandes = Commande.objects.filter(
        payment_method="cash",
        payment_status="pending"
    )

    historique = Commande.objects.filter(
        payment_method="cash",
        payment_status="paid",
        cashier=user   # 🔥 IMPORTANT

    )

    # ================= FILTRE DATE =================
    if start_date:
        historique = historique.filter(created_at__date__gte=start_date)

    if end_date:
        historique = historique.filter(created_at__date__lte=end_date)

    total_jour = historique.aggregate(total=Sum("total"))["total"] or 0

    context = dict(
        self.each_context(request),
        en_attente_cash=commandes,
        historique=historique,
        total_jour=total_jour,
        nb_commandes=historique.count(),
        en_attente=commandes.count(),
        start_date=start_date,
        end_date=end_date,
    )

    return TemplateResponse(request, "admin/caisse_dashboard.html", context)

from django.db.models import Sum
from django.template.response import TemplateResponse

from django.db.models import Sum, Q

def caisse(self, request):

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # 🔥 commandes à valider (tolérant à la casse + null)
    commandes = Commande.objects.filter(
        Q(payment_method__iexact="cash"),
        Q(payment_status__iexact="pending")
    ).order_by("-created_at")

    # 🔥 historique
    historique = Commande.objects.filter(
        Q(payment_method__iexact="cash"),
        Q(payment_status__iexact="paid")
    ).order_by("-created_at")

    # ================= FILTRE DATE =================
    if start_date:
        historique = historique.filter(created_at__date__gte=start_date)

    if end_date:
        historique = historique.filter(created_at__date__lte=end_date)

    total_jour = historique.aggregate(total=Sum("total"))["total"] or 0

    context = dict(
        self.each_context(request),
        en_attente_cash=commandes,
        historique=historique,
        total_jour=total_jour,
        nb_commandes=historique.count(),
        en_attente=commandes.count(),
    )

    return TemplateResponse(request, "admin/caisse_dashboard.html", context)

def valider_cash(request, id):

    commande = get_object_or_404(Commande, id=id)

    commande.payment_status = "paid"
    commande.status = "processing"
    commande.save()

    return redirect("/admin/caisse/")

from .models import Commande, CashAuditLog, CashShift

def valider_casheee(request, id):

    commande = get_object_or_404(Commande, id=id)

    # 🔐 sécurité
    if not request.user.is_staff:
        return HttpResponse("Accès refusé", status=403)

    # 🚫 éviter double paiement
    if commande.payment_status == "paid":
        return HttpResponse("Commande déjà payée")

    # 🔥 récupérer shift actif
    shift = CashShift.objects.filter(
        cashier=request.user,
        is_active=True
    ).first()

    if not shift:
        return HttpResponse("Aucune caisse ouverte", status=400)

    # 💰 montant avant
    amount_before = commande.total

    # ✅ mise à jour
    commande.payment_status = "paid"
    commande.status = "processing"
    commande.payment_method = "cash"
    commande.cashier = request.user
    commande.cash_shift = shift
    commande.save()

    # 🧾 log audit
    CashAuditLog.objects.create(
        cashier=request.user,
        action="PAYMENT",
        commande_id=commande.id,
        amount_before=amount_before,
        amount_after=commande.total,
        description=f"Encaissement commande #{commande.id}"
    )

    return redirect("/admin/caisse/")

def valider_paiement(request, commande_id):

    commande = get_object_or_404(Commande, id=commande_id)
    # 🔥 Mise à jour paiement
    commande.payment_status = "paid"
    commande.status = "processing"  # ou delivered si tu veux direct
    commande.save()
    return redirect("/admin/caisse/")

def export_caisse_jour_pdf(request):

    today = date.today()

    commandes = Commande.objects.filter(
        payment_method="cash",
        payment_status="paid",
        created_at__date=today
    )

    total_jour = sum(c.total for c in commandes)

    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()
    elements = []

    # ================= TITLE =================
    title = Paragraph("🧾 Encaissements du jour", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 20))

    # ================= TABLE DATA =================
    data = [["ID", "Client", "Montant", "Date"]]

    for c in commandes:
        data.append([
            c.id,
            c.customer_name,
            f"{c.total} FCFA",
            c.created_at.strftime("%H:%M")
        ])

    # ================= TABLE =================
    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # ================= TOTAL =================
    total = Paragraph(
        f"<b>Total encaissé du jour :</b> {total_jour} FCFA",
        styles["Heading2"]
    )

    elements.append(total)

    pdf.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type="application/pdf")

from django.utils.timezone import now
from django.db.models import Sum

def historique_commandes_view(self, request):

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    status = request.GET.get("status")

    commandes = Commande.objects.all().order_by('-created_at')

    # 🔎 FILTRES
    if start_date:
        commandes = commandes.filter(created_at__date__gte=start_date)

    if end_date:
        commandes = commandes.filter(created_at__date__lte=end_date)

    if status:
        commandes = commandes.filter(payment_status=status)

    # 📊 STATS
    total = commandes.aggregate(total=Sum("total"))["total"] or 0

    context = dict(
        self.each_context(request),
        commandes=commandes[:100],  # limite pour performance
        total=total,
    )

    return TemplateResponse(request, "historique_commandes.html", context)

from django.shortcuts import render
from .models import CashAuditLog

def audit_dashboard(request):

    logs = CashAuditLog.objects.all().order_by("-created_at")

    # filtres optionnels
    cashier = request.GET.get("cashier")
    action = request.GET.get("action")

    if cashier:
        logs = logs.filter(cashier__username__icontains=cashier)

    if action:
        logs = logs.filter(action=action)

    return render(request, "admin/cash_audit.html", {
        "logs": logs
    })


from .models import CashAuditLog


def update_commande(request, commande_id):

    commande = Commande.objects.get(id=commande_id)

    ancien_montant = commande.total

    # traitement modification
    nouveau_montant = 15000
    commande.total = nouveau_montant
    commande.save()

    # enregistrer audit
    CashAuditLog.objects.create(
        cashier=request.user,
        action="MODIFICATION",
        commande_id=commande.id,
        amount_before=ancien_montant,
        amount_after=nouveau_montant
    )

    return redirect("commande_list")


