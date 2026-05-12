from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """System audit log stored in SQLite, not business data."""

    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_STATUS_CHANGE = "status_change"
    ACTION_FIRESTORE_ERROR = "firestore_error"

    ACTION_CHOICES = (
        (ACTION_CREATE, "Create"),
        (ACTION_UPDATE, "Update"),
        (ACTION_DELETE, "Delete"),
        (ACTION_STATUS_CHANGE, "Status change"),
        (ACTION_FIRESTORE_ERROR, "Firestore error"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    collection = models.CharField(max_length=128, blank=True)
    document_id = models.CharField(max_length=255, blank=True)
    summary = models.CharField(max_length=255)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = (
            models.Index(fields=("collection", "document_id")),
            models.Index(fields=("action", "created_at")),
        )

    def __str__(self):
        return f"{self.action} {self.collection}/{self.document_id}".strip()
