from __future__ import annotations

from typing import Any

from django import forms
from django.http import HttpRequest

from apps.core.constants import BOOK_FORMATS
from apps.core.image_uploads import save_admin_image_upload
from apps.firebase_client.validators import assert_firestore_field_names, validate_book_format


def _split_lines(value: str) -> list[str]:
    return [item.strip() for item in value.replace(",", "\n").splitlines() if item.strip()]


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleFileInput

    def clean(self, data: Any, initial: Any = None) -> list[Any]:
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleImageField, self).clean(file, initial) for file in files]


class BookForm(forms.Form):
    """Validate Firestore books payloads without creating a Django ORM model."""

    documentId = forms.CharField(label="Document ID", required=False, max_length=120, widget=forms.HiddenInput)
    title = forms.CharField(label="Tên sách", max_length=255)
    author = forms.CharField(label="Tác giả", max_length=255)
    publisher = forms.CharField(label="Nhà xuất bản", max_length=255)
    genre = forms.CharField(
        label="Thể loại chính",
        max_length=120,
        required=False,
        help_text="Có thể để trống, hệ thống sẽ lấy theo danh mục đầu tiên được chọn.",
    )
    pages = forms.IntegerField(label="Số trang", min_value=0)
    price = forms.DecimalField(label="Giá", min_value=0, max_digits=14, decimal_places=2)
    salePrice = forms.DecimalField(label="Giá khuyến mãi", required=False, min_value=0, max_digits=14, decimal_places=2)
    stock = forms.IntegerField(label="Tồn kho", min_value=0, initial=0)
    soldQuantity = forms.IntegerField(label="Đã bán", min_value=0, initial=0)
    rating = forms.DecimalField(label="Rating", min_value=0, max_value=5, max_digits=3, decimal_places=2, initial=0)
    ratingCount = forms.IntegerField(label="Số lượt rating", min_value=0, initial=0)
    coverImage = forms.URLField(label="Cover image URL", required=False, max_length=1000)
    coverImageUpload = forms.ImageField(
        label="Upload cover mới",
        required=False,
        help_text="Nếu chọn file, hệ thống sẽ upload và thay thế Cover image URL.",
    )
    imagesText = forms.CharField(
        label="Danh sách ảnh",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Mỗi dòng một URL hoặc phân tách bằng dấu phẩy.",
    )
    extraImageUpload = MultipleImageField(
        label="Upload thêm ảnh",
        required=False,
        help_text="Có thể chọn nhiều ảnh, hệ thống sẽ thêm vào danh sách ảnh bên dưới.",
    )
    availableFormats = forms.MultipleChoiceField(
        label="Định dạng",
        choices=[(value, value) for value in BOOK_FORMATS],
        widget=forms.CheckboxSelectMultiple,
        initial=["paperback"],
    )
    description = forms.CharField(label="Mô tả", required=False, widget=forms.Textarea(attrs={"rows": 5}))
    tagsText = forms.CharField(
        label="Tags",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Mỗi dòng một tag hoặc phân tách bằng dấu phẩy.",
    )
    categoryIds = forms.MultipleChoiceField(
        label="Danh mục",
        required=False,
        choices=[],
        widget=forms.CheckboxSelectMultiple,
        help_text="Chọn từ danh mục hiện có thay vì nhập ID thủ công.",
    )
    brandId = forms.ChoiceField(label="NXB/Brand", required=False, choices=[])
    brandName = forms.CharField(label="Brand name", required=False, max_length=255, widget=forms.HiddenInput)
    isActive = forms.BooleanField(label="Đang hiển thị", required=False, initial=True)
    isDeleted = forms.BooleanField(label="Đã xóa mềm", required=False)
    isOutOfStock = forms.BooleanField(label="Hết hàng", required=False)

    def __init__(
        self,
        *args: Any,
        initial: dict[str, Any] | None = None,
        is_create: bool = False,
        categories: list[dict[str, Any]] | None = None,
        brands: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ):
        firestore_initial = self.from_firestore(initial or {})
        super().__init__(*args, initial=firestore_initial, **kwargs)
        self.is_create = is_create
        self.category_options = categories or []
        self.brand_options = brands or []
        self.fields["categoryIds"].choices = self._build_category_choices(
            self.category_options,
            firestore_initial.get("categoryIds") or [],
        )
        self.fields["brandId"].choices = self._build_brand_choices(
            self.brand_options,
            firestore_initial.get("brandId") or "",
        )
        if not is_create:
            self.fields["documentId"].disabled = True
            self.fields["documentId"].required = False

    @staticmethod
    def from_firestore(book: dict[str, Any]) -> dict[str, Any]:
        data = dict(book)
        data["documentId"] = book.get("id", "")
        data["imagesText"] = "\n".join(book.get("images") or [])
        data["tagsText"] = "\n".join(book.get("tags") or [])
        data["categoryIds"] = book.get("categoryIds") or []
        return data

    @staticmethod
    def _build_category_choices(categories: list[dict[str, Any]], selected_ids: list[str]) -> list[tuple[str, str]]:
        choices = [(item["id"], item.get("name") or item["id"]) for item in categories if item.get("id")]
        known_ids = {value for value, _label in choices}
        for category_id in selected_ids:
            if category_id and category_id not in known_ids:
                choices.append((category_id, category_id))
        return choices

    @staticmethod
    def _build_brand_choices(brands: list[dict[str, Any]], selected_id: str) -> list[tuple[str, str]]:
        choices = [("", "Không gắn NXB/brand")]
        choices.extend((item["id"], item.get("name") or item["id"]) for item in brands if item.get("id"))
        known_ids = {value for value, _label in choices}
        if selected_id and selected_id not in known_ids:
            choices.append((selected_id, selected_id))
        return choices

    def clean_documentId(self) -> str:
        document_id = (self.cleaned_data.get("documentId") or "").strip()
        if document_id and any(char.isspace() for char in document_id):
            raise forms.ValidationError("Document ID không được chứa khoảng trắng.")
        if document_id and "/" in document_id:
            raise forms.ValidationError("Document ID không được chứa dấu /.")
        return document_id

    def clean_availableFormats(self) -> list[str]:
        formats = self.cleaned_data.get("availableFormats") or []
        if not formats:
            raise forms.ValidationError("Chọn ít nhất một định dạng sách.")
        for value in formats:
            validate_book_format(value)
        return list(formats)

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        price = cleaned_data.get("price")
        sale_price = cleaned_data.get("salePrice")
        stock = cleaned_data.get("stock")

        if sale_price is not None and price is not None and sale_price > price:
            self.add_error("salePrice", "Giá khuyến mãi không được lớn hơn giá gốc.")

        if stock == 0 and not cleaned_data.get("isOutOfStock"):
            cleaned_data["isOutOfStock"] = True
        if stock and stock > 0 and cleaned_data.get("isOutOfStock"):
            self.add_error("isOutOfStock", "Sách còn tồn kho thì không nên đánh dấu hết hàng.")

        brand_id = cleaned_data.get("brandId") or ""
        if brand_id:
            brand_lookup = {item.get("id"): item.get("name", "") for item in self.brand_options}
            cleaned_data["brandName"] = brand_lookup.get(brand_id, cleaned_data.get("brandName", ""))

        selected_categories = cleaned_data.get("categoryIds") or []
        category_lookup = {item.get("id"): item.get("name", "") for item in self.category_options}
        cleaned_data["categoryNames"] = [
            category_lookup.get(category_id, category_id) for category_id in selected_categories
        ]
        if not cleaned_data.get("genre"):
            cleaned_data["genre"] = category_lookup.get(selected_categories[0], "") if selected_categories else ""

        return cleaned_data

    def apply_image_uploads(self, request: HttpRequest) -> None:
        cover_upload = self.cleaned_data.get("coverImageUpload")
        if cover_upload:
            self.cleaned_data["coverImage"] = save_admin_image_upload(request, cover_upload, folder="books")

        extra_uploads = self.cleaned_data.get("extraImageUpload") or []
        if extra_uploads:
            current_images = _split_lines(self.cleaned_data.get("imagesText") or "")
            for extra_upload in extra_uploads:
                current_images.append(save_admin_image_upload(request, extra_upload, folder="books"))
            self.cleaned_data["imagesText"] = "\n".join(current_images)

    def to_firestore_payload(self) -> dict[str, Any]:
        if not self.is_valid():
            raise ValueError("Cannot build Firestore payload from invalid form")

        data = self.cleaned_data
        payload = {
            "title": data["title"].strip(),
            "author": data["author"].strip(),
            "publisher": data["publisher"].strip(),
            "genre": (data.get("genre") or "").strip(),
            "pages": int(data["pages"]),
            "price": float(data["price"]),
            "coverImage": (data.get("coverImage") or "").strip(),
            "availableFormats": data["availableFormats"],
            "description": (data.get("description") or "").strip(),
            "stock": int(data.get("stock") or 0),
            "soldQuantity": int(data.get("soldQuantity") or 0),
            "rating": float(data.get("rating") or 0),
            "ratingCount": int(data.get("ratingCount") or 0),
            "isOutOfStock": bool(data.get("isOutOfStock")),
            "isActive": bool(data.get("isActive")),
            "isDeleted": bool(data.get("isDeleted")),
            "tags": _split_lines(data.get("tagsText") or ""),
            "images": _split_lines(data.get("imagesText") or ""),
            "categoryIds": list(data.get("categoryIds") or []),
            "categoryNames": list(data.get("categoryNames") or []),
            "brandId": (data.get("brandId") or "").strip(),
            "brandName": (data.get("brandName") or "").strip(),
        }
        if data.get("salePrice") is not None:
            payload["salePrice"] = float(data["salePrice"])
        else:
            payload["salePrice"] = None

        assert_firestore_field_names(payload)
        return payload


