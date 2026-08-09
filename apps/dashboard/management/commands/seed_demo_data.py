from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import User, Role
from apps.settings_app.models import CompanyProfile
from apps.customers.models import Customer
from apps.suppliers.models import Supplier
from apps.seeds.models import CropType, SeedCategory, Brand, Seed, SeedBatch
from apps.finance.models import ChartOfAccount, JournalVoucher, JournalItem

class Command(BaseCommand):
    help = "Seeds initial demo data for the Seed ERP system."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Initializing ERP Demo Data..."))

        # 1. Ensure Roles
        admin_role = Role.objects.get(name=Role.ADMIN)

        # 2. Create Admin User
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
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write("Created Superuser: admin / admin123")

        # 3. Company Settings
        company = CompanyProfile.get_instance()
        company.name = "AgriSeed Enterprise ERP"
        company.tagline = "Premium Agriculture Seeds & Hybrid Quality"
        company.phone = "+92-42-35800000"
        company.email = "contact@agriseederp.com"
        company.save()

        # 4. Master Crops & Categories
        wheat, _ = CropType.objects.get_or_create(name='Wheat', defaults={'description': 'Grain crop varieties'})
        rice, _ = CropType.objects.get_or_create(name='Rice', defaults={'description': 'Aromatic & Coarse Rice varieties'})
        cotton, _ = CropType.objects.get_or_create(name='Cotton', defaults={'description': 'Bt Cotton hybrids'})
        maize, _ = CropType.objects.get_or_create(name='Maize', defaults={'description': 'Hybrid Corn & Maize'})

        certified, _ = SeedCategory.objects.get_or_create(name='Certified Seed')
        foundation, _ = SeedCategory.objects.get_or_create(name='Foundation Seed')

        brand_pioneer, _ = Brand.objects.get_or_create(name='Pioneer Seeds', defaults={'company_name': 'Pioneer Hi-Bred'})
        brand_guard, _ = Brand.objects.get_or_create(name='Guard Agricultural Research', defaults={'company_name': 'Guard Rice & Seeds'})

        # 5. Customers
        c1, _ = Customer.objects.get_or_create(
            name='Chaudhry Farming Store',
            defaults={'company_name': 'Chaudhry Agri Corp', 'phone': '0300-1112223', 'city': 'Multan', 'opening_balance': 50000.00, 'debit_limit': 500000.00}
        )
        c2, _ = Customer.objects.get_or_create(
            name='Al-Rehman Seed Agency',
            defaults={'company_name': 'Al-Rehman Traders', 'phone': '0321-4445556', 'city': 'Sahiwal', 'opening_balance': 0.00, 'debit_limit': 1000000.00}
        )

        # 6. Suppliers
        s1, _ = Supplier.objects.get_or_create(
            name='Punjab Seed Corporation',
            defaults={'company_name': 'PSC Govt Ltd', 'phone': '042-99200000', 'city': 'Lahore', 'opening_balance': 0.00}
        )

        # 7. Seed Catalog & Batches
        seed_wheat, _ = Seed.objects.get_or_create(
            code='SEED-0001',
            defaults={
                'name': 'Faisalabad-2008 Certified Wheat',
                'variety': 'FSD-08',
                'crop_type': wheat,
                'category': certified,
                'brand': brand_pioneer,
                'packing_size': '50 Kg Bag',
                'weight_kg': 50.00,
                'purchase_price': 4200.00,
                'retail_price': 4800.00,
                'wholesale_price': 4600.00,
                'min_stock_alert': 20,
                'barcode': 'SEED-0001'
            }
        )

        seed_rice, _ = Seed.objects.get_or_create(
            code='SEED-0002',
            defaults={
                'name': 'Super Kernel Basmati Rice Seed',
                'variety': 'Super Kernel',
                'crop_type': rice,
                'category': foundation,
                'brand': brand_guard,
                'packing_size': '20 Kg Bag',
                'weight_kg': 20.00,
                'purchase_price': 3500.00,
                'retail_price': 4200.00,
                'wholesale_price': 4000.00,
                'min_stock_alert': 15,
                'barcode': 'SEED-0002'
            }
        )

        today = timezone.now().date()
        SeedBatch.objects.get_or_create(
            batch_number='B-2026-W1',
            seed=seed_wheat,
            defaults={
                'lot_number': 'LOT-9988',
                'manufacturing_date': today - timedelta(days=60),
                'expiry_date': today + timedelta(days=300),
                'initial_qty': 500,
                'current_qty': 450,
                'purchase_price': 4200.00,
                'sale_price': 4800.00,
            }
        )

        SeedBatch.objects.get_or_create(
            batch_number='B-2026-R1',
            seed=seed_rice,
            defaults={
                'lot_number': 'LOT-4433',
                'manufacturing_date': today - timedelta(days=90),
                'expiry_date': today + timedelta(days=250),
                'initial_qty': 300,
                'current_qty': 280,
                'purchase_price': 3500.00,
                'sale_price': 4200.00,
            }
        )

        self.stdout.write(self.style.SUCCESS("Demo data successfully created! You can now log in with admin / admin123."))
