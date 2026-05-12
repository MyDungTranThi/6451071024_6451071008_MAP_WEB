from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import create_audit_log
from apps.core.constants import COLLECTION_BOOKS, COLLECTION_BRANDS, COLLECTION_CATEGORIES
from apps.firebase_client.repositories import FirestoreRepository
from apps.firebase_client.validators import assert_firestore_field_names


class BookService:
    """Firestore-backed Books service. No Django ORM business models are used."""

    def __init__(self, repository: FirestoreRepository | None = None):
        self.repository = repository or FirestoreRepository(COLLECTION_BOOKS)

    def list_books(self, *, status: str = "active", query: str = "", limit: int = 100) -> list[dict[str, Any]]:
        page = self.repository.list(limit=limit, order_by="title")
        books = page.items
        if status == "active":
            books = [book for book in books if book.get("isActive", True) and not book.get("isDeleted", False)]
        elif status == "deleted":
            books = [book for book in books if book.get("isDeleted", False)]
        elif status == "inactive":
            books = [book for book in books if not book.get("isActive", True) and not book.get("isDeleted", False)]

        normalized_query = query.strip().lower()
        if normalized_query:
            books = [
                book
                for book in books
                if normalized_query in str(book.get("title", "")).lower()
                or normalized_query in str(book.get("author", "")).lower()
                or normalized_query in str(book.get("publisher", "")).lower()
                or normalized_query in str(book.get("id", "")).lower()
            ]
        return books

    def get_book(self, book_id: str) -> dict[str, Any] | None:
        return self.repository.get(book_id)

    def create_book(self, *, payload: dict[str, Any], document_id: str | None, request: HttpRequest | None) -> str:
        assert_firestore_field_names(payload)
        now = timezone.now()
        create_payload = {
            **payload,
            "createdAt": now,
            "updatedAt": now,
        }
        book_id = self.repository.create(create_payload, document_id=document_id or None)
        if not document_id:
            self.repository.set(book_id, {"id": book_id}, merge=True)
            create_payload["id"] = book_id
        else:
            create_payload["id"] = document_id
            self.repository.set(document_id, {"id": document_id}, merge=True)

        create_audit_log(
            request=request,
            action=AuditLog.ACTION_CREATE,
            collection=COLLECTION_BOOKS,
            document_id=book_id,
            summary=f"Tạo sách {create_payload.get('title', book_id)}",
            after=create_payload,
        )
        return book_id

    def update_book(self, *, book_id: str, payload: dict[str, Any], request: HttpRequest | None) -> None:
        assert_firestore_field_names(payload)
        before = self.get_book(book_id) or {}
        update_payload = {
            **payload,
            "id": book_id,
            "updatedAt": timezone.now(),
        }
        self.repository.set(book_id, update_payload, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_UPDATE,
            collection=COLLECTION_BOOKS,
            document_id=book_id,
            summary=f"Cập nhật sách {update_payload.get('title', book_id)}",
            before=before,
            after=update_payload,
        )

    def set_active(self, *, book_id: str, is_active: bool, request: HttpRequest | None) -> None:
        before = self.get_book(book_id) or {}
        payload = {"isActive": is_active, "updatedAt": timezone.now()}
        self.repository.set(book_id, payload, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_STATUS_CHANGE,
            collection=COLLECTION_BOOKS,
            document_id=book_id,
            summary=("Hiện sách" if is_active else "Ẩn sách") + f" {before.get('title', book_id)}",
            before=before,
            after=payload,
        )

    def soft_delete_book(self, *, book_id: str, request: HttpRequest | None) -> None:
        before = self.get_book(book_id) or {}
        payload = {"isDeleted": True, "isActive": False, "updatedAt": timezone.now()}
        self.repository.set(book_id, payload, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_DELETE,
            collection=COLLECTION_BOOKS,
            document_id=book_id,
            summary=f"Xóa mềm sách {before.get('title', book_id)}",
            before=before,
            after=payload,
        )

    def restore_book(self, *, book_id: str, request: HttpRequest | None) -> None:
        before = self.get_book(book_id) or {}
        payload = {"isDeleted": False, "isActive": True, "updatedAt": timezone.now()}
        self.repository.set(book_id, payload, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_STATUS_CHANGE,
            collection=COLLECTION_BOOKS,
            document_id=book_id,
            summary=f"Khôi phục sách {before.get('title', book_id)}",
            before=before,
            after=payload,
        )


class SimpleCatalogService:
    """Shared Firestore CRUD for simple catalog collections."""

    def __init__(self, *, collection_name: str, label: str, repository: FirestoreRepository | None = None):
        self.collection_name = collection_name
        self.label = label
        self.repository = repository or FirestoreRepository(collection_name)

    def list_items(self, *, query: str = "", limit: int = 100) -> list[dict[str, Any]]:
        page = self.repository.list(limit=limit, order_by="name")
        items = page.items
        normalized_query = query.strip().lower()
        if normalized_query:
            items = [
                item
                for item in items
                if normalized_query in str(item.get("name", "")).lower()
                or normalized_query in str(item.get("id", "")).lower()
            ]
        return items

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        return self.repository.get(item_id)

    def create_item(self, *, payload: dict[str, Any], document_id: str | None, request: HttpRequest | None) -> str:
        assert_firestore_field_names(payload)
        item_id = self.repository.create({**payload, "id": document_id or ""}, document_id=document_id or None)
        if not document_id:
            self.repository.set(item_id, {"id": item_id}, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_CREATE,
            collection=self.collection_name,
            document_id=item_id,
            summary=f"Tạo {self.label} {payload.get('name', item_id)}",
            after={**payload, "id": item_id},
        )
        return item_id

    def update_item(self, *, item_id: str, payload: dict[str, Any], request: HttpRequest | None) -> None:
        assert_firestore_field_names(payload)
        before = self.get_item(item_id) or {}
        update_payload = {**payload, "id": item_id}
        self.repository.set(item_id, update_payload, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_UPDATE,
            collection=self.collection_name,
            document_id=item_id,
            summary=f"Cập nhật {self.label} {payload.get('name', item_id)}",
            before=before,
            after=update_payload,
        )


def category_service() -> SimpleCatalogService:
    return SimpleCatalogService(collection_name=COLLECTION_CATEGORIES, label="category")


def brand_service() -> SimpleCatalogService:
    return SimpleCatalogService(collection_name=COLLECTION_BRANDS, label="brand")
