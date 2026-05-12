from __future__ import annotations

from typing import Any

from django import forms
from django.http import HttpRequest

from apps.core.image_uploads import save_admin_image_upload
from apps.firebase_client.validators import assert_firestore_field_names


GENDER_CHOICES = (
    ("", "Chưa chọn"),
    ("male", "Nam"),
    ("female", "Nữ"),
    ("other", "Khác"),
)

BANK_PRESETS = {
    "VCB": {"bankName": "Vietcombank", "shortName": "VCB", "bankCode": "VCB", "bin": "970436"},
    "TCB": {"bankName": "Techcombank", "shortName": "TCB", "bankCode": "TCB", "bin": "970407"},
    "BIDV": {"bankName": "BIDV", "shortName": "BIDV", "bankCode": "BIDV", "bin": "970418"},
    "CTG": {"bankName": "VietinBank", "shortName": "CTG", "bankCode": "CTG", "bin": "970415"},
    "MB": {"bankName": "MB Bank", "shortName": "MB", "bankCode": "MB", "bin": "970422"},
    "ACB": {"bankName": "ACB", "shortName": "ACB", "bankCode": "ACB", "bin": "970416"},
    "VPB": {"bankName": "VPBank", "shortName": "VPB", "bankCode": "VPB", "bin": "970432"},
    "TPB": {"bankName": "TPBank", "shortName": "TPB", "bankCode": "TPB", "bin": "970423"},
    "VIB": {"bankName": "VIB", "shortName": "VIB", "bankCode": "VIB", "bin": "970441"},
    "HDB": {"bankName": "HDBank", "shortName": "HDB", "bankCode": "HDB", "bin": "970437"},
    "AGR": {"bankName": "Agribank", "shortName": "AGR", "bankCode": "AGR", "bin": "970405"},
    "STB": {"bankName": "Sacombank", "shortName": "STB", "bankCode": "STB", "bin": "970403"},
    "OCB": {"bankName": "OCB", "shortName": "OCB", "bankCode": "OCB", "bin": "970448"},
    "MSB": {"bankName": "MSB", "shortName": "MSB", "bankCode": "MSB", "bin": "970426"},
    "SHB": {"bankName": "SHB", "shortName": "SHB", "bankCode": "SHB", "bin": "970443"},
}


