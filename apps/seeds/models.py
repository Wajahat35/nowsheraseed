import io
import qrcode
from django.db import models
from django.core.files.base import ContentFile

class CropType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class SeedCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    company_name = models.CharField(max_length=150, blank=True, null=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)

    def __str__(self):
        return self.name

class Seed(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Discontinued', 'Discontinued'),
        ('Out of Stock', 'Out of Stock'),
    ]

    code = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=200)
    variety = models.CharField(max_length=100)
    crop_type = models.ForeignKey(CropType, on_delete=models.SET_NULL, null=True, related_name='seeds')
    category = models.ForeignKey(SeedCategory, on_delete=models.SET_NULL, null=True, related_name='seeds')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, related_name='seeds')
    
    packing_size = models.CharField(max_length=50, help_text="e.g. 10 Kg Bag, 50 Kg Bag, 1 Kg Pack")
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2, default=1.00, verbose_name="Unit Weight (Kg)")
    
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    retail_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00, verbose_name="GST (%)")
    
    min_stock_alert = models.IntegerField(default=10, verbose_name="Minimum Stock Alert Quantity")
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True)
    qr_code = models.ImageField(upload_to='qrcodes/seeds/', blank=True, null=True)
    image = models.ImageField(upload_to='seeds/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.code:
            last_seed = Seed.objects.order_by('-id').first()
            last_id = last_seed.id if last_seed else 0
            self.code = f"SEED-{(last_id + 1):04d}"
        
        if not self.barcode:
            self.barcode = self.code

        # Generate QR Code automatically
        if not self.qr_code:
            qr_content = f"SEED ERP | Code: {self.code} | Name: {self.name} | Variety: {self.variety} | Price: PKR {self.retail_price}"
            qr_img = qrcode.make(qr_content)
            buffer = io.BytesIO()
            qr_img.save(buffer, format='PNG')
            self.qr_code.save(f"qr_{self.code}.png", ContentFile(buffer.getvalue()), save=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name} ({self.variety})"

    def get_total_stock(self):
        """Returns total available stock from all batches. Batches are the single source of truth."""
        return sum(b.current_qty for b in self.batches.all())

class SeedBatch(models.Model):
    batch_number = models.CharField(max_length=100)
    lot_number = models.CharField(max_length=100)
    seed = models.ForeignKey(Seed, on_delete=models.CASCADE, related_name='batches')
    manufacturing_date = models.DateField()
    expiry_date = models.DateField()
    initial_qty = models.IntegerField(default=0)
    current_qty = models.IntegerField(default=0)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['expiry_date']
        unique_together = ('batch_number', 'seed')

    def __str__(self):
        return f"Batch #{self.batch_number} (Lot #{self.lot_number}) - {self.seed.name} [Qty: {self.current_qty}]"

    def is_expired(self):
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()
