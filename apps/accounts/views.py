from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib import messages
from .models import User, Role, AuditLog, UserPermission, MODULE_CHOICES
from .forms import CustomUserCreationForm, CustomUserChangeForm
from django.http import JsonResponse

def log_activity(user, action, module, description, request=None):
    ip_address = getattr(request, 'client_ip', None) if request else None
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        module=module,
        description=description,
        ip_address=ip_address
    )

class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        log_activity(user, 'LOGIN', 'Accounts', f"User {user.username} logged in successfully.", self.request)
        messages.success(self.request, f"Welcome back, {user.get_full_name() or user.username}!")

        target = self.request.POST.get('target_system') or self.request.GET.get('target')

        if target == 'seed' and user.has_seed_access():
            return redirect('dashboard:home')
        elif target == 'trading' and user.has_trading_access():
            return redirect('trading:dashboard')

        if user.has_both_access():
            return redirect('accounts:select_module')
        elif user.has_trading_access():
            return redirect('trading:dashboard')
        return redirect('dashboard:home')


class SelectModuleView(LoginRequiredMixin, View):
    template_name = 'accounts/select_module.html'

    def get(self, request):
        user = request.user
        if not user.has_both_access():
            if user.has_trading_access():
                return redirect('trading:dashboard')
            return redirect('dashboard:home')
        return render(request, self.template_name)


class UserLogoutView(LogoutView):
    next_page = 'accounts:login'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            log_activity(request.user, 'LOGOUT', 'Accounts', f"User {request.user.username} logged out.", request)
            messages.info(request, "You have been logged out.")
        return super().dispatch(request, *args, **kwargs)

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin()

class UserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 15
    ordering = ['username']

class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'CREATE', 'Accounts', f"Created user {self.object.username}", self.request)
        messages.success(self.request, f"User {self.object.username} created successfully!")
        return response

class UserUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'UPDATE', 'Accounts', f"Updated user {self.object.username}", self.request)
        messages.success(self.request, f"User {self.object.username} updated successfully!")
        return response

class UserDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = User
    template_name = 'accounts/user_confirm_delete.html'
    success_url = reverse_lazy('accounts:user_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_activity(request.user, 'DELETE', 'Accounts', f"Deleted user {obj.username}", request)
        messages.success(request, f"User {obj.username} deleted.")
        return super().delete(request, *args, **kwargs)

class AuditLogListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = AuditLog
    template_name = 'accounts/audit_log.html'
    context_object_name = 'logs'
    paginate_by = 25

class UserPermissionView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Admin view to manage per-module permissions for a user."""
    template_name = 'accounts/user_permissions.html'

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        perms = {}
        for module_key, module_label in MODULE_CHOICES:
            perm, _ = UserPermission.objects.get_or_create(
                user=user, module=module_key,
                defaults={'can_view': False, 'can_create': False, 'can_edit': False, 'can_delete': False}
            )
            perms[module_key] = {
                'label': module_label,
                'perm': perm,
            }
        return render(request, self.template_name, {'target_user': user, 'perms': perms, 'MODULE_CHOICES': MODULE_CHOICES})

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        for module_key, _ in MODULE_CHOICES:
            perm, _ = UserPermission.objects.get_or_create(user=user, module=module_key)
            perm.can_view = f'view_{module_key}' in request.POST
            perm.can_create = f'create_{module_key}' in request.POST
            perm.can_edit = f'edit_{module_key}' in request.POST
            perm.can_delete = f'delete_{module_key}' in request.POST
            perm.save()
        log_activity(request.user, 'UPDATE', 'Accounts', f"Updated module permissions for user {user.username}", request)
        messages.success(request, f"Permissions for {user.username} updated successfully!")
        return redirect('accounts:user_permissions', pk=pk)
