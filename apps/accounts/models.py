from django.db import models
from django.contrib.auth.models import AbstractUser

class Role(models.Model):
    ADMIN = 'ADMIN'
    MANAGER = 'MANAGER'
    OPERATOR = 'OPERATOR'
    ACCOUNTANT = 'ACCOUNTANT'
    STORE_KEEPER = 'STORE_KEEPER'
    SALESMAN = 'SALESMAN'

    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (MANAGER, 'Manager'),
        (OPERATOR, 'Operator'),
        (ACCOUNTANT, 'Accountant'),
        (STORE_KEEPER, 'Store Keeper'),
        (SALESMAN, 'Salesman'),
    ]

    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.get_name_display()

class User(AbstractUser):
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    phone = models.CharField(max_length=20, blank=True, null=True)
    cnic = models.CharField(max_length=20, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def is_admin(self):
        return self.is_superuser or (self.role and self.role.name == Role.ADMIN)

    def is_manager(self):
        return self.is_admin() or (self.role and self.role.name == Role.MANAGER)

    def is_accountant(self):
        return self.is_admin() or (self.role and self.role.name == Role.ACCOUNTANT)

    def is_storekeeper(self):
        return self.is_admin() or (self.role and self.role.name == Role.STORE_KEEPER)

    def is_salesman(self):
        return self.is_admin() or (self.role and self.role.name == Role.SALESMAN)

    def has_module_perm(self, module, action='view'):
        """Check if user has permission for a module action. Admins always have all permissions."""
        if self.is_admin():
            return True
        perm = self.module_permissions.filter(module=module).first()
        if perm is None:
            # Default: Managers can view all; others can only view dashboard
            if self.is_manager() and action == 'view':
                return True
            if module == 'dashboard' and action == 'view':
                return True
            return False
        if action == 'view':
            return perm.can_view
        elif action == 'create':
            return perm.can_create
        elif action == 'edit':
            return perm.can_edit
        elif action == 'delete':
            return perm.can_delete
        return False

    def __str__(self):
        role_str = self.role.get_name_display() if self.role else 'No Role'
        return f"{self.get_full_name() or self.username} ({role_str})"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('CREATE', 'Created Record'),
        ('UPDATE', 'Updated Record'),
        ('DELETE', 'Deleted Record'),
        ('PRINT', 'Printed Document'),
        ('EXPORT', 'Exported Report'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    module = models.CharField(max_length=50)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.user} - {self.action} on {self.module}"

MODULE_CHOICES = [
    ('dashboard', 'Dashboard'),
    ('seeds', 'Seeds Catalog'),
    ('inventory', 'Inventory & Stock'),
    ('sales', 'Sales & Invoices'),
    ('purchases', 'Purchases & Bills'),
    ('gatepass', 'Gate Pass'),
    ('expenses', 'Expenses'),
    ('finance', 'Finance & Ledger'),
    ('reports', 'Reports'),
    ('settings', 'Settings'),
    ('accounts', 'User Management'),
]

class UserPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='module_permissions')
    module = models.CharField(max_length=50, choices=MODULE_CHOICES)
    can_view = models.BooleanField(default=True)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'module')
        ordering = ['module']

    def __str__(self):
        return f"{self.user.username} — {self.module} [V:{self.can_view} C:{self.can_create} E:{self.can_edit} D:{self.can_delete}]"
