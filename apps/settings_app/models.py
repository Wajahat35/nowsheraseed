import os
from django.db import models

class CompanyProfile(models.Model):
    name = models.CharField(max_length=200, default="AgriSeed Enterprise ERP")
    tagline = models.CharField(max_length=255, default="Quality Seeds for Maximum Yield", blank=True)
    ntn = models.CharField(max_length=50, blank=True, null=True, verbose_name="NTN Number")
    strn = models.CharField(max_length=50, blank=True, null=True, verbose_name="Sales Tax Reg No (STRN)")
    logo = models.ImageField(upload_to='company/', blank=True, null=True)
    invoice_logo = models.ImageField(upload_to='company/', blank=True, null=True)
    phone = models.CharField(max_length=30, default="+92-42-111-222-333", blank=True, null=True)
    mobile = models.CharField(max_length=30, default="+92-300-1234567", blank=True, null=True)
    email = models.EmailField(default="info@agriseederp.com", blank=True, null=True)
    website = models.CharField(max_length=255, default="https://agriseederp.com", blank=True, null=True)
    erp_base_url = models.CharField(
        max_length=255,
        default="https://nowsheraseed.onrender.com",
        blank=True, null=True,
        verbose_name="ERP Server Base URL",
        help_text="Used in QR codes so phones can open invoice verification pages."
    )
    address = models.TextField(default="Industrial Agriculture Zone, Multan Road, Lahore, Pakistan", blank=True, null=True)
    city = models.CharField(max_length=100, default="Lahore", blank=True, null=True)
    
    currency_symbol = models.CharField(max_length=10, default="PKR", blank=True, null=True)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00, verbose_name="GST Rate (%)", blank=True, null=True)
    invoice_prefix = models.CharField(max_length=10, default="INV-", blank=True, null=True)
    purchase_prefix = models.CharField(max_length=10, default="PUR-", blank=True, null=True)
    gatepass_prefix = models.CharField(max_length=10, default="GP-", blank=True, null=True)
    invoice_footer = models.TextField(default="Thank you for your business! Quality Seed Certified by FSC&RD.", blank=True, null=True)

    def __str__(self):
        return self.name

    def get_logo_url(self):
        if self.logo and hasattr(self.logo, 'url'):
            try:
                if os.path.exists(self.logo.path):
                    return self.logo.url
            except Exception:
                pass
        return '/static/icon.png'

    def get_invoice_logo_url(self):
        if self.invoice_logo and hasattr(self.invoice_logo, 'url'):
            try:
                if os.path.exists(self.invoice_logo.path):
                    return self.invoice_logo.url
            except Exception:
                pass
        return self.get_logo_url()

    @classmethod
    def get_instance(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj
