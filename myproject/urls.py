# """
# URL configuration for myproject project.

# The `urlpatterns` list routes URLs to views. For more information please see:
#     https://docs.djangoproject.com/en/5.2/topics/http/urls/
# Examples:
# Function views
#     1. Add an import:  from my_app import views
#     2. Add a URL to urlpatterns:  path('', views.home, name='home')
# Class-based views
#     1. Add an import:  from other_app.views import Home
#     2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
# Including another URLconf
#     1. Import the include() function: from django.urls import include, path
#     2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
# """
# from myapp.views import home
# from django.contrib import admin
# from django.urls import path
# from django.conf import settings
# from django.conf.urls.static import static

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', home, name='home'),
# ]

# if settings.DEBUG: # permette de géré l'url des photos
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.contrib import admin
from django.urls import path
from myapp import views
from django.conf import settings
from django.conf.urls.static import static
from myapp.views import home , commande, commande_confirmation, generate_pdf
from myapp.admin import admin_site  # <- IMPORTANT, on importe l'admin personnalisé
from myapp.views import process_mobile_money, process_wave_payment

urlpatterns = [
    # Admin personnalisé
    # path('admin/', admin.site.urls),
    path('admin/', admin_site.urls),
    # Pages du site
    path('', views.home, name='home'),
    path('commande/<int:product_id>/', views.commande, name='commande'),
    path('commande-confirmation/<int:commande_id>/', views.commande_confirmation, name='commande_confirmation'),
    path('commande-confirmation-pdf/<int:commande_id>/', views.generate_pdf, name='generate_pdf'),
    path('produit/<int:id>/', views.product_detail, name='product_detail'),
    # path('produit/<int:id>/', views.product_detail, name='product_detail')
    path('panier/', views.panier_view, name='panier'),  # panier
    # path('checkout/', views.checkout, name='checkout'),
    path("checkout/", views.checkout_view, name="checkout"),
    # path('payment/notify/', views.payment_notify, name='payment_notify'),
    path('payment/<int:commande_id>/', views.payment_view, name='payment'),
    path("payment/notify/", views.payment_notify, name="payment_notify"),
    path("payment/success/<int:commande_id>/", views.payment_success_view, name="payment_success"),
    path('payment/process/<int:commande_id>/<str:method>/', views.process_payment, name='process_payment'),
    # path('payment/process/<int:commande_id>/mobile_money/', views.process_mobile_money, name='process_mobile_money'),
    path('payment/process_mobile_money/<int:commande_id>/', views.process_mobile_money, name='process_mobile_money'),
    # path("payment/success/", payment_success, name="payment_success"),
    path('payer/<int:commande_id>/', views.payment_view, name='payer_commande'),
    # path('payment/process_wave_payment/<int:commande_id>/', process_wave_payment, name='process_wave_payment'),
    path("payment/wave/<int:commande_id>/", views.wave_payment, name="wave_payment"),
    #  path('payer/<int:commande_id>/', views.payment_view, name='payer_commande'),  # Utilise payment_view
    path('category/<int:id>/', views.category_products, name='category_products'),
    path("payment/cash/<int:commande_id>/", views.cash_payment, name="cash_payment"),
    path('caisse/', views.caisse, name='caisse'),
    path('caisse/valider/<int:commande_id>/', views.valider_paiement, name='valider_paiement'),
    path('admin/valider-cash/<int:id>/', views.valider_cash),
]
# permette de charger le fichier image dans django
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# *************************************************


