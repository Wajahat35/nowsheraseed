from django.db import models
from django.conf import settings
from apps.finance.models import ChartOfAccount

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Expense(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank', 'Bank Transfer'),
        ('Cheque', 'Cheque'),
        ('Online Transfer', 'Online Transfer'),
        ('JazzCash', 'JazzCash'),
        ('EasyPaisa', 'EasyPaisa'),
    ]

    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='expenses')
    account = models.ForeignKey(ChartOfAccount, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    date = models.DateField()
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    receipt_attachment = models.FileField(upload_to='expenses/', blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.category.name} - PKR {self.amount} ({self.date})"
