from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import create_audit_log
from apps.core.constants import COLLECTION_BOOKS, COLLECTION_ORDERS, COLLECTION_REVIEWS, COLLECTION_USERS
from apps.firebase_client.repositories import FirestoreRepository
from apps.firebase_client.validators import assert_firestore_field_names


class ReviewService:
    def __init__(self, repository: FirestoreRepository | None = None):
        self.repository = repository or FirestoreRepository(COLLECTION_REVIEWS)

    def list_reviews(self, *, status: str = "active", query: str = "", limit: int = 100) -> list[dict[str, Any]]:
        page = self.repository.list(limit=limit, order_by="createdAt", descending=True)
        reviews = self._enrich_reviews(page.items)
        if status == "active":
            reviews = [review for review in reviews if not review.get("isDeleted", False)]
        elif status == "deleted":
            reviews = [review for review in reviews if review.get("isDeleted", False)]
        normalized_query = query.strip().lower()
        if normalized_query:
            reviews = [
                review
                for review in reviews
                if normalized_query in str(review.get("id", "")).lower()
                or normalized_query in str(review.get("userId", "")).lower()
                or normalized_query in str(review.get("userName", "")).lower()
                or normalized_query in str(review.get("userLabel", "")).lower()
                or normalized_query in str(review.get("productId", "")).lower()
                or normalized_query in str(review.get("bookTitleDisplay", "")).lower()
                or normalized_query in str(review.get("orderId", "")).lower()
                or normalized_query in str(review.get("orderCodeDisplay", "")).lower()
                or normalized_query in str(review.get("comment", "")).lower()
            ]
        return reviews

    def get_review(self, review_id: str) -> dict[str, Any] | None:
        review = self.repository.get(review_id)
        if not review:
            return None
        enriched = self._enrich_reviews([review])
        return enriched[0] if enriched else review

    def set_deleted(self, *, review_id: str, is_deleted: bool, request: HttpRequest | None) -> None:
        before = self.get_review(review_id) or {}
        payload = {"isDeleted": is_deleted, "updatedAt": timezone.now()}
        assert_firestore_field_names(payload)
        self.repository.set(review_id, payload, merge=True)
        create_audit_log(
            request=request,
            action=AuditLog.ACTION_STATUS_CHANGE,
            collection=COLLECTION_REVIEWS,
            document_id=review_id,
            summary=("Ẩn" if is_deleted else "Hiện") + f" review {review_id}",
            before=before,
            after=payload,
        )

    def _enrich_reviews(self, reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        users = self._map_collection(COLLECTION_USERS)
        books = self._map_collection(COLLECTION_BOOKS)
        orders = self._map_collection(COLLECTION_ORDERS, order_by="createdAt", descending=True)
        enriched = []
        for review in reviews:
            user = users.get(review.get("userId", ""), {})
            book_id = review.get("bookId") or review.get("productId") or ""
            book = books.get(book_id, {})
            order = orders.get(review.get("orderId", ""), {})
            enriched.append(
                {
                    **review,
                    "bookId": book_id,
                    "userLabel": self._user_label(user, review.get("userName") or review.get("userId", "")),
                    "bookTitleDisplay": review.get("productName") or review.get("bookTitle") or book.get("title") or book_id or "-",
                    "bookCoverDisplay": review.get("coverImage") or book.get("coverImage") or "",
                    "orderCodeDisplay": order.get("orderCode") or review.get("orderId") or "-",
                    "createdAtDisplay": self._format_datetime(review.get("createdAt")),
                }
            )
        return enriched

    @staticmethod
    def _map_collection(
        collection_name: str,
        *,
        limit: int = 700,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, dict[str, Any]]:
        try:
            items = FirestoreRepository(collection_name).list(limit=limit, order_by=order_by, descending=descending).items
        except Exception:
            return {}
        return {item["id"]: item for item in items if item.get("id")}

    @staticmethod
    def _user_label(user: dict[str, Any], fallback: str) -> str:
        if not user:
            return fallback or "-"
        full_name = " ".join(part for part in [user.get("firstName", ""), user.get("lastName", "")] if part).strip()
        name = full_name or user.get("displayName") or user.get("fullName") or user.get("username") or user.get("email") or fallback
        contact = user.get("email") or user.get("phone") or ""
        return " - ".join(dict.fromkeys(part for part in [name, contact] if part))

    @staticmethod
    def _format_datetime(value: Any) -> str:
        if not value:
            return "-"
        if hasattr(value, "strftime"):
            return value.strftime("%d/%m/%Y %H:%M")
        return str(value)
