from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import create_audit_log
from apps.core.constants import COLLECTION_BOOKS, COLLECTION_COUPONS, COLLECTION_ORDERS, COLLECTION_USERS
from apps.firebase_client.repositories import FirestoreRepository
from apps.firebase_client.validators import assert_firestore_field_names, validate_order_status


class OrderService:
    def __init__(self, repository: FirestoreRepository | None = None):
        self.repository = repository or FirestoreRepository(COLLECTION_ORDERS)

    def list_orders(self, *, status: str = "all", query: str = "", limit: int = 100) -> list[dict[str, Any]]:
        page = self.repository.list(limit=limit, order_by="createdAt", descending=True)
        orders = self._enrich_orders(page.items)
        if status != "all":
            orders = [order for order in orders if order.get("status") == status]
        normalized_query = query.strip().lower()
        if normalized_query:
            orders = [
                order
                for order in orders
                if normalized_query in str(order.get("orderCode", "")).lower()
                or normalized_query in str(order.get("userId", "")).lower()
                or normalized_query in str(order.get("customerLabel", "")).lower()
                or normalized_query in str(order.get("recipientName", "")).lower()
                or normalized_query in str(order.get("phoneNumber", "")).lower()
                or normalized_query in str(order.get("id", "")).lower()
            ]
        return orders

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        order = self.repository.get(order_id)
        if not order:
            return None
        return self._enrich_order_detail(order)

    def update_status(self, *, order_id: str, status: str, request: HttpRequest | None) -> None:
        status = validate_order_status(status)
        before = self.get_order(order_id) or {}
        payload = {"status": status, "updatedAt": timezone.now()}
        self.repository.set(order_id, payload, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_STATUS_CHANGE,
            collection=COLLECTION_ORDERS,
            document_id=order_id,
            summary=f"Cập nhật trạng thái đơn {before.get('orderCode', order_id)}: {before.get('status')} -> {status}",
            before=before,
            after=payload,
        )

    def _enrich_orders(self, orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        users = self._user_map()
        return [self._with_order_display(order, users=users) for order in orders]

    def _enrich_order_detail(self, order: dict[str, Any]) -> dict[str, Any]:
        users = self._user_map()
        books = self._book_map()
        enriched = self._with_order_display(order, users=users)
        enriched_items = []
        for item in enriched.get("items") or []:
            book_id = item.get("bookId") or item.get("productId") or ""
            book = books.get(book_id, {})
            enriched_items.append(
                {
                    **item,
                    "bookId": book_id,
                    "bookTitleDisplay": item.get("title") or book.get("title") or book_id or "-",
                    "bookCoverDisplay": item.get("coverImage") or book.get("coverImage") or "",
                }
            )
        enriched["items"] = enriched_items
        return enriched

    @staticmethod
    def _with_order_display(order: dict[str, Any], *, users: dict[str, dict[str, Any]]) -> dict[str, Any]:
        user_id = order.get("userId") or ""
        user = users.get(user_id, {})
        customer_name = _user_display_name(user) if user else ""
        recipient = order.get("recipientName") or ""
        return {
            **order,
            "orderCodeDisplay": order.get("orderCode") or order.get("id") or "-",
            "customerNameDisplay": customer_name or recipient or user_id or "-",
            "customerContactDisplay": user.get("email") or user.get("phone") or order.get("phoneNumber") or "",
            "customerLabel": " - ".join(
                part for part in [customer_name or recipient or user_id, user.get("email") or order.get("phoneNumber")] if part
            ),
            "totalDisplay": _format_money(order.get("total")),
            "createdAtDisplay": _format_datetime(order.get("createdAt")),
        }

    @staticmethod
    def _user_map(limit: int = 500) -> dict[str, dict[str, Any]]:
        try:
            users = FirestoreRepository(COLLECTION_USERS).list(limit=limit).items
        except Exception:
            return {}
        return {user["id"]: user for user in users if user.get("id")}

    @staticmethod
    def _book_map(limit: int = 500) -> dict[str, dict[str, Any]]:
        try:
            books = FirestoreRepository(COLLECTION_BOOKS).list(limit=limit).items
        except Exception:
            return {}
        return {book["id"]: book for book in books if book.get("id")}


class CouponService:
    def __init__(self, repository: FirestoreRepository | None = None):
        self.repository = repository or FirestoreRepository(COLLECTION_COUPONS)

    def list_coupons(self, *, query: str = "", limit: int = 100) -> list[dict[str, Any]]:
        page = self.repository.list(limit=limit, order_by="code")
        coupons = [self._with_coupon_display(coupon) for coupon in page.items]
        normalized_query = query.strip().lower()
        if normalized_query:
            coupons = [
                coupon
                for coupon in coupons
                if normalized_query in str(coupon.get("code", "")).lower()
                or normalized_query in str(coupon.get("id", "")).lower()
                or normalized_query in str(coupon.get("type", "")).lower()
            ]
        return coupons

    def get_coupon(self, coupon_id: str) -> dict[str, Any] | None:
        coupon = self.repository.get(coupon_id)
        return self._with_coupon_display(coupon) if coupon else None

    def create_coupon(self, *, payload: dict[str, Any], request: HttpRequest | None) -> str:
        assert_firestore_field_names(payload)
        coupon_id = payload["code"]
        self.repository.set(coupon_id, {**payload, "id": coupon_id}, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_CREATE,
            collection=COLLECTION_COUPONS,
            document_id=coupon_id,
            summary=f"Tạo coupon {coupon_id}",
            after={**payload, "id": coupon_id},
        )
        return coupon_id

    def update_coupon(self, *, coupon_id: str, payload: dict[str, Any], request: HttpRequest | None) -> None:
        assert_firestore_field_names(payload)
        before = self.get_coupon(coupon_id) or {}
        update_payload = {**payload, "code": coupon_id, "id": coupon_id}
        self.repository.set(coupon_id, update_payload, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_UPDATE,
            collection=COLLECTION_COUPONS,
            document_id=coupon_id,
            summary=f"Cập nhật coupon {coupon_id}",
            before=before,
            after=update_payload,
        )

    @staticmethod
    def _with_coupon_display(coupon: dict[str, Any]) -> dict[str, Any]:
        type_labels = {
            "percent": "Giảm theo %",
            "fixed": "Giảm số tiền",
            "freeShipping": "Miễn phí vận chuyển",
        }
        return {
            **coupon,
            "typeDisplay": type_labels.get(coupon.get("type"), coupon.get("type") or "-"),
            "valueDisplay": _format_money(coupon.get("value")) if coupon.get("type") == "fixed" else coupon.get("value", 0),
            "minSubtotalDisplay": _format_money(coupon.get("minSubtotal")),
            "maxDiscountDisplay": _format_money(coupon.get("maxDiscount")) if coupon.get("maxDiscount") not in (None, "") else "-",
        }


def _user_display_name(user: dict[str, Any]) -> str:
    full_name = " ".join(part for part in [user.get("firstName", ""), user.get("lastName", "")] if part).strip()
    return full_name or user.get("displayName") or user.get("fullName") or user.get("username") or user.get("email") or ""


def _format_money(value: Any) -> str:
    if value in (None, ""):
        return "0 đ"
    try:
        return f"{float(value):,.0f}".replace(",", ".") + " đ"
    except (TypeError, ValueError):
        return str(value)


def _format_datetime(value: Any) -> str:
    if not value:
        return "-"
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M")
    return str(value)
