import io
import qrcode
from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile

class GatePass(models.Model):
    PASS_TYPE_CHOICES = [
        ('SALES', 'Sales Outward Gate Pass (INV)'),
        ('PURCHASE', 'Purchase Inward Gate Pass (PUR)'),
        ('MANUAL', 'Manual / General Cargo Gate Pass'),
    ]

    STATUS_CHOICES = [
        ('Issued', 'Issued'),
        ('Verified', 'Security Verified'),
        ('Completed', 'Completed / Dispatched'),
    ]

    pass_number = models.CharField(max_length=50, unique=True, editable=False)
    pass_type = models.CharField(max_length=15, choices=PASS_TYPE_CHOICES, default='SALES')
    date_time = models.DateTimeField(auto_now_add=True)
    
    vehicle_number = models.CharField(max_length=50, help_text="e.g. LES-1234")
    driver_name = models.CharField(max_length=150)
    driver_cnic = models.CharField(max_length=20, verbose_name="Driver CNIC (XXXXX-XXXXXXX-X)")
    driver_mobile = models.CharField(max_length=30, verbose_name="Driver Mobile (03XXXXXXXXX)")
    transport_company = models.CharField(max_length=200, blank=True, null=True)
    
    invoice_reference = models.CharField(max_length=100, blank=True, null=True, help_text="Sales/Purchase Invoice #")
    total_bags = models.PositiveIntegerField(default=0)
    total_weight_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total Weight (Kg)")
    
    qr_code_image = models.ImageField(upload_to='qrcodes/gatepass/', blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Issued', blank=True)
    
    seed = models.ForeignKey('seeds.Seed', on_delete=models.SET_NULL, null=True, blank=True, related_name='gate_passes', help_text="Optional: Direct seed for manual inward pass")
    batch = models.ForeignKey('seeds.SeedBatch', on_delete=models.SET_NULL, null=True, blank=True, related_name='gate_passes', help_text="Optional: Direct batch for manual inward pass")
    is_stock_updated = models.BooleanField(default=False, blank=True, help_text="True if inward goods have been added to inventory stock")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_gatepasses')

    def save(self, *args, **kwargs):
        if self.is_stock_updated is None:
            self.is_stock_updated = False

        if not self.pass_number:
            last_gp = GatePass.objects.order_by('-id').first()
            last_id = last_gp.id if last_gp else 0
            self.pass_number = f"GP-{(last_id + 1):04d}"

        if not self.status:
            self.status = 'Issued'

        if not self.qr_code_image:
            qr_content = f"GATEPASS VERIFICATION\nPass #: {self.pass_number}\nType: {self.get_pass_type_display()}\nVehicle: {self.vehicle_number}\nDriver: {self.driver_name}\nCNIC: {self.driver_cnic}\nBags: {self.total_bags}\nWeight: {self.total_weight_kg} Kg\nRef: {self.invoice_reference}"
            qr_img = qrcode.make(qr_content)
            buffer = io.BytesIO()
            qr_img.save(buffer, format='PNG')
            self.qr_code_image.save(f"qr_{self.pass_number}.png", ContentFile(buffer.getvalue()), save=False)

        super().save(*args, **kwargs)

        if self.pass_type in ['PURCHASE', 'MANUAL', 'SALES'] and not self.is_stock_updated:
            self.process_inward_stock()

    def process_inward_stock(self, user=None):
        """Auto-add product to inventory stock when inwarded via gate pass."""
        if self.is_stock_updated:
            return False

        if self.pass_type not in ['PURCHASE', 'MANUAL', 'SALES']:
            return False

        try:
            from apps.purchases.models import PurchaseInvoice
            from apps.sales.models import SalesInvoice
            from apps.inventory.models import StockMovement
            from apps.seeds.models import SeedBatch
            from django.utils import timezone
            from datetime import timedelta

            added_count = 0

            # 1. Linked Purchase Bill (PUR-XXXX)
            if self.pass_type == 'PURCHASE' and self.invoice_reference and self.invoice_reference.startswith('PUR-'):
                pur_invoice = PurchaseInvoice.objects.filter(invoice_number=self.invoice_reference).first()
                if pur_invoice:
                    already_moved_by_pur = StockMovement.objects.filter(
                        reference_no=pur_invoice.invoice_number,
                        movement_type='STOCK_IN'
                    ).exists()

                    if already_moved_by_pur:
                        self.is_stock_updated = True
                        GatePass.objects.filter(pk=self.pk).update(is_stock_updated=True)
                        return True

                    for item in pur_invoice.items.all():
                        batch = item.batch
                        if not batch:
                            batch = SeedBatch.objects.filter(seed=item.seed).order_by('-id').first()
                            if not batch:
                                today = timezone.now().date()
                                batch = SeedBatch.objects.create(
                                    seed=item.seed,
                                    batch_number=f"INW-{self.pass_number}",
                                    lot_number=f"LOT-{self.pass_number}",
                                    manufacturing_date=today,
                                    expiry_date=today + timedelta(days=365),
                                    initial_qty=item.quantity,
                                    current_qty=0,
                                    purchase_price=item.unit_price or 0,
                                    sale_price=item.seed.retail_price or 0
                                )

                        batch.current_qty += item.quantity
                        batch.save()

                        StockMovement.objects.create(
                            movement_type='STOCK_IN',
                            seed=item.seed,
                            batch=batch,
                            quantity=item.quantity,
                            reference_no=self.pass_number,
                            notes=f"Auto Inwarded via Gate Pass {self.pass_number} (Ref: {pur_invoice.invoice_number})",
                            user=user or self.created_by
                        )
                        added_count += 1

            # 2. Linked Sales Bill (INV-XXXX)
            elif self.pass_type == 'SALES' and self.invoice_reference and self.invoice_reference.startswith('INV-'):
                inv_invoice = SalesInvoice.objects.filter(invoice_number=self.invoice_reference).first()
                if inv_invoice:
                    already_moved_by_inv = StockMovement.objects.filter(
                        reference_no=inv_invoice.invoice_number,
                        movement_type='STOCK_OUT'
                    ).exists()

                    if already_moved_by_inv:
                        self.is_stock_updated = True
                        GatePass.objects.filter(pk=self.pk).update(is_stock_updated=True)
                        return True

                    for item in inv_invoice.items.all():
                        batch = item.batch
                        if not batch:
                            batch = SeedBatch.objects.filter(seed=item.seed).order_by('-id').first()
                            
                        if batch:
                            batch.current_qty -= item.quantity
                            batch.save()

                            StockMovement.objects.create(
                                movement_type='STOCK_OUT',
                                seed=item.seed,
                                batch=batch,
                                quantity=item.quantity,
                                reference_no=self.pass_number,
                                notes=f"Auto Outwarded via Gate Pass {self.pass_number} (Ref: {inv_invoice.invoice_number})",
                                user=user or self.created_by
                            )
                        added_count += 1

            # 3. Direct Seed Inward (Manual / Non-Invoice Inward Gate Pass)
            elif self.pass_type == 'MANUAL' and self.seed and self.total_bags and self.total_bags > 0:
                already_moved = StockMovement.objects.filter(
                    reference_no=self.pass_number,
                    seed=self.seed,
                    movement_type='STOCK_IN'
                ).exists()

                if not already_moved:
                    batch = self.batch
                    if not batch:
                        batch = SeedBatch.objects.filter(seed=self.seed).order_by('-id').first()
                        if not batch:
                            today = timezone.now().date()
                            batch = SeedBatch.objects.create(
                                seed=self.seed,
                                batch_number=f"INW-{self.pass_number}",
                                lot_number=f"LOT-{self.pass_number}",
                                manufacturing_date=today,
                                expiry_date=today + timedelta(days=365),
                                initial_qty=self.total_bags,
                                current_qty=0,
                                purchase_price=self.seed.purchase_price or 0,
                                sale_price=self.seed.retail_price or 0
                            )

                    batch.current_qty += self.total_bags
                    batch.save()

                    StockMovement.objects.create(
                        movement_type='STOCK_IN',
                        seed=self.seed,
                        batch=batch,
                        quantity=self.total_bags,
                        reference_no=self.pass_number,
                        notes=f"Auto Inwarded via Gate Pass {self.pass_number}",
                        user=user or self.created_by
                    )
                added_count += 1

            self.is_stock_updated = True
            GatePass.objects.filter(pk=self.pk).update(is_stock_updated=True)
            return True

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error inwarding stock for Gate Pass {self.pass_number}: {e}")
            return False

    def __str__(self):
        return f"{self.pass_number} ({self.get_pass_type_display()}) - Vehicle: {self.vehicle_number} - Driver: {self.driver_name}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('gatepass:gatepass_detail', kwargs={'pk': self.pk})
