from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.http import HttpRequest
from django.utils.functional import Promise

from .models import AuditLog


def get_client_ip(request: HttpRequest) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def to_json_safe(value: Any) -> Any:
    """Convert Firestore/Django values into data accepted by JSONField."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Promise):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_json_safe(item) for item in value]
    if hasattr(value, "latitude") and hasattr(value, "longitude"):
        return {"latitude": value.latitude, "longitude": value.longitude}
    if hasattr(value, "path"):
        return str(value.path)
    return str(value)


def create_audit_log(
    *,
    request: HttpRequest | None,
    action: str,
    summary: str,
    collection: str = "",
    document_id: str = "",
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    user = None
    ip_address = None
    user_agent = ""
    if request is not None:
        if request.user.is_authenticated:
            user = request.user
        ip_address = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

    return AuditLog.objects.create(
        user=user,
        action=action,
        collection=collection,
        document_id=document_id,
        summary=summary,
        before=to_json_safe(before or {}),
        after=to_json_safe(after or {}),
        ip_address=ip_address,
        user_agent=user_agent,
    )
