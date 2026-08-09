from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.suppliers.models import Supplier
from apps.seeds.models import Seed, SeedBatch

class PurchaseInvoice(models.Model):
    PAYMENT_CHOICES = [
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
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_invoices')
    supplier_bill_no = models.CharField(max_length=100, blank=True, null=True, help_text="Supplier's original bill number")
    date = models.DateField()
    due_date = models.DateField(blank=True, null=True)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    payment_method = models.CharField(max_length=30, choices=PAYMENT_CHOICES, default='Cash')
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unpaid')
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_inv = PurchaseInvoice.objects.order_by('-id').first()
            last_id = last_inv.id if last_inv else 0
            self.invoice_number = f"PUR-{(last_id + 1):04d}"

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

        super().save(*args, **kwargs)

    @property
    def due_amount(self):
        grand = Decimal(str(self.grand_total or 0))
        paid = Decimal(str(self.paid_amount or 0))
        return max(Decimal('0'), grand - paid)

    def __str__(self):
        return f"{self.invoice_number} - {self.supplier.name} (PKR {self.grand_total})"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('purchases:purchase_detail', kwargs={'pk': self.pk})

class PurchaseItem(models.Model):
    purchase_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='items')
    seed = models.ForeignKey(Seed, on_delete=models.CASCADE)
    batch = models.ForeignKey(SeedBatch, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = (self.quantity * self.unit_price) * (1 + (self.tax_rate / 100))
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Auto-increase inventory stock
            if not self.batch:
                from django.utils import timezone
                from datetime import timedelta
                today = timezone.now().date()
                self.batch = SeedBatch.objects.filter(seed=self.seed).order_by('-id').first()
                if not self.batch:
                    self.batch = SeedBatch.objects.create(
                        seed=self.seed,
                        batch_number=f"PUR-BATCH-{self.purchase_invoice.invoice_number}",
                        lot_number=f"LOT-{self.purchase_invoice.invoice_number}",
                        manufacturing_date=today,
                        expiry_date=today + timedelta(days=365),
                        initial_qty=self.quantity,
                        current_qty=0,
                        purchase_price=self.unit_price or 0,
                        sale_price=self.seed.retail_price or 0
                    )
                PurchaseItem.objects.filter(pk=self.pk).update(batch=self.batch)

            self.batch.current_qty += self.quantity
            self.batch.save()
            
            from apps.inventory.models import StockMovement
            StockMovement.objects.create(
                movement_type='STOCK_IN',
                seed=self.seed,
                batch=self.batch,
                quantity=self.quantity,
                reference_no=self.purchase_invoice.invoice_number,
                notes=f"Purchased from {self.purchase_invoice.supplier.name}",
                user=self.purchase_invoice.created_by
            )

    def __str__(self):
        return f"{self.seed.name} x {self.quantity} @ {self.unit_price}"
