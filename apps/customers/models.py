from django.db import models

class Customer(models.Model):
    code = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=200)
    father_name = models.CharField(max_length=200, blank=True, null=True)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    cnic = models.CharField(max_length=20, blank=True, null=True, verbose_name="CNIC")
    ntn = models.CharField(max_length=50, blank=True, null=True, verbose_name="NTN")
    phone = models.CharField(max_length=30)
    whatsapp = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, default="Lahore")
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    debit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Credit/Debit Limit")
    credit_days = models.IntegerField(default=30)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.code:
            last_cust = Customer.objects.order_by('-id').first()
            last_id = last_cust.id if last_cust else 0
            self.code = f"CUST-{(last_id + 1):04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        comp = f" ({self.company_name})" if self.company_name else ""
        return f"{self.code} - {self.name}{comp}"

    def get_current_balance(self):
        # Calculated dynamically from invoices & receipts
        from apps.sales.models import SalesInvoice
        from apps.finance.models import JournalItem
        
        invoices_total = SalesInvoice.objects.filter(customer=self).aggregate(
            total=models.Sum('grand_total'),
            paid=models.Sum('paid_amount')
        )
        grand = invoices_total['total'] or 0
        paid = invoices_total['paid'] or 0
        balance = self.opening_balance + (grand - paid)
        return balance
