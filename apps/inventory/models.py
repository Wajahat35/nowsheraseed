from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.seeds.models import Seed, SeedBatch
from apps.suppliers.models import Supplier

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


class SeedProcessing(models.Model):
    batch_number = models.CharField(max_length=50, unique=True, editable=False)
    date = models.DateField()
    grower = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='processings', verbose_name="Grower")
    seed = models.ForeignKey(Seed, on_delete=models.CASCADE, related_name='processings')
    target_batch = models.ForeignKey(SeedBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name='processings')

    raw_input_kg = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total Raw Seed Input (KG)")
    clean_seed_kg = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Clean / Usable Seed Output (KG)")
    wastage_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Wastage / By-Product (KG)")
    wastage_type = models.ForeignKey('wastage.WastageType', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Wastage Grade")
    moisture_dust_loss_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Moisture / Dust Loss (KG)")

    recovery_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Recovery Rate (%)")
    wastage_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Wastage Rate (%)")
    loss_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Dust/Moisture Loss Rate (%)")
    equivalent_bags = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Equivalent Packaged Bags")

    notes = models.TextField(blank=True, null=True, verbose_name="Processing & Quality Notes")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']
        verbose_name = "Seed Processing Run"
        verbose_name_plural = "Seed Processing Runs"

    def clean(self):
        super().clean()
        raw = Decimal(str(self.raw_input_kg or 0))
        clean = Decimal(str(self.clean_seed_kg or 0))
        wst = Decimal(str(self.wastage_kg or 0))
        loss = Decimal(str(self.moisture_dust_loss_kg or 0))

        if raw <= Decimal('0'):
            raise ValidationError("Total Raw Input (KG) must be greater than zero.")

        # If loss is not manually provided, auto-compute difference as permissible loss
        computed_total = clean + wst + loss
        if abs(raw - computed_total) > Decimal('0.05'):
            # Check if loss can absorb the difference
            if loss == Decimal('0') and raw >= (clean + wst):
                self.moisture_dust_loss_kg = raw - (clean + wst)
            else:
                raise ValidationError(
                    f"Equation validation error: Total Raw Input ({raw:,.2f} KG) must equal Clean Seed ({clean:,.2f} KG) + Wastage ({wst:,.2f} KG) + Loss ({loss:,.2f} KG). Current sum is {computed_total:,.2f} KG."
                )

    def save(self, *args, **kwargs):
        if not self.batch_number:
            last = SeedProcessing.objects.order_by('-id').first()
            last_id = last.id if last else 0
            self.batch_number = f"PRC-{(last_id + 1):04d}"

        raw = Decimal(str(self.raw_input_kg or 0))
        clean = Decimal(str(self.clean_seed_kg or 0))
        wst = Decimal(str(self.wastage_kg or 0))

        # Auto-compute loss if difference exists
        if raw >= (clean + wst) and (self.moisture_dust_loss_kg is None or Decimal(str(self.moisture_dust_loss_kg)) == Decimal('0')):
            self.moisture_dust_loss_kg = raw - (clean + wst)

        loss = Decimal(str(self.moisture_dust_loss_kg or 0))

        if raw > Decimal('0'):
            self.recovery_rate = round((clean / raw) * Decimal('100.0'), 2)
            self.wastage_rate = round((wst / raw) * Decimal('100.0'), 2)
            self.loss_rate = round((loss / raw) * Decimal('100.0'), 2)

        # Equivalent bags
        pack_wgt = Decimal(str(self.seed.weight_kg or 50.0))
        if pack_wgt > Decimal('0'):
            self.equivalent_bags = round(clean / pack_wgt, 2)
        else:
            self.equivalent_bags = clean

        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            # 1. Credit Clean Seed (KG) to SeedBatch
            from django.utils import timezone
            from datetime import timedelta
            today = timezone.now().date()

            if not self.target_batch:
                self.target_batch = SeedBatch.objects.create(
                    seed=self.seed,
                    batch_number=f"PRC-BATCH-{self.batch_number}",
                    lot_number=f"LOT-{self.batch_number}",
                    manufacturing_date=self.date or today,
                    expiry_date=(self.date or today) + timedelta(days=365),
                    initial_qty=clean,
                    current_qty=clean,
                    purchase_price=self.seed.purchase_price or Decimal('0.00'),
                    sale_price=self.seed.retail_price or Decimal('0.00')
                )
                SeedProcessing.objects.filter(pk=self.pk).update(target_batch=self.target_batch)
            else:
                self.target_batch.current_qty = Decimal(str(self.target_batch.current_qty)) + clean
                self.target_batch.save()

            # Record Stock Movement for usable clean seed
            StockMovement.objects.create(
                movement_type='STOCK_IN',
                seed=self.seed,
                batch=self.target_batch,
                quantity=clean,
                reference_no=self.batch_number,
                notes=f"Clean seed recovered from intake processing ({self.grower.name}) - {self.equivalent_bags} equivalent bags",
                user=self.created_by
            )

            # 2. Divert Wastage (KG) to Wastage Module
            if wst > Decimal('0') and self.wastage_type:
                from apps.wastage.models import WastageStock, WastageMovement
                w_stock, _ = WastageStock.objects.get_or_create(wastage_type=self.wastage_type)
                w_stock.current_stock_kg = Decimal(str(w_stock.current_stock_kg)) + wst
                w_stock.save()

                WastageMovement.objects.create(
                    movement_type='INTAKE_PROCESSING',
                    wastage_type=self.wastage_type,
                    quantity_kg=wst,
                    reference_no=self.batch_number,
                    notes=f"Wastage diverted from processing run {self.batch_number} (Grower: {self.grower.name})",
                    user=self.created_by
                )

    def __str__(self):
        return f"{self.batch_number} - {self.seed.name} (Input: {self.raw_input_kg} KG | Clean: {self.clean_seed_kg} KG | Wastage: {self.wastage_kg} KG)"

