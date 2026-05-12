from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import create_audit_log
from apps.core.constants import (
    COLLECTION_ORDERS,
    COLLECTION_USERS,
    SUBCOLLECTION_ADDRESSES,
    SUBCOLLECTION_BANK_ACCOUNTS,
)
from apps.firebase_client.repositories import FirestoreRepository
from apps.firebase_client.validators import assert_firestore_field_names


class CustomerService:
    def __init__(
        self,
        repository: FirestoreRepository | None = None,
        order_repository: FirestoreRepository | None = None,
    ):
        self.repository = repository or FirestoreRepository(COLLECTION_USERS)
        self.order_repository = order_repository or FirestoreRepository(COLLECTION_ORDERS)

    def list_customers(self, *, query: str = "", limit: int = 100) -> list[dict[str, Any]]:
        page = self.repository.list(limit=limit, order_by="email")
        customers = [self._with_customer_display(customer) for customer in page.items]
        normalized_query = query.strip().lower()
        if normalized_query:
            customers = [
                customer
                for customer in customers
                if normalized_query in str(customer.get("id", "")).lower()
                or normalized_query in str(customer.get("firstName", "")).lower()
                or normalized_query in str(customer.get("lastName", "")).lower()
                or normalized_query in str(customer.get("nameDisplay", "")).lower()
                or normalized_query in str(customer.get("username", "")).lower()
                or normalized_query in str(customer.get("email", "")).lower()
                or normalized_query in str(customer.get("phone", "")).lower()
            ]
        return customers

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        customer = self.repository.get(customer_id)
        return self._with_customer_display(customer) if customer else None

    def list_customer_orders(self, *, customer_id: str, limit: int = 300) -> list[dict[str, Any]]:
        orders = self.order_repository.where_equal("userId", customer_id, limit=limit)
        normalized_orders = [self._normalize_customer_order(order) for order in orders]
        return sorted(normalized_orders, key=self._created_at_sort_value, reverse=True)

    def get_order_summary(self, orders: list[dict[str, Any]]) -> dict[str, Any]:
        completed_orders = [order for order in orders if order.get("status") != "cancelled"]
        total_spent = sum(self._to_number(order.get("total")) for order in completed_orders)
        average_order_value = total_spent / len(completed_orders) if completed_orders else 0
        latest_purchase = next((order.get("createdAtDisplay") for order in completed_orders), "-")
        return {
            "totalOrders": len(orders),
            "totalSpent": self._format_money(total_spent),
            "averageOrderValue": self._format_money(average_order_value),
            "latestPurchase": latest_purchase or "-",
        }

    def update_customer(self, *, customer_id: str, payload: dict[str, Any], request: HttpRequest | None) -> None:
        assert_firestore_field_names(payload)
        before = self.get_customer(customer_id) or {}
        update_payload = {**payload, "id": customer_id, "updatedAt": timezone.now()}
        self.repository.set(customer_id, update_payload, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_UPDATE,
            collection=COLLECTION_USERS,
            document_id=customer_id,
            summary=f"Cập nhật customer {before.get('email', customer_id)}",
            before=before,
            after=update_payload,
        )

    @classmethod
    def _normalize_customer_order(cls, order: dict[str, Any]) -> dict[str, Any]:
        total = cls._to_number(order.get("total"))
        return {
            **order,
            "orderCodeDisplay": order.get("orderCode") or order.get("id") or "-",
            "createdAtDisplay": cls._format_datetime(order.get("createdAt")),
            "totalItemsDisplay": cls._resolve_total_items(order),
            "totalDisplay": cls._format_money(total),
        }

    @staticmethod
    def _with_customer_display(customer: dict[str, Any]) -> dict[str, Any]:
        full_name = " ".join(part for part in [customer.get("firstName", ""), customer.get("lastName", "")] if part).strip()
        name = full_name or customer.get("displayName") or customer.get("fullName") or customer.get("username") or customer.get("email") or customer.get("id", "-")
        contact = customer.get("email") or customer.get("phone") or ""
        return {
            **customer,
            "nameDisplay": name,
            "contactDisplay": contact,
            "identityDisplay": customer.get("username") or customer.get("id") or "-",
        }

    @staticmethod
    def _created_at_sort_value(order: dict[str, Any]) -> float:
        value = order.get("createdAt")
        if hasattr(value, "timestamp"):
            return value.timestamp()
        return 0

    @staticmethod
    def _resolve_total_items(order: dict[str, Any]) -> int | str:
        explicit_value = order.get("totalItems", order.get("itemCount"))
        if explicit_value not in (None, ""):
            return explicit_value

        items = order.get("items")
        if not isinstance(items, list):
            return 0

        quantity_total = 0
        for item in items:
            if isinstance(item, dict):
                quantity_total += int(CustomerService._to_number(item.get("quantity")))
        return quantity_total or len(items)

    @staticmethod
    def _to_number(value: Any) -> float:
        if value in (None, ""):
            return 0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _format_money(value: float) -> str:
        return f"{value:,.0f}".replace(",", ".") + " đ"

    @staticmethod
    def _format_datetime(value: Any) -> str:
        if not value:
            return "-"
        if hasattr(value, "strftime"):
            return value.strftime("%d/%m/%Y %H:%M")
        return str(value)


