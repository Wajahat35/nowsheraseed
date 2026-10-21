import io
import base64
import qrcode
from decimal import Decimal
from django.db import models
from django.conf import settings

class WastageType(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name="Wastage Grade / Type")
    description = models.TextField(blank=True, null=True)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Current Rate per KG (PKR)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Wastage Type & Grade"
        verbose_name_plural = "Wastage Types & Grades"

    def __str__(self):
        return f"{self.name} (PKR {self.price_per_kg}/KG)"

    def get_or_create_stock(self):
        stock, _ = WastageStock.objects.get_or_create(wastage_type=self)
        return stock


class WastageRateHistory(models.Model):
    wastage_type = models.ForeignKey(WastageType, on_delete=models.CASCADE, related_name='rate_history')
    old_rate = models.DecimalField(max_digits=10, decimal_places=2)
    new_rate = models.DecimalField(max_digits=10, decimal_places=2)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True, null=True, help_text="Reason for rate revision")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Wastage Rate Audit Log"
        verbose_name_plural = "Wastage Rate Audit Logs"

    def __str__(self):
        return f"{self.wastage_type.name}: {self.old_rate} -> {self.new_rate} on {self.created_at.strftime('%Y-%m-%d')}"


class WastageStock(models.Model):
    wastage_type = models.OneToOneField(WastageType, on_delete=models.CASCADE, related_name='stock')
    current_stock_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Current Stock (KG)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Wastage Stock Balance"
        verbose_name_plural = "Wastage Stock Balances"

    def __str__(self):
        return f"{self.wastage_type.name}: {self.current_stock_kg} KG"

    def get_equivalent_bags(self, bag_weight=50):
        """Converts KG to equivalent bags and remaining loose weight"""
        bw = Decimal(str(bag_weight or 50))
        kg = Decimal(str(self.current_stock_kg or 0))
        bags = int(kg // bw) if bw > 0 else 0
        loose = kg % bw if bw > 0 else 0
        return bags, loose

    def display_dual(self, bag_weight=50):
        bags, loose = self.get_equivalent_bags(bag_weight)
        loose_str = f" + {loose:,.1f} KG loose" if loose > 0 else ""
        return f"{self.current_stock_kg:,.1f} KG (≈ {bags:,} Bags of {bag_weight} KG{loose_str})"


class WastageMovement(models.Model):
    MOVEMENT_CHOICES = [
        ('INTAKE_PROCESSING', 'Intake from Seed Processing'),
        ('SALES_DISPATCH', 'Sold / Dispatched to Buyer'),
        ('ADJUSTMENT', 'Stock Adjustment / Loss Write-Off'),
        ('RETURN', 'Sales Return / Inward Adjustment'),
    ]

    movement_type = models.CharField(max_length=30, choices=MOVEMENT_CHOICES)
    wastage_type = models.ForeignKey(WastageType, on_delete=models.CASCADE, related_name='movements')
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, help_text="Positive for addition, negative for deduction")
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Wastage Movement"
        verbose_name_plural = "Wastage Movements"

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.wastage_type.name}: {self.quantity_kg} KG"


class WastageInvoice(models.Model):
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Partial', 'Partially Paid'),
        ('Unpaid', 'Unpaid'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank', 'Bank Transfer'),
        ('Cheque', 'Cheque'),
        ('Online Transfer', 'Online Transfer'),
        ('JazzCash', 'JazzCash'),
        ('EasyPaisa', 'EasyPaisa'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    date = models.DateField()
    buyer_name = models.CharField(max_length=200, verbose_name="Buyer / Trader Name")
    buyer_phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Contact Phone")
    buyer_address = models.TextField(blank=True, null=True, verbose_name="Dispatch Address / City")

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)

    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unpaid')
    reference_no = models.CharField(max_length=100, blank=True, null=True, help_text="Vehicle / Bilty / Transaction Ref")
    remarks = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-id']
        verbose_name = "Wastage Invoice"
        verbose_name_plural = "Wastage Invoices"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last = WastageInvoice.objects.order_by('-id').first()
            last_id = last.id if last else 0
            self.invoice_number = f"WST-{(last_id + 1):04d}"

        self.subtotal = Decimal(str(self.subtotal or 0))
        self.discount_amount = Decimal(str(self.discount_amount or 0))
        self.tax_amount = Decimal(str(self.tax_amount or 0))
        self.grand_total = max(Decimal('0'), (self.subtotal + self.tax_amount) - self.discount_amount)
        self.paid_amount = Decimal(str(self.paid_amount or 0))

        if self.paid_amount >= self.grand_total and self.grand_total > Decimal('0'):
            self.payment_status = 'Paid'
        elif self.paid_amount > Decimal('0'):
            self.payment_status = 'Partial'
        else:
            self.payment_status = 'Unpaid'

        super().save(*args, **kwargs)

    @property
    def due_amount(self):
        return max(Decimal('0'), self.grand_total - self.paid_amount)

    @property
    def total_weight_kg(self):
        return sum((item.quantity_kg for item in self.items.all()), Decimal('0.00'))

    def __str__(self):
        return f"{self.invoice_number} - {self.buyer_name} (PKR {self.grand_total})"

    def get_qr_data_uri(self, request=None):
        base_url = 'https://nowsheraseed.onrender.com'
        if request:
            base_url = f"{request.scheme}://{request.get_host()}"
        verify_url = f"{base_url}/wastage/invoices/{self.pk}/"
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
        qr.add_data(verify_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#0f172a", back_color="white")
        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        b64 = base64.b64encode(buffer.getvalue()).decode('ascii')
        return f"data:image/png;base64,{b64}"


class WastageInvoiceItem(models.Model):
    invoice = models.ForeignKey(WastageInvoice, on_delete=models.CASCADE, related_name='items')
    wastage_type = models.ForeignKey(WastageType, on_delete=models.CASCADE)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Quantity (KG)")
    rate_per_kg = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Rate per KG (PKR)")
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Subtotal (PKR)")

    def save(self, *args, **kwargs):
        qty = Decimal(str(self.quantity_kg or 0))
        rate = Decimal(str(self.rate_per_kg or 0))
        self.subtotal = qty * rate
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            # Auto-deduct from WastageStock
            stock, _ = WastageStock.objects.get_or_create(wastage_type=self.wastage_type)
            stock.current_stock_kg = max(Decimal('0'), Decimal(str(stock.current_stock_kg)) - qty)
            stock.save()

            WastageMovement.objects.create(
                movement_type='SALES_DISPATCH',
                wastage_type=self.wastage_type,
                quantity_kg=-qty,
                reference_no=self.invoice.invoice_number,
                notes=f"Sold to {self.invoice.buyer_name} ({qty} KG @ PKR {rate}/KG)",
                user=self.invoice.created_by
            )

    def __str__(self):
        return f"{self.wastage_type.name} - {self.quantity_kg} KG @ PKR {self.rate_per_kg}"
