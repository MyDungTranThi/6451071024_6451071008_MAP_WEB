from django.db import models


class PermissionAnchor(models.Model):
    """Unmanaged model that owns custom permissions for Firestore admin views."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ("manage_books", "Can manage books"),
            ("manage_categories", "Can manage categories"),
            ("manage_brands", "Can manage brands"),
            ("manage_orders", "Can manage orders"),
            ("manage_coupons", "Can manage coupons"),
            ("manage_customers", "Can manage customers"),
            ("manage_reviews", "Can manage reviews"),
            ("manage_notifications", "Can manage notifications"),
            ("view_dashboard", "Can view dashboard"),
        ]
