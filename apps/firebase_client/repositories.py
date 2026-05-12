from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .client import get_firestore_client
from .serializers import document_to_dict


@dataclass(frozen=True)
class FirestorePage:
    items: list[dict[str, Any]]
    limit: int
    has_more: bool = False


class FirestoreRepository:
    """Small repository wrapper for direct Firestore access.

    The repository preserves Firestore document field names exactly. It must not
    convert camelCase fields to snake_case before writes.
    """

    collection_name: str

    def __init__(self, collection_name: str | None = None):
        if collection_name is not None:
            self.collection_name = collection_name
        if not getattr(self, "collection_name", ""):
            raise ValueError("collection_name is required")

    @property
    def db(self):
        return get_firestore_client()

    @property
    def collection(self):
        return self.db.collection(self.collection_name)

    def list(self, *, limit: int = 50, order_by: str | None = None, descending: bool = False) -> FirestorePage:
        query = self.collection
        if order_by:
            direction = "DESCENDING" if descending else "ASCENDING"
            query = query.order_by(order_by, direction=direction)
        snapshots = list(query.limit(limit + 1).stream())
        return FirestorePage(
            items=[document_to_dict(snapshot) for snapshot in snapshots[:limit]],
            limit=limit,
            has_more=len(snapshots) > limit,
        )

    def get(self, document_id: str) -> dict[str, Any] | None:
        snapshot = self.collection.document(document_id).get()
        if not snapshot.exists:
            return None
        return document_to_dict(snapshot)

    def create(self, data: dict[str, Any], *, document_id: str | None = None) -> str:
        if document_id:
            self.collection.document(document_id).set(data)
            return document_id
        document_ref = self.collection.document()
        document_ref.set(data)
        return document_ref.id

    def update(self, document_id: str, data: dict[str, Any]) -> None:
        self.collection.document(document_id).update(data)

    def set(self, document_id: str, data: dict[str, Any], *, merge: bool = True) -> None:
        self.collection.document(document_id).set(data, merge=merge)

    def soft_delete(self, document_id: str) -> None:
        self.update(document_id, {"isDeleted": True})

    def where_equal(self, field: str, value: Any, *, limit: int = 50) -> list[dict[str, Any]]:
        snapshots = self.collection.where(field, "==", value).limit(limit).stream()
        return [document_to_dict(snapshot) for snapshot in snapshots]

    def batch_update(self, payloads: Iterable[tuple[str, dict[str, Any]]]) -> None:
        batch = self.db.batch()
        for document_id, data in payloads:
            batch.update(self.collection.document(document_id), data)
        batch.commit()