class UserSubcollectionService:
    def __init__(self, *, subcollection_name: str, label: str, user_repository: FirestoreRepository | None = None):
        self.subcollection_name = subcollection_name
        self.label = label
        self.user_repository = user_repository or FirestoreRepository(COLLECTION_USERS)

    def _collection(self, customer_id: str):
        return self.user_repository.collection.document(customer_id).collection(self.subcollection_name)

    @staticmethod
    def _document_to_dict(snapshot) -> dict[str, Any]:
        data = snapshot.to_dict() or {}
        data.setdefault("id", snapshot.id)
        return data

    def list_items(self, *, customer_id: str, limit: int = 100) -> list[dict[str, Any]]:
        snapshots = list(self._collection(customer_id).limit(limit).stream())
        return [self._document_to_dict(snapshot) for snapshot in snapshots]

    def get_item(self, *, customer_id: str, item_id: str) -> dict[str, Any] | None:
        snapshot = self._collection(customer_id).document(item_id).get()
        if not snapshot.exists:
            return None
        return self._document_to_dict(snapshot)

    def create_item(self, *, customer_id: str, payload: dict[str, Any], request: HttpRequest | None) -> str:
        assert_firestore_field_names(payload)
        create_payload = {**payload, "createdAt": timezone.now()}
        document_ref = self._collection(customer_id).document()
        document_ref.set(create_payload)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_CREATE,
            collection=f"{COLLECTION_USERS}/{customer_id}/{self.subcollection_name}",
            document_id=document_ref.id,
            summary=f"Tạo {self.label} cho customer {customer_id}",
            after={**create_payload, "id": document_ref.id},
        )
        return document_ref.id

    def update_item(self, *, customer_id: str, item_id: str, payload: dict[str, Any], request: HttpRequest | None) -> None:
        assert_firestore_field_names(payload)
        before = self.get_item(customer_id=customer_id, item_id=item_id) or {}
        update_payload = {**payload, "updatedAt": timezone.now()}
        self._collection(customer_id).document(item_id).set(update_payload, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_UPDATE,
            collection=f"{COLLECTION_USERS}/{customer_id}/{self.subcollection_name}",
            document_id=item_id,
            summary=f"Cập nhật {self.label} cho customer {customer_id}",
            before=before,
            after=update_payload,
        )


def address_service() -> UserSubcollectionService:
    return UserSubcollectionService(subcollection_name=SUBCOLLECTION_ADDRESSES, label="address")


def bank_account_service() -> UserSubcollectionService:
    return UserSubcollectionService(subcollection_name=SUBCOLLECTION_BANK_ACCOUNTS, label="bank account")
