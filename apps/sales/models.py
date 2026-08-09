import io
import base64
import qrcode
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from apps.customers.models import Customer
from apps.seeds.models import Seed, SeedBatch

class SalesInvoice(models.Model):
    SALES_TYPE_CHOICES = [
        ('Retail', 'Retail Sale'),
        ('Wholesale', 'Wholesale'),
        ('POS', 'POS Terminal'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank', 'Bank Transfer'),
        ('Cheque', 'Cheque'),
        ('Online Transfer', 'Online Transfer'),
        ('JazzCash', 'JazzCash'),
        ('EasyPaisa', 'EasyPaisa'),
    ]

    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Partial', 'Partially Paid'),
        ('Unpaid', 'Unpaid'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales_invoices')
    date = models.DateField()
    due_date = models.DateField(blank=True, null=True)
    sales_type = models.CharField(max_length=20, choices=SALES_TYPE_CHOICES, default='Retail')
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unpaid')
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    qr_code = models.ImageField(upload_to='qrcodes/invoices/', blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_inv = SalesInvoice.objects.order_by('-id').first()
            last_id = last_inv.id if last_inv else 0
            self.invoice_number = f"INV-{(last_id + 1):04d}"

        # Coerce all monetary fields to Decimal to avoid float/Decimal clashes
        self.subtotal = Decimal(str(self.subtotal or 0))
        self.tax_amount = Decimal(str(self.tax_amount or 0))
        self.discount_amount = Decimal(str(self.discount_amount or 0))
        self.grand_total = Decimal(str(self.grand_total or 0))
        self.paid_amount = Decimal(str(self.paid_amount or 0))

        # Payment Status calculation
        if self.paid_amount >= self.grand_total and self.grand_total > Decimal('0'):
            self.payment_status = 'Paid'
        elif self.paid_amount > Decimal('0'):
            self.payment_status = 'Partial'
        else:
            self.payment_status = 'Unpaid'

        # Generate / Regenerate Pro-Level QR Code on every save
        self._regenerate_qr()

        super().save(*args, **kwargs)

    def get_qr_data_uri(self, request=None):
        """Returns inline base64 PNG data URI for the invoice QR code.
        Encodes the full verification URL so mobile phones can scan & verify."""
        from apps.settings_app.models import CompanyProfile

        company = CompanyProfile.get_instance()

        if request:
            base_url = f"{request.scheme}://{request.get_host()}"
        elif company.erp_base_url and '127.0.0.1' not in company.erp_base_url and 'localhost' not in company.erp_base_url:
            base_url = company.erp_base_url.rstrip('/')
        elif not settings.DEBUG:
            base_url = 'https://nowsheraseed.onrender.com'
        else:
            base_url = (company.erp_base_url or 'http://127.0.0.1:8000').rstrip('/')

        verify_url = f"{base_url}/sales/verify/{self.invoice_number}/"

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=3,
        )
        qr.add_data(verify_url)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="#0f172a", back_color="white")
        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        b64 = base64.b64encode(buffer.getvalue()).decode('ascii')
        return f"data:image/png;base64,{b64}"

    def _regenerate_qr(self):
        """Generate scannable QR code — encodes the invoice verification URL."""
        try:
            from apps.settings_app.models import CompanyProfile
            company = CompanyProfile.get_instance()

            if company.erp_base_url and '127.0.0.1' not in company.erp_base_url and 'localhost' not in company.erp_base_url:
                base_url = company.erp_base_url.rstrip('/')
            elif not settings.DEBUG:
                base_url = 'https://nowsheraseed.onrender.com'
            else:
                base_url = (company.erp_base_url or 'http://127.0.0.1:8000').rstrip('/')

            verify_url = f"{base_url}/sales/verify/{self.invoice_number}/"

            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=3,
            )
            qr.add_data(verify_url)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="#0f172a", back_color="white")
            buffer = io.BytesIO()
            qr_img.save(buffer, format='PNG')
            self.qr_code.save(
                f"qr_{self.invoice_number}.png",
                ContentFile(buffer.getvalue()),
                save=False
            )
        except Exception:
            pass

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name} (PKR {self.grand_total})"

    @property
    def due_amount(self):
        grand = Decimal(str(self.grand_total or 0))
        paid = Decimal(str(self.paid_amount or 0))
        return max(Decimal('0'), grand - paid)

    def get_gross_profit(self):
        cost_sum = sum(item.cost_price * item.quantity for item in self.items.all())
        return self.grand_total - cost_sum

class SalesItem(models.Model):
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='items')
    seed = models.ForeignKey(Seed, on_delete=models.CASCADE)
    batch = models.ForeignKey(SeedBatch, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        line_price = (self.unit_price - self.discount) * self.quantity
        self.subtotal = line_price * (1 + (self.tax_rate / 100))
        is_new = self.pk is None
        
        if not self.cost_price:
            self.cost_price = self.batch.purchase_price if self.batch else self.seed.purchase_price
            
        super().save(*args, **kwargs)
        
        if is_new:
            # Auto-deduct inventory stock
            if not self.batch:
                self.batch = SeedBatch.objects.filter(seed=self.seed, current_qty__gt=0).order_by('-id').first()
                if not self.batch:
                    self.batch = SeedBatch.objects.filter(seed=self.seed).order_by('-id').first()
                if self.batch:
                    SalesItem.objects.filter(pk=self.pk).update(batch=self.batch)

            if self.batch:
                self.batch.current_qty = max(0, self.batch.current_qty - self.quantity)
                self.batch.save()
            
            from apps.inventory.models import StockMovement
            StockMovement.objects.create(
                movement_type='STOCK_OUT',
                seed=self.seed,
                batch=self.batch,
                quantity=-self.quantity,
                reference_no=self.sales_invoice.invoice_number,
                notes=f"Sold to {self.sales_invoice.customer.name}",
                user=self.sales_invoice.created_by
            )

    def __str__(self):
        return f"{self.seed.name} x {self.quantity} @ {self.unit_price}"

class Quotation(models.Model):
    quotation_number = models.CharField(max_length=50, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    date = models.DateField()
    valid_until = models.DateField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, default='Draft', choices=[('Draft', 'Draft'), ('Sent', 'Sent'), ('Accepted', 'Accepted'), ('Converted', 'Converted')])
    notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.quotation_number:
            last_qt = Quotation.objects.order_by('-id').first()
            last_id = last_qt.id if last_qt else 0
            self.quotation_number = f"QT-{(last_id + 1):04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quotation_number} - {self.customer.name}"

class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    seed = models.ForeignKey(Seed, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
