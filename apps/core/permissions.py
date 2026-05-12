from functools import wraps

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required

PERM_MANAGE_BOOKS = "core.manage_books"
PERM_MANAGE_CATEGORIES = "core.manage_categories"
PERM_MANAGE_BRANDS = "core.manage_brands"
PERM_MANAGE_ORDERS = "core.manage_orders"
PERM_MANAGE_COUPONS = "core.manage_coupons"
PERM_MANAGE_CUSTOMERS = "core.manage_customers"
PERM_MANAGE_REVIEWS = "core.manage_reviews"
PERM_MANAGE_NOTIFICATIONS = "core.manage_notifications"
PERM_VIEW_DASHBOARD = "core.view_dashboard"


def admin_permission_required(permission: str):
    """Require staff login and a specific Django permission for a custom admin view."""

    def decorator(view_func):
        protected = staff_member_required(permission_required(permission, raise_exception=True)(view_func))

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            return protected(request, *args, **kwargs)

        return wrapper

    return decorator
