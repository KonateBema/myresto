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

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     # path('admin/dashboard/', views.dashboard, name='admin_dashboard'),
#     path('admin/dashboard/', dashboard, name='admin_dashboard'),
#     # path('admin/', admin.site.urls),
#     path('', views.home, name='home'),
#     path('commande/<int:product_id>/', commande, name='commande'),
#     path('commande-confirmation/<int:commande_id>/', commande_confirmation, name='commande_confirmation'),
#     path('commande-confirmation-pdf/<int:commande_id>/', generate_pdf, name='generate_pdf'),

# ]
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

]
# permette de charger le fichier image dans django
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# *************************************************
# from django.shortcuts import render
# from .models import Product , HomePage

# creer la views
# def home(request):
#     products = Product.objects.all()
#     home_data = HomePage.objects.first() # recuperer les donners de homePage
#     return render(request, 'home.html',{'home_data': home_data ,'products':products})


