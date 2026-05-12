from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import create_audit_log
from apps.core.constants import COLLECTION_NOTIFICATIONS, COLLECTION_ORDERS, COLLECTION_USERS
from apps.firebase_client.repositories import FirestoreRepository
from apps.firebase_client.validators import assert_firestore_field_names


class NotificationService:
    def __init__(self, repository: FirestoreRepository | None = None):
        self.repository = repository or FirestoreRepository(COLLECTION_NOTIFICATIONS)

    def list_notifications(self, *, status: str = "all", query: str = "", limit: int = 100) -> list[dict[str, Any]]:
        page = self.repository.list(limit=limit, order_by="createdAt", descending=True)
        notifications = self._enrich_notifications(page.items)
        if status == "read":
            notifications = [item for item in notifications if item.get("isRead", False)]
        elif status == "unread":
            notifications = [item for item in notifications if not item.get("isRead", False)]
        normalized_query = query.strip().lower()
        if normalized_query:
            notifications = [
                item
                for item in notifications
                if normalized_query in str(item.get("id", "")).lower()
                or normalized_query in str(item.get("userId", "")).lower()
                or normalized_query in str(item.get("userLabel", "")).lower()
                or normalized_query in str(item.get("orderId", "")).lower()
                or normalized_query in str(item.get("orderLabel", "")).lower()
                or normalized_query in str(item.get("orderStatus", "")).lower()
                or normalized_query in str(item.get("message", "")).lower()
            ]
        return notifications

    def get_notification(self, notification_id: str) -> dict[str, Any] | None:
        notification = self.repository.get(notification_id)
        if not notification:
            return None
        enriched = self._enrich_notifications([notification])
        return enriched[0] if enriched else notification

    def list_user_options(self, *, limit: int = 300) -> list[dict[str, str]]:
        page = FirestoreRepository(COLLECTION_USERS).list(limit=limit)
        options = []
        for user in page.items:
            full_name = " ".join(
                part for part in [user.get("firstName", ""), user.get("lastName", "")] if part
            ).strip()
            display_name = user.get("displayName") or user.get("fullName") or user.get("name") or ""
            label_parts = [
                full_name or display_name or user.get("username") or user.get("email") or user.get("id", ""),
                user.get("email") or user.get("phone") or user.get("id", ""),
            ]
            label = " - ".join(dict.fromkeys(part for part in label_parts if part))
            options.append({"id": user["id"], "label": label or user["id"]})
        return sorted(options, key=lambda item: item["label"].lower())

    def list_order_options(self, *, limit: int = 500) -> list[dict[str, str]]:
        page = FirestoreRepository(COLLECTION_ORDERS).list(limit=limit, order_by="createdAt", descending=True)
        options = []
        for order in page.items:
            user_id = order.get("userId") or ""
            if not user_id:
                continue
            code = order.get("orderCode") or order.get("id", "")
            status = order.get("status") or "pending"
            recipient = order.get("recipientName") or ""
            total = order.get("total")
            total_text = f" - {total}" if total not in (None, "") else ""
            label = f"{code} - {status}{total_text}"
            if recipient:
                label = f"{label} - {recipient}"
            options.append(
                {
                    "id": order["id"],
                    "userId": user_id,
                    "label": label,
                    "status": status,
                }
            )
        return options

    def create_notification(self, *, payload: dict[str, Any], request: HttpRequest | None) -> str:
        assert_firestore_field_names(payload)
        create_payload = {**payload, "createdAt": timezone.now()}
        notification_id = self.repository.create(create_payload)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_CREATE,
            collection=COLLECTION_NOTIFICATIONS,
            document_id=notification_id,
            summary=f"Tạo notification cho user {payload.get('userId', '')}",
            after={**create_payload, "id": notification_id},
        )
        return notification_id

    def update_notification(self, *, notification_id: str, payload: dict[str, Any], request: HttpRequest | None) -> None:
        assert_firestore_field_names(payload)
        before = self.get_notification(notification_id) or {}
        update_payload = {**payload, "updatedAt": timezone.now()}
        self.repository.set(notification_id, update_payload, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_UPDATE,
            collection=COLLECTION_NOTIFICATIONS,
            document_id=notification_id,
            summary=f"Cập nhật notification {notification_id}",
            before=before,
            after=update_payload,
        )

    def _enrich_notifications(self, notifications: list[dict[str, Any]]) -> list[dict[str, Any]]:
        users = self._user_map()
        orders = self._order_map()
        enriched = []
        for notification in notifications:
            user = users.get(notification.get("userId", ""), {})
            order = orders.get(notification.get("orderId", ""), {})
            enriched.append(
                {
                    **notification,
                    "userLabel": self._user_label(user, notification.get("userId", "")),
                    "orderLabel": self._order_label(order, notification.get("orderId", "")),
                    "createdAtDisplay": self._format_datetime(notification.get("createdAt")),
                }
            )
        return enriched

    @staticmethod
    def _user_map(limit: int = 500) -> dict[str, dict[str, Any]]:
        try:
            users = FirestoreRepository(COLLECTION_USERS).list(limit=limit).items
        except Exception:
            return {}
        return {user["id"]: user for user in users if user.get("id")}

    @staticmethod
    def _order_map(limit: int = 700) -> dict[str, dict[str, Any]]:
        try:
            orders = FirestoreRepository(COLLECTION_ORDERS).list(limit=limit, order_by="createdAt", descending=True).items
        except Exception:
            return {}
        return {order["id"]: order for order in orders if order.get("id")}

    @staticmethod
    def _user_label(user: dict[str, Any], fallback: str) -> str:
        if not user:
            return fallback or "-"
        full_name = " ".join(part for part in [user.get("firstName", ""), user.get("lastName", "")] if part).strip()
        name = full_name or user.get("displayName") or user.get("fullName") or user.get("username") or user.get("email") or fallback
        contact = user.get("email") or user.get("phone") or ""
        return " - ".join(dict.fromkeys(part for part in [name, contact] if part))

    @staticmethod
    def _order_label(order: dict[str, Any], fallback: str) -> str:
        if not order:
            return fallback or "-"
        code = order.get("orderCode") or order.get("id") or fallback
        total = order.get("total")
        total_text = NotificationService._format_money(total) if total not in (None, "") else ""
        return " - ".join(part for part in [code, order.get("status"), total_text] if part)

    @staticmethod
    def _format_money(value: Any) -> str:
        try:
            return f"{float(value):,.0f}".replace(",", ".") + " đ"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_datetime(value: Any) -> str:
        if not value:
            return "-"
        if hasattr(value, "strftime"):
            return value.strftime("%d/%m/%Y %H:%M")
        return str(value)
