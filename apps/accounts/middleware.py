from django.http import HttpResponseForbidden
from django.urls import resolve, Resolver404

# Maps URL namespace (app_name) to UserPermission module key
APP_TO_MODULE = {
    'sales':      'sales',
    'purchases':  'purchases',
    'gatepass':   'gatepass',
    'seeds':      'seeds',
    'inventory':  'inventory',
    'customers':  'sales',       # customers are part of sales visibility
    'suppliers':  'purchases',   # suppliers are part of purchases visibility
    'expenses':   'expenses',
    'finance':    'finance',
    'reports':    'reports',
    'accounts':   'accounts',
    'settings_app': 'settings',
    'dashboard':  'dashboard',
}

# Paths that are always public / don't need checking
EXEMPT_PATHS = ['/accounts/login/', '/accounts/logout/', '/static/', '/media/']


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Attach client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            request.client_ip = x_forwarded_for.split(',')[0]
        else:
            request.client_ip = request.META.get('REMOTE_ADDR')

        # 2. Permission enforcement for authenticated, non-admin users
        if request.user.is_authenticated and not request.user.is_admin():
            path = request.path_info

            # Skip exempt paths
            if not any(path.startswith(ep) for ep in EXEMPT_PATHS):
                try:
                    match = resolve(path)
                    app_name = match.app_name or match.namespace or ''
                    module = APP_TO_MODULE.get(app_name)
                    if module and not request.user.has_module_perm(module, 'view'):
                        return HttpResponseForbidden(
                            '<html><body style="font-family:Inter,sans-serif;display:flex;align-items:center;'
                            'justify-content:center;height:100vh;margin:0;background:#f0f4f8;">'
                            '<div style="text-align:center;padding:40px;background:#fff;border-radius:12px;'
                            'box-shadow:0 4px 24px rgba(0,0,0,0.08);max-width:480px;">'
                            '<div style="font-size:3rem;margin-bottom:1rem;">🔒</div>'
                            '<h2 style="color:#1e293b;font-weight:700;margin-bottom:0.5rem;">Access Restricted</h2>'
                            '<p style="color:#64748b;margin-bottom:1.5rem;">You do not have permission to access '
                            f'<strong>{module.replace("_"," ").title()}</strong>. '
                            'Please contact your administrator to request access.</p>'
                            '<a href="/dashboard/" style="display:inline-block;padding:10px 24px;background:#10b981;'
                            'color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">← Go to Dashboard</a>'
                            '</div></body></html>'
                        )
                except Resolver404:
                    pass

        response = self.get_response(request)
        return response
