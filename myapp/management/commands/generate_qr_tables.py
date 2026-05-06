# myapp/management/commands/generate_qr_tables.py
import os
import qrcode
from django.core.management.base import BaseCommand
from django.conf import settings
from myapp.models import Table  # Ton modèle Table

class Command(BaseCommand):
    help = 'Générer des QR Codes pour toutes les tables'

    def handle(self, *args, **kwargs):
        # Crée le dossier QR si inexistant
        qr_folder = os.path.join(settings.MEDIA_ROOT, 'qr_tables')
        os.makedirs(qr_folder, exist_ok=True)

        # Récupère toutes les tables
        tables = Table.objects.all()
        if not tables:
            self.stdout.write(self.style.WARNING("Aucune table trouvée dans la base."))
            return

        # Génération des QR codes
        for table in tables:
            url = f"http://127.0.0.1:5400/?table={table.number}"  # URL vers ton site + table
            img = qrcode.make(url)
            qr_path = os.path.join(qr_folder, f'table_{table.number}.png')
            img.save(qr_path)
            self.stdout.write(self.style.SUCCESS(f'QR code généré pour Table {table.number}'))

        self.stdout.write(self.style.SUCCESS('Tous les QR codes ont été générés !'))