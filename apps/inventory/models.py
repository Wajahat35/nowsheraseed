from django.db import models
from django.conf import settings
from apps.seeds.models import Seed, SeedBatch

class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    location = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('STOCK_IN', 'Stock In (Purchase)'),
        ('STOCK_OUT', 'Stock Out (Sale)'),
        ('TRANSFER', 'Stock Transfer'),
        ('ADJUSTMENT', 'Stock Adjustment'),
        ('DAMAGE', 'Damage Stock Write-off'),
        ('EXPIRED', 'Expired Stock Write-off'),
        ('RETURN', 'Sales/Purchase Return'),
    ]

    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    seed = models.ForeignKey(Seed, on_delete=models.CASCADE, related_name='movements')
    batch = models.ForeignKey(SeedBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements')
    quantity = models.IntegerField(help_text="Positive for additions, negative for deductions")
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.seed.name} [{self.quantity}]"

class StockAdjustment(models.Model):
    ADJUSTMENT_CHOICES = [
        ('DAMAGE', 'Damage Write-Off'),
        ('EXPIRED', 'Expiry Write-Off'),
        ('DEDUCTION', 'Manual Deduction / Correction'),
    ]

    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_CHOICES)
    seed = models.ForeignKey(Seed, on_delete=models.CASCADE)
    batch = models.ForeignKey(SeedBatch, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    reason = models.TextField()
    adjusted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # All adjustment types are write-offs (deductions only)
            if self.batch:
                self.batch.current_qty = max(0, self.batch.current_qty - self.quantity)
                self.batch.save()

            # Record Stock Movement with correct type
            movement_map = {
                'DAMAGE': 'DAMAGE',
                'EXPIRED': 'EXPIRED',
                'DEDUCTION': 'ADJUSTMENT',
            }
            StockMovement.objects.create(
                movement_type=movement_map.get(self.adjustment_type, 'ADJUSTMENT'),
                seed=self.seed,
                batch=self.batch,
                quantity=-self.quantity,  # Always negative (write-off)
                reference_no=f"ADJ-{self.id}",
                notes=self.reason,
                user=self.adjusted_by
            )

    def __str__(self):
        return f"Adjustment #{self.id} - {self.seed.name} ({self.adjustment_type})"
