from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError

from apps.core.constants import BOOK_FORMATS, COUPON_TYPES, ORDER_STATUSES


FORBIDDEN_ORDER_STATUSES = {"shipped", "canceled", "created", "returned", "refunded", "completed"}
COUPON_TYPE_ALIASES = {
    "percentage": "percent",
    "free_shipping": "freeShipping",
}


def validate_allowed_value(value: str, allowed_values: tuple[str, ...], field_name: str) -> str:
    if value not in allowed_values:
        raise ValidationError({field_name: f"Giá trị không hợp lệ: {value}"})
    return value


def validate_order_status(status: str) -> str:
    if status in FORBIDDEN_ORDER_STATUSES:
        raise ValidationError({"status": f"Không dùng status không đúng schema app: {status}"})
    return validate_allowed_value(status, ORDER_STATUSES, "status")


def normalize_coupon_type(coupon_type: str) -> str:
    normalized = COUPON_TYPE_ALIASES.get(coupon_type, coupon_type)
    return validate_allowed_value(normalized, COUPON_TYPES, "type")


def validate_book_format(format_value: str) -> str:
    return validate_allowed_value(format_value, BOOK_FORMATS, "format")


def assert_firestore_field_names(data: dict[str, Any]) -> None:
    """Reject obviously snake_case payload keys before writing to Firestore."""

    invalid_keys = [key for key in data if "_" in key]
    if invalid_keys:
        raise ValidationError(
            {
                "fields": (
                    "Không ghi snake_case vào Firestore. "
                    f"Các field không hợp lệ: {', '.join(sorted(invalid_keys))}"
                )
            }
        )
