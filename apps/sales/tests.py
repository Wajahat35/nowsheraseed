from django.test import TestCase
from django.utils import timezone
from apps.customers.models import Customer
from apps.seeds.models import Seed, SeedBatch, CropType
from apps.sales.models import SalesInvoice, SalesItem
from apps.finance.models import ChartOfAccount, AccountCategory, JournalVoucher, JournalItem

class SalesInvoiceTestCase(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            name="Test Farmer Store",
            phone="0300-1112223",
            city="Multan"
        )
        self.crop = CropType.objects.create(name="Wheat")
        self.seed = Seed.objects.create(
            name="FSD-2008 Wheat",
            variety="FSD-08",
            crop_type=self.crop,
            retail_price=4500.00,
            purchase_price=4000.00
        )
        self.batch = SeedBatch.objects.create(
            batch_number="B-101",
            lot_number="L-101",
            seed=self.seed,
            manufacturing_date=timezone.now().date(),
            expiry_date=timezone.now().date() + timezone.timedelta(days=180),
            initial_qty=100,
            current_qty=100,
            purchase_price=4000.00,
            sale_price=4500.00
        )

    def test_sales_invoice_creation_and_stock_deduction(self):
        invoice = SalesInvoice.objects.create(
            customer=self.customer,
            date=timezone.now().date(),
            sales_type='Retail',
            subtotal=4500.00,
            grand_total=4500.00,
            paid_amount=4500.00,
            payment_status='Paid'
        )
        
        SalesItem.objects.create(
            sales_invoice=invoice,
            seed=self.seed,
            batch=self.batch,
            quantity=10,
            unit_price=4500.00,
            subtotal=45000.00
        )

        self.batch.refresh_from_db()
        # Initial stock was 100, sold 10 -> current_qty should be 90
        self.assertEqual(self.batch.current_qty, 90)
        self.assertEqual(invoice.customer.name, "Test Farmer Store")

class FinanceDoubleEntryTestCase(TestCase):
    def setUp(self):
        self.asset_cat, _ = AccountCategory.objects.get_or_create(name='ASSET')
        self.cash_acc, _ = ChartOfAccount.objects.get_or_create(code='1000', defaults={'name': 'Cash in Hand', 'category': self.asset_cat})
        self.rev_cat, _ = AccountCategory.objects.get_or_create(name='REVENUE')
        self.sales_acc, _ = ChartOfAccount.objects.get_or_create(code='4000', defaults={'name': 'Sales Revenue', 'category': self.rev_cat})

    def test_double_entry_balance(self):
        voucher = JournalVoucher.objects.create(
            voucher_type='CRV',
            date=timezone.now().date(),
            total_debit=5000.00,
            total_credit=5000.00
        )
        JournalItem.objects.create(voucher=voucher, account=self.cash_acc, debit=5000.00, credit=0.00)
        JournalItem.objects.create(voucher=voucher, account=self.sales_acc, debit=0.00, credit=5000.00)

        self.assertEqual(self.cash_acc.get_balance(), 5000.00)
        self.assertEqual(self.sales_acc.get_balance(), 5000.00)
