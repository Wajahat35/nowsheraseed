from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Role

@receiver(post_migrate)
def create_default_roles(sender, **kwargs):
    if sender.name == 'apps.accounts':
        roles = [
            (Role.ADMIN, 'Full system administrative control'),
            (Role.MANAGER, 'Operational management and approvals'),
            (Role.OPERATOR, 'Data entry and daily operations'),
            (Role.ACCOUNTANT, 'Financial accounts, vouchers, and reporting'),
            (Role.STORE_KEEPER, 'Stock, warehouse, and gate pass management'),
            (Role.SALESMAN, 'POS sales terminal and customer invoices'),
        ]
        for role_code, desc in roles:
            Role.objects.get_or_create(name=role_code, defaults={'description': desc})
