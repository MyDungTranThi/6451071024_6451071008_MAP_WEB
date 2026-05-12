from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest


def admin_shell(request: HttpRequest) -> dict:
    """Expose Django Admin/Unfold shell context to custom admin templates."""

    if not request.path.startswith(("/admin-dashboard/", "/admin-catalog/", "/admin-sales/", "/admin-customers/", "/admin-reviews/", "/admin-notifications/")):
        return {}

    return admin.site.each_context(request)
