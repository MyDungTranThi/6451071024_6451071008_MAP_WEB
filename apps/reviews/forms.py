from __future__ import annotations

from typing import Any

from django import forms

from apps.firebase_client.validators import assert_firestore_field_names


class ReviewModerationForm(forms.Form):
    isDeleted = forms.BooleanField(label="Ẩn review", required=False)

    def to_firestore_payload(self) -> dict[str, Any]:
        if not self.is_valid():
            raise ValueError("Cannot build Firestore payload from invalid form")
        payload = {"isDeleted": bool(self.cleaned_data.get("isDeleted"))}
        assert_firestore_field_names(payload)
        return payload
