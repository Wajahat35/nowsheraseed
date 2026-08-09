from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Role, AuditLog

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('ERP Details', {'fields': ('role', 'phone', 'cnic', 'designation', 'avatar')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'module', 'ip_address')
    list_filter = ('action', 'module', 'timestamp')
    search_fields = ('description', 'user__username', 'ip_address')
    readonly_fields = ('timestamp',)
