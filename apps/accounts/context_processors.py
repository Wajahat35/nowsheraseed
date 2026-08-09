"""
Context processor that injects user module permissions into every template.
Usage in templates: {% if perms_map.sales %}  or  {% if perms_map.inventory %}
"""

MODULE_LIST = [
    'dashboard', 'sales', 'purchases', 'gatepass',
    'seeds', 'inventory', 'expenses', 'finance',
    'reports', 'accounts', 'settings',
]


def user_module_permissions(request):
    """
    Injects a dict `perms_map` into context:
      perms_map['sales']      = True/False  (can_view)
      perms_map['sales_create'] = True/False (can_create)
      perms_map['sales_edit']   = True/False
      perms_map['sales_delete'] = True/False
    Admin users always get True for everything.
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'perms_map': {}}

    user = request.user
    perms_map = {}

    for module in MODULE_LIST:
        perms_map[module] = user.has_module_perm(module, 'view')
        perms_map[f'{module}_create'] = user.has_module_perm(module, 'create')
        perms_map[f'{module}_edit'] = user.has_module_perm(module, 'edit')
        perms_map[f'{module}_delete'] = user.has_module_perm(module, 'delete')

    return {'perms_map': perms_map}
