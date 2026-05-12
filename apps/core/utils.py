from decimal import Decimal
from typing import Any


def to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def compact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Remove empty string values while keeping False and zero values."""
    return {key: value for key, value in data.items() if value != ""}
