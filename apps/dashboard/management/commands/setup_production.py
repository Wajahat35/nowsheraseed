from django.core.management.base import BaseCommand
from django.core.management import call_command
from apps.accounts.models import User, Role
from apps.settings_app.models import CompanyProfile
import os

class Command(BaseCommand):
    help = "Sets up production database, erp_base_url, and ensures admin user exists"

    def handle(self, *args, **options):
        self.stdout.write("Checking database content...")
        
        # 1. Load data from data_backup.json if fixture exists
        fixture_path = 'data_backup.json'
        if os.path.exists(fixture_path):
            try:
                self.stdout.write("Loading data_backup.json...")
                call_command('loaddata', fixture_path)
                self.stdout.write(self.style.SUCCESS("Successfully imported data_backup.json"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"loaddata notice: {e}"))

        # 2. Ensure Role exists
        admin_role, _ = Role.objects.get_or_create(
            name=Role.ADMIN,
            defaults={'description': 'System Administrator'}
        )

        # 3. Ensure Admin User exists with active password
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@seederp.com',
                'first_name': 'Super',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
                'role': admin_role
            }
        )
        admin_user.set_password('admin123')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.is_active = True
        admin_user.role = admin_role
        admin_user.save()

        # 4. Set Company ERP base URL for QR codes to public production domain
        company = CompanyProfile.get_instance()
        company.erp_base_url = 'https://nowsheraseed.onrender.com'
        company.save()

        self.stdout.write(self.style.SUCCESS("[SUCCESS] Production admin user & QR Code Base URL configured: https://nowsheraseed.onrender.com"))
