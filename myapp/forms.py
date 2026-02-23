from django import forms
from .models import Commande
 
class CommandeForm(forms.ModelForm):
    class Meta:
        model = Commande
        fields = [
            'quantity', 'payment', 'customer_name', 
            'customer_email', 'customer_phone', 'customer_address',
        ]
        
        labels = {
            'quantity': 'Quantité',
            'payment': 'Mode de paiement',
            'customer_name': 'Nom complet',
            'customer_email': 'Email',
            'customer_phone': 'Téléphone',
            'customer_address': 'Adresse',
        }
        
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Quantité'
            }),
            'payment': forms.Select(attrs={
                'class': 'form- '
            }),
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nom complet'
            }),
            'customer_email': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Email'
            }),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Téléphone'
            }),
            'customer_address': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Adresse'
            }),
        }
PAYMENT_CHOICES = [
    ('ORANGE', 'Orange Money'),
    ('MTN', 'MTN MoMo'),
    ('WAVE', 'Wave'),
]

payment = forms.ChoiceField(
    choices=PAYMENT_CHOICES,
    widget=forms.Select(attrs={'class': 'form-select'})
)


# class OrderForm(forms.ModelForm):
#     class Meta:
#         model = Order
#         fields = [
#             'customer_name',
#             'customer_phone',
#             'customer_email',
#             'customer_address',
#             'payment',
#         ]
