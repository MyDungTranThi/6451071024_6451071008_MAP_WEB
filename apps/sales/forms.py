from __future__ import annotations

import secrets
from typing import Any

from django import forms

from apps.core.constants import ORDER_STATUSES
from apps.firebase_client.validators import assert_firestore_field_names, normalize_coupon_type, validate_order_status


class OrderStatusForm(forms.Form):
    status = forms.ChoiceField(label="Trạng thái", choices=[(value, value) for value in ORDER_STATUSES])

    def clean_status(self) -> str:
        return validate_order_status(self.cleaned_data["status"])


class CouponForm(forms.Form):
    COUPON_TYPE_CHOICES = (
        ("percent", "Giảm theo %"),
        ("fixed", "Giảm số tiền"),
        ("freeShipping", "Miễn phí vận chuyển"),
    )

    code = forms.CharField(
        label="Mã coupon",
        max_length=80,
        required=False,
        help_text="Có thể để trống khi tạo mới, hệ thống sẽ tự sinh mã.",
    )
    type = forms.ChoiceField(label="Loại", choices=COUPON_TYPE_CHOICES)
    value = forms.DecimalField(label="Giá trị", required=False, min_value=0, max_digits=14, decimal_places=2, initial=0)
    minSubtotal = forms.DecimalField(label="Đơn tối thiểu", min_value=0, max_digits=14, decimal_places=2, initial=0)
    maxDiscount = forms.DecimalField(label="Giảm tối đa", required=False, min_value=0, max_digits=14, decimal_places=2)
    isActive = forms.BooleanField(label="Đang hoạt động", required=False, initial=True)

    def __init__(self, *args: Any, initial: dict[str, Any] | None = None, is_create: bool = False, **kwargs: Any):
        data = dict(initial or {})
        data["code"] = data.get("code") or data.get("id") or ""
        if data.get("type"):
            data["type"] = normalize_coupon_type(data["type"])
        mutable_post_data = None
        if args and hasattr(args[0], "copy"):
            mutable_post_data = args[0].copy()
            if mutable_post_data.get("type"):
                mutable_post_data["type"] = normalize_coupon_type(mutable_post_data["type"])
            args = (mutable_post_data, *args[1:])
        super().__init__(*args, initial=data, **kwargs)
        self.is_create = is_create
        if not is_create:
            self.fields["code"].disabled = True

    @staticmethod
    def generate_code() -> str:
        return f"BOOK-{secrets.token_hex(3).upper()}"

    def clean_code(self) -> str:
        code = (self.cleaned_data.get("code") or "").strip().upper()
        if any(char.isspace() for char in code) or "/" in code:
            raise forms.ValidationError("Mã coupon không được chứa khoảng trắng hoặc dấu /.")
        return code

    def clean_type(self) -> str:
        return normalize_coupon_type(self.cleaned_data["type"])

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        coupon_type = cleaned_data.get("type")
        value = cleaned_data.get("value")
        if coupon_type == "percent" and value is not None and value > 100:
            self.add_error("value", "Coupon percent không được lớn hơn 100.")
        if coupon_type == "freeShipping" and value not in (None, 0):
            self.add_error("value", "Coupon freeShipping phải có value = 0.")
        if coupon_type == "freeShipping":
            cleaned_data["value"] = 0
        return cleaned_data

    def to_firestore_payload(self) -> dict[str, Any]:
        if not self.is_valid():
            raise ValueError("Cannot build Firestore payload from invalid form")
        payload = {
            "code": self.cleaned_data["code"] or self.generate_code(),
            "type": self.cleaned_data["type"],
            "value": float(self.cleaned_data.get("value") or 0),
            "minSubtotal": float(self.cleaned_data.get("minSubtotal") or 0),
            "isActive": bool(self.cleaned_data.get("isActive")),
        }
        if self.cleaned_data.get("maxDiscount") is not None:
            payload["maxDiscount"] = float(self.cleaned_data["maxDiscount"])
        else:
            payload["maxDiscount"] = None
        assert_firestore_field_names(payload)
        return payload
