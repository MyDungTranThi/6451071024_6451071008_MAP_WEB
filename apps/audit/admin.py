from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ("created_at", "user", "action", "collection", "document_id", "summary")
    list_filter = ("action", "collection", "created_at")
    search_fields = ("collection", "document_id", "summary", "user__username")
    readonly_fields = (
        "user",
        "action",
        "collection",
        "document_id",
        "summary",
        "before",
        "after",
        "ip_address",
        "user_agent",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
