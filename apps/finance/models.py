from django.db import models
from django.conf import settings

class AccountCategory(models.Model):
    TYPES = [
        ('ASSET', 'Assets'),
        ('LIABILITY', 'Liabilities'),
        ('EQUITY', 'Equity'),
        ('REVENUE', 'Revenue'),
        ('EXPENSE', 'Expenses'),
    ]

    name = models.CharField(max_length=50, choices=TYPES, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.get_name_display()

class ChartOfAccount(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    category = models.ForeignKey(AccountCategory, on_delete=models.CASCADE, related_name='accounts')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name} ({self.category.get_name_display()})"

    def get_balance(self):
        debit_sum = JournalItem.objects.filter(account=self).aggregate(total=models.Sum('debit'))['total'] or 0
        credit_sum = JournalItem.objects.filter(account=self).aggregate(total=models.Sum('credit'))['total'] or 0
        if self.category.name in ['ASSET', 'EXPENSE']:
            return debit_sum - credit_sum
        else:
            return credit_sum - debit_sum

class JournalVoucher(models.Model):
    VOUCHER_TYPES = [
        ('JV', 'Journal Voucher'),
        ('CPV', 'Cash Payment Voucher'),
        ('CRV', 'Cash Receipt Voucher'),
        ('BPV', 'Bank Payment Voucher'),
        ('BRV', 'Bank Receipt Voucher'),
        ('EXPV', 'Expense Voucher'),
    ]

    voucher_number = models.CharField(max_length=50, unique=True, editable=False)
    voucher_type = models.CharField(max_length=10, choices=VOUCHER_TYPES, default='JV')
    date = models.DateField()
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    total_debit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.voucher_number:
            last_v = JournalVoucher.objects.order_by('-id').first()
            last_id = last_v.id if last_v else 0
            self.voucher_number = f"VCH-{(last_id + 1):04d}"
        super().save(*args, **kwargs)

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit

    @property
    def balance_difference(self):
        return abs(self.total_debit - self.total_credit)

    def __str__(self):
        return f"{self.voucher_number} ({self.voucher_type}) - PKR {self.total_debit}"

class JournalItem(models.Model):
    voucher = models.ForeignKey(JournalVoucher, on_delete=models.CASCADE, related_name='items')
    account = models.ForeignKey(ChartOfAccount, on_delete=models.CASCADE, related_name='journal_items')
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    narration = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.account.name}: Dr {self.debit} | Cr {self.credit}"
