from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def document_to_dict(snapshot: Any) -> dict[str, Any]:
    """Convert a Firestore document snapshot to a dict while preserving fields."""

    data = snapshot.to_dict() or {}
    data["id"] = snapshot.id
    return data


def to_firestore_value(value: Any) -> Any:
    """Normalize common Django/Python values before Firestore writes."""

    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, list):
        return [to_firestore_value(item) for item in value]
    if isinstance(value, tuple):
        return [to_firestore_value(item) for item in value]
    if isinstance(value, dict):
        return {key: to_firestore_value(item) for key, item in value.items()}
    return value


def to_firestore_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Return a Firestore payload without changing field naming conventions."""

    return {key: to_firestore_value(value) for key, value in data.items() if value != ""}