class CategoryForm(forms.Form):
    documentId = forms.CharField(label="Document ID", required=False, max_length=120, widget=forms.HiddenInput)
    name = forms.CharField(label="Tên danh mục", max_length=255)
    image = forms.URLField(label="Image URL", required=False, max_length=1000)
    imageUpload = forms.ImageField(
        label="Upload ảnh mới",
        required=False,
        help_text="Nếu chọn file, hệ thống sẽ upload và thay thế Image URL.",
    )
    isFeatured = forms.BooleanField(label="Nổi bật", required=False)

    def __init__(self, *args: Any, initial: dict[str, Any] | None = None, is_create: bool = False, **kwargs: Any):
        data = dict(initial or {})
        data["documentId"] = data.get("id", "")
        super().__init__(*args, initial=data, **kwargs)
        self.is_create = is_create
        if not is_create:
            self.fields["documentId"].disabled = True

    def clean_documentId(self) -> str:
        document_id = (self.cleaned_data.get("documentId") or "").strip()
        if document_id and (any(char.isspace() for char in document_id) or "/" in document_id):
            raise forms.ValidationError("Document ID không được chứa khoảng trắng hoặc dấu /.")
        return document_id

    def apply_image_uploads(self, request: HttpRequest) -> None:
        image_upload = self.cleaned_data.get("imageUpload")
        if image_upload:
            self.cleaned_data["image"] = save_admin_image_upload(request, image_upload, folder="categories")

    def to_firestore_payload(self) -> dict[str, Any]:
        if not self.is_valid():
            raise ValueError("Cannot build Firestore payload from invalid form")
        payload = {
            "name": self.cleaned_data["name"].strip(),
            "image": (self.cleaned_data.get("image") or "").strip(),
            "isFeatured": bool(self.cleaned_data.get("isFeatured")),
        }
        assert_firestore_field_names(payload)
        return payload