class CustomerForm(forms.Form):
    firstName = forms.CharField(label="Tên", max_length=100, required=False)
    lastName = forms.CharField(label="Họ", max_length=100, required=False)
    username = forms.CharField(label="Username", max_length=100, required=False)
    email = forms.EmailField(label="Email", required=False)
    phone = forms.CharField(label="Số điện thoại", max_length=30, required=False)
    emailVerified = forms.BooleanField(label="Email đã xác minh", required=False)
    gender = forms.ChoiceField(label="Giới tính", required=False, choices=GENDER_CHOICES)
    dateOfBirth = forms.DateField(label="Ngày sinh", required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def to_firestore_payload(self) -> dict[str, Any]:
        if not self.is_valid():
            raise ValueError("Cannot build Firestore payload from invalid form")
        payload = {
            "firstName": self.cleaned_data.get("firstName") or "",
            "lastName": self.cleaned_data.get("lastName") or "",
            "username": self.cleaned_data.get("username") or "",
            "email": self.cleaned_data.get("email") or "",
            "phone": self.cleaned_data.get("phone") or "",
            "emailVerified": bool(self.cleaned_data.get("emailVerified")),
        }
        if self.cleaned_data.get("gender"):
            payload["gender"] = self.cleaned_data["gender"]
        if self.cleaned_data.get("dateOfBirth"):
            payload["dateOfBirth"] = self.cleaned_data["dateOfBirth"]
        assert_firestore_field_names(payload)
        return payload


class AddressForm(forms.Form):
    receiverName = forms.CharField(label="Người nhận", max_length=160)
    phoneNumber = forms.CharField(label="Số điện thoại", max_length=30)
    city = forms.CharField(label="Tỉnh/Thành", max_length=120)
    ward = forms.CharField(label="Phường/Xã", max_length=120)
    street = forms.CharField(label="Đường", max_length=160)
    number = forms.CharField(label="Số nhà", max_length=80)
    isDefault = forms.BooleanField(label="Địa chỉ mặc định", required=False)

    def to_firestore_payload(self) -> dict[str, Any]:
        if not self.is_valid():
            raise ValueError("Cannot build Firestore payload from invalid form")
        payload = {
            "receiverName": self.cleaned_data["receiverName"],
            "phoneNumber": self.cleaned_data["phoneNumber"],
            "city": self.cleaned_data["city"],
            "ward": self.cleaned_data["ward"],
            "street": self.cleaned_data["street"],
            "number": self.cleaned_data["number"],
            "isDefault": bool(self.cleaned_data.get("isDefault")),
        }
        assert_firestore_field_names(payload)
        return payload


class BankAccountForm(forms.Form):
    accountNumber = forms.CharField(label="Số tài khoản", max_length=80)
    accountHolderName = forms.CharField(label="Chủ tài khoản", max_length=160)
    bankPreset = forms.ChoiceField(
        label="Ngân hàng",
        required=False,
        choices=[("", "Chọn ngân hàng")] + [(key, value["bankName"]) for key, value in BANK_PRESETS.items()],
        help_text="Chọn ngân hàng để hệ thống tự điền mã ngân hàng và BIN.",
    )
    bankName = forms.CharField(
        label="Ngân hàng khác",
        max_length=220,
        required=False,
        help_text="Chỉ nhập khi ngân hàng không có trong danh sách.",
    )
    shortName = forms.CharField(label="Tên viết tắt", max_length=50, required=False, widget=forms.HiddenInput)
    bankCode = forms.CharField(label="Mã ngân hàng", max_length=50, required=False, widget=forms.HiddenInput)
    bin = forms.CharField(label="BIN", max_length=50, required=False, widget=forms.HiddenInput)
    logo = forms.URLField(label="Logo URL", required=False)
    logoUpload = forms.ImageField(
        label="Upload logo mới",
        required=False,
        help_text="Nếu chọn file, hệ thống sẽ upload và thay thế Logo URL.",
    )

    def __init__(self, *args: Any, initial: dict[str, Any] | None = None, **kwargs: Any):
        data = dict(initial or {})
        preset = self._resolve_bank_preset(data)
        if preset:
            data["bankPreset"] = preset
        super().__init__(*args, initial=data, **kwargs)

    @staticmethod
    def _resolve_bank_preset(data: dict[str, Any]) -> str:
        bank_code = (data.get("bankCode") or data.get("shortName") or "").upper()
        if bank_code in BANK_PRESETS:
            return bank_code
        bank_name = (data.get("bankName") or "").lower()
        for key, preset in BANK_PRESETS.items():
            if bank_name and bank_name == preset["bankName"].lower():
                return key
        return ""

    def clean_accountHolderName(self) -> str:
        return (self.cleaned_data.get("accountHolderName") or "").strip().upper()

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        bank_preset = cleaned_data.get("bankPreset") or ""
        if bank_preset:
            preset = BANK_PRESETS[bank_preset]
            cleaned_data.update(preset)
        elif not cleaned_data.get("bankName"):
            self.add_error("bankPreset", "Chọn ngân hàng hoặc nhập tên ngân hàng khác.")
        return cleaned_data

    def apply_image_uploads(self, request: HttpRequest) -> None:
        logo_upload = self.cleaned_data.get("logoUpload")
        if logo_upload:
            self.cleaned_data["logo"] = save_admin_image_upload(request, logo_upload, folder="bank-logos")

    def to_firestore_payload(self) -> dict[str, Any]:
        if not self.is_valid():
            raise ValueError("Cannot build Firestore payload from invalid form")
        payload = {
            "accountNumber": self.cleaned_data["accountNumber"],
            "accountHolderName": self.cleaned_data["accountHolderName"],
            "bankName": self.cleaned_data.get("bankName") or "",
            "shortName": self.cleaned_data.get("shortName") or "",
            "bankCode": self.cleaned_data.get("bankCode") or "",
            "bin": self.cleaned_data.get("bin") or "",
            "logo": self.cleaned_data.get("logo") or "",
        }
        assert_firestore_field_names(payload)
        return payload
