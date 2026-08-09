from django.db import models

class Supplier(models.Model):
    code = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    cnic = models.CharField(max_length=20, blank=True, null=True, verbose_name="CNIC")
    ntn = models.CharField(max_length=50, blank=True, null=True, verbose_name="NTN")
    phone = models.CharField(max_length=30)
    whatsapp = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, default="Lahore")
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    bank_details = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.code:
            last_supp = Supplier.objects.order_by('-id').first()
            last_id = last_supp.id if last_supp else 0
            self.code = f"SUPP-{(last_id + 1):04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        comp = f" ({self.company_name})" if self.company_name else ""
        return f"{self.code} - {self.name}{comp}"

    def get_current_balance(self):
        from apps.purchases.models import PurchaseInvoice
        bills_total = PurchaseInvoice.objects.filter(supplier=self).aggregate(
            total=models.Sum('grand_total'),
            paid=models.Sum('paid_amount')
        )
        grand = bills_total['total'] or 0
        paid = bills_total['paid'] or 0
        balance = self.opening_balance + (grand - paid)
        return balance