class BrandForm(forms.Form):
    documentId = forms.CharField(label="Document ID", required=False, max_length=120, widget=forms.HiddenInput)
    name = forms.CharField(label="Tên NXB/Brand", max_length=255)
    imageUrl = forms.URLField(label="Image URL", required=False, max_length=1000)
    imageUpload = forms.ImageField(
        label="Upload ảnh mới",
        required=False,
        help_text="Nếu chọn file, hệ thống sẽ upload và thay thế Image URL.",
    )
    isFeatured = forms.BooleanField(label="Nổi bật", required=False)
    productsCount = forms.IntegerField(label="Số sản phẩm", min_value=0, initial=0)

    def __init__(self, *args: Any, initial: dict[str, Any] | None = None, is_create: bool = False, **kwargs: Any):
        data = dict(initial or {})
        data["documentId"] = data.get("id", "")
        super().__init__(*args, initial=data, **kwargs)
        self.is_create = is_create
        if not is_create:
            self.fields["documentId"].disabled = True

    def clean_documentId(self) -> str:
        document_id = (self.cleaned_data.get("documentId") or "").strip()
        if document_id and (any(char.isspace() for char in document_id) or "/" in document_id):
            raise forms.ValidationError("Document ID không được chứa khoảng trắng hoặc dấu /.")
        return document_id

    def apply_image_uploads(self, request: HttpRequest) -> None:
        image_upload = self.cleaned_data.get("imageUpload")
        if image_upload:
            self.cleaned_data["imageUrl"] = save_admin_image_upload(request, image_upload, folder="brands")

    def to_firestore_payload(self) -> dict[str, Any]:
        if not self.is_valid():
            raise ValueError("Cannot build Firestore payload from invalid form")
        payload = {
            "name": self.cleaned_data["name"].strip(),
            "imageUrl": (self.cleaned_data.get("imageUrl") or "").strip(),
            "isFeatured": bool(self.cleaned_data.get("isFeatured")),
            "productsCount": int(self.cleaned_data.get("productsCount") or 0),
        }
        assert_firestore_field_names(payload)
        return payload
