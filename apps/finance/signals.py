from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import AccountCategory, ChartOfAccount

@receiver(post_migrate)
def create_default_coa(sender, **kwargs):
    if sender.name == 'apps.finance':
        cat_asset, _ = AccountCategory.objects.get_or_create(name='ASSET', defaults={'description': 'Company Assets'})
        cat_liab, _ = AccountCategory.objects.get_or_create(name='LIABILITY', defaults={'description': 'Company Liabilities'})
        cat_eq, _ = AccountCategory.objects.get_or_create(name='EQUITY', defaults={'description': 'Owner Equity & Capital'})
        cat_rev, _ = AccountCategory.objects.get_or_create(name='REVENUE', defaults={'description': 'Sales & Operating Income'})
        cat_exp, _ = AccountCategory.objects.get_or_create(name='EXPENSE', defaults={'description': 'Cost of Goods & Operating Expenses'})

        default_accounts = [
            ('1000', 'Cash in Hand', cat_asset),
            ('1010', 'Bank Account (Meezan/HBL)', cat_asset),
            ('1100', 'Accounts Receivable (Customers)', cat_asset),
            ('1200', 'Inventory Asset (Seed Stock)', cat_asset),
            ('2000', 'Accounts Payable (Suppliers)', cat_liab),
            ('2100', 'Sales Tax Payable (GST)', cat_liab),
            ('3000', 'Owner Capital Account', cat_eq),
            ('4000', 'Seed Sales Revenue', cat_rev),
            ('4100', 'Wholesale Revenue', cat_rev),
            ('5000', 'Cost of Goods Sold (COGS)', cat_exp),
            ('6000', 'Office Expenses', cat_exp),
            ('6010', 'Salaries & Wages', cat_exp),
            ('6020', 'Electricity & Utilities', cat_exp),
            ('6030', 'Fuel & Transport', cat_exp),
            ('6040', 'Building Rent', cat_exp),
            ('6050', 'Repair & Maintenance', cat_exp),
        ]

        for code, name, category in default_accounts:
            ChartOfAccount.objects.get_or_create(code=code, defaults={'name': name, 'category': category})
