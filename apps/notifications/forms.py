from __future__ import annotations

from typing import Any

from django import forms

from apps.core.constants import ORDER_STATUSES
from apps.firebase_client.validators import assert_firestore_field_names, validate_order_status


class NotificationForm(forms.Form):
    userId = forms.ChoiceField(label="Khách hàng")
    orderId = forms.ChoiceField(label="Đơn hàng", required=False)
    orderStatus = forms.ChoiceField(
        label="Trạng thái đơn hàng",
        choices=[("", "---")] + [(value, value) for value in ORDER_STATUSES],
        required=False,
    )
    message = forms.CharField(label="Nội dung", widget=forms.Textarea(attrs={"rows": 4}))
    isRead = forms.BooleanField(label="Đã đọc", required=False)

    def __init__(
        self,
        *args: Any,
        users: list[dict[str, str]] | None = None,
        orders: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.users = users or []
        self.orders = orders or []

        selected_user_id = ""
        if self.is_bound:
            selected_user_id = self.data.get(self.add_prefix("userId"), "")
        else:
            selected_user_id = self.initial.get("userId", "")
        selected_order_id = ""
        if self.is_bound:
            selected_order_id = self.data.get(self.add_prefix("orderId"), "")
        else:
            selected_order_id = self.initial.get("orderId", "")

        if selected_user_id and not any(user["id"] == selected_user_id for user in self.users):
            self.users.append({"id": selected_user_id, "label": selected_user_id})
        if selected_order_id and not any(order["id"] == selected_order_id for order in self.orders):
            self.orders.append(
                {
                    "id": selected_order_id,
                    "userId": selected_user_id,
                    "label": selected_order_id,
                    "status": self.initial.get("orderStatus", ""),
                }
            )

        self.fields["userId"].choices = [("", "Chọn khách hàng")] + [
            (user["id"], user["label"]) for user in self.users
        ]
        self.fields["orderId"].choices = [("", "Không gắn đơn hàng")] + [
            (order["id"], order["label"])
            for order in self.orders
            if not selected_user_id or order.get("userId") == selected_user_id
        ]

    def clean_orderStatus(self) -> str:
        status = self.cleaned_data.get("orderStatus") or ""
        return validate_order_status(status) if status else ""

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        user_id = cleaned_data.get("userId") or ""
        order_id = cleaned_data.get("orderId") or ""
        if order_id:
            matching_order = next((order for order in self.orders if order["id"] == order_id), None)
            if not matching_order:
                self.add_error("orderId", "Đơn hàng không hợp lệ.")
            elif matching_order.get("userId") != user_id:
                self.add_error("orderId", "Đơn hàng không thuộc khách hàng đã chọn.")
            elif not cleaned_data.get("orderStatus"):
                cleaned_data["orderStatus"] = matching_order.get("status", "")
        return cleaned_data

    def to_firestore_payload(self) -> dict[str, Any]:
        if not self.is_valid():
            raise ValueError("Cannot build Firestore payload from invalid form")
        payload = {
            "userId": self.cleaned_data["userId"],
            "orderId": self.cleaned_data.get("orderId") or "",
            "orderStatus": self.cleaned_data.get("orderStatus") or "",
            "message": self.cleaned_data["message"],
            "isRead": bool(self.cleaned_data.get("isRead")),
        }
        assert_firestore_field_names(payload)
        return payload
