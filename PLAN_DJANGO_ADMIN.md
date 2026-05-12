# Kế hoạch triển khai Web Admin Book Store bằng Django + Django Admin + Unfold + Firestore trực tiếp

## 1. Mục tiêu

Xây dựng Web Admin quản lý hệ thống Book Store đã có sẵn trên app Flutter, dùng stack:

- Django
- Django Admin
- Django Unfold
- Firebase Admin SDK
- Cloud Firestore

Hướng triển khai được chọn: **Django + Unfold làm giao diện quản trị, Firestore là database nghiệp vụ chính, không tạo database trung gian cho Book Store**.

SQLite mặc định của Django chỉ dùng cho:

- Admin users
- Groups/permissions
- Sessions
- Audit log nội bộ nếu cần

Toàn bộ dữ liệu nghiệp vụ như sách, danh mục, thương hiệu, đơn hàng, khách hàng, coupon, review, notification sẽ được đọc/ghi trực tiếp từ Firestore để nhẹ, nhanh và tránh lỗi đồng bộ hai nguồn dữ liệu.

## 2. Lý do chọn Firestore trực tiếp

App Flutter hiện tại đã dùng Firebase/Firestore làm backend chính. Nếu tạo thêm Django ORM database rồi sync hai chiều sẽ phát sinh thêm độ phức tạp:

- Phải import/export dữ liệu.
- Dễ lệch schema giữa Django DB và Firestore.
- Dễ lỗi đồng bộ khi admin và app cùng ghi dữ liệu.
- Tốn thời gian xây mapper hai chiều.
- Không cần thiết cho MVP hoặc đồ án.

Với yêu cầu hiện tại, dùng Firestore trực tiếp hợp lý hơn vì:

- Dữ liệu chỉ có một nguồn sự thật.
- Admin chỉnh sửa xong app Flutter thấy ngay.
- Không cần sync hai chiều.
- Không cần PostgreSQL.
- Triển khai nhanh hơn.
- Phù hợp với kiến trúc Firebase hiện có.

## 3. Kiến trúc tổng thể

```text
Django Admin + Unfold
        |
        | Firebase Admin SDK
        v
Cloud Firestore
        ^
        |
Flutter Book Store App
```

### 3.1. Vai trò từng thành phần

| Thành phần | Vai trò |
|---|---|
| Django | Backend web admin, routing, auth admin, permission |
| Django Admin | Login admin, quản lý user/group/permission nội bộ |
| Unfold | Giao diện admin đẹp, dashboard, sidebar, layout |
| Firebase Admin SDK | Kết nối và thao tác Firestore/Auth |
| Firestore | Database nghiệp vụ chính của Book Store |
| SQLite | Chỉ lưu dữ liệu hệ thống Django, không lưu dữ liệu Book Store |

## 4. Phạm vi chức năng

### 4.1. Module cần xây dựng

1. Dashboard tổng quan
2. Quản lý sản phẩm sách
3. Quản lý danh mục sách
4. Quản lý thương hiệu/NXB
5. Quản lý coupon/mã giảm giá
6. Quản lý đơn hàng
7. Quản lý khách hàng
8. Quản lý địa chỉ khách hàng
9. Quản lý tài khoản ngân hàng khách hàng
10. Quản lý đánh giá sản phẩm
11. Quản lý thông báo
12. Quản lý admin user/group/permission
13. Audit log thao tác admin

### 4.2. Collection Firestore cần quản lý

| Collection/Subcollection | Chức năng |
|---|---|
| `books` | Sách/sản phẩm |
| `categories` | Danh mục sách |
| `brands` | Thương hiệu/NXB |
| `coupons` | Coupon/mã giảm giá |
| `orders` | Đơn hàng |
| `users` | Khách hàng/profile |
| `users/{uid}/addresses` | Địa chỉ khách hàng |
| `users/{uid}/bank_accounts` | Tài khoản ngân hàng đã lưu |
| `users/{uid}/cartItems` | Giỏ hàng, thường chỉ xem nếu cần |
| `users/{uid}/wishlistItems` | Wishlist, thường chỉ xem nếu cần |
| `reviews` | Đánh giá sản phẩm |
| `notifications` | Thông báo |

## 5. Cấu trúc project đề xuất

```text
6451071024_6451071008_MAP_WEB/
├── manage.py
├── requirements.txt
├── .env.example
├── README.md
├── service-account.json              # Không commit file thật
├── bookstore_admin/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── unfold.py
├── apps/
│   ├── core/
│   │   ├── permissions.py
│   │   ├── constants.py
│   │   └── utils.py
│   ├── firebase_client/
│   │   ├── client.py
│   │   ├── repositories.py
│   │   ├── serializers.py
│   │   └── validators.py
│   ├── dashboard/
│   │   ├── views.py
│   │   ├── services.py
│   │   └── urls.py
│   ├── catalog/
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── services.py
│   │   └── urls.py
│   ├── sales/
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── services.py
│   │   └── urls.py
│   ├── customers/
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── services.py
│   │   └── urls.py
│   ├── reviews/
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── services.py
│   │   └── urls.py
│   ├── notifications/
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── services.py
│   │   └── urls.py
│   └── audit/
│       ├── models.py
│       ├── admin.py
│       └── services.py
└── templates/
    └── admin_custom/
        ├── base.html
        ├── dashboard.html
        ├── list.html
        ├── form.html
        └── detail.html
```

## 6. Dependencies đề xuất

```txt
Django>=5.0
firebase-admin
python-dotenv
django-unfold
Pillow
whitenoise
gunicorn
```

Không cần các dependency sau trong MVP Firestore trực tiếp:

```txt
psycopg[binary]
django-import-export
django-filter
```

Chỉ thêm nếu sau này cần database SQL hoặc import/export nâng cao.

## 7. Cấu hình môi trường

File `.env.example`:

```env
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
FIREBASE_SERVICE_ACCOUNT_PATH=service-account.json
FIREBASE_PROJECT_ID=your-project-id
```

File `.gitignore` cần có:

```gitignore
.env
service-account.json
*.sqlite3
__pycache__/
staticfiles/
```

## 8. Cấu hình Django + Unfold

### 8.1. `INSTALLED_APPS`

```python
INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.firebase_client",
    "apps.dashboard",
    "apps.catalog",
    "apps.sales",
    "apps.customers",
    "apps.reviews",
    "apps.notifications",
    "apps.audit",
]
```

### 8.2. Database Django

Dùng SQLite mặc định:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

Lưu ý: SQLite chỉ phục vụ auth/session/audit, không lưu dữ liệu sách/đơn hàng/khách hàng.

### 8.3. Sidebar Unfold đề xuất

```python
UNFOLD = {
    "SITE_TITLE": "Book Store Admin",
    "SITE_HEADER": "Book Store Admin",
    "SITE_SUBHEADER": "Firestore Management",
    "SIDEBAR": {
        "show_search": True,
        "navigation": [
            {
                "title": "Dashboard",
                "items": [
                    {"title": "Tổng quan", "link": "/admin-dashboard/"},
                ],
            },
            {
                "title": "Catalog",
                "items": [
                    {"title": "Books", "link": "/admin-catalog/books/"},
                    {"title": "Categories", "link": "/admin-catalog/categories/"},
                    {"title": "Brands/NXB", "link": "/admin-catalog/brands/"},
                ],
            },
            {
                "title": "Sales",
                "items": [
                    {"title": "Orders", "link": "/admin-sales/orders/"},
                    {"title": "Coupons", "link": "/admin-sales/coupons/"},
                ],
            },
            {
                "title": "Customers",
                "items": [
                    {"title": "Customers", "link": "/admin-customers/"},
                ],
            },
            {
                "title": "Reviews & Notifications",
                "items": [
                    {"title": "Reviews", "link": "/admin-reviews/"},
                    {"title": "Notifications", "link": "/admin-notifications/"},
                ],
            },
        ]
    }
}
```

## 9. Firebase client layer

### 9.1. Client kết nối Firestore

File `apps/firebase_client/client.py`:

```python
import firebase_admin
from firebase_admin import credentials, firestore, auth
from django.conf import settings

_app = None
_db = None


def get_firebase_app():
    global _app
    if _app:
        return _app
    cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
    _app = firebase_admin.initialize_app(cred)
    return _app


def get_firestore_client():
    global _db
    if _db:
        return _db
    get_firebase_app()
    _db = firestore.client()
    return _db


def get_auth_client():
    get_firebase_app()
    return auth
```

### 9.2. Repository base

File `apps/firebase_client/repositories.py`:

```python
from google.cloud.firestore_v1 import FieldFilter
from .client import get_firestore_client


class FirestoreRepository:
    collection_name = None

    def __init__(self):
        self.db = get_firestore_client()
        self.collection = self.db.collection(self.collection_name)

    def list(self, limit=50, order_by=None, direction="DESCENDING"):
        query = self.collection
        if order_by:
            query = query.order_by(order_by, direction=direction)
        docs = query.limit(limit).stream()
        return [self._with_id(doc) for doc in docs]

    def get(self, document_id):
        doc = self.collection.document(document_id).get()
        if not doc.exists:
            return None
        return self._with_id(doc)

    def create(self, data, document_id=None):
        if document_id:
            ref = self.collection.document(document_id)
            ref.set(data)
            return document_id
        ref = self.collection.document()
        ref.set({**data, "id": ref.id})
        return ref.id

    def update(self, document_id, data):
        self.collection.document(document_id).update(data)

    def soft_delete(self, document_id):
        self.update(document_id, {"isDeleted": True})

    def _with_id(self, doc):
        data = doc.to_dict() or {}
        data["id"] = data.get("id") or doc.id
        data["_doc_id"] = doc.id
        return data
```

### 9.3. Repository theo collection

```python
class BookRepository(FirestoreRepository):
    collection_name = "books"


class CategoryRepository(FirestoreRepository):
    collection_name = "categories"


class BrandRepository(FirestoreRepository):
    collection_name = "brands"


class CouponRepository(FirestoreRepository):
    collection_name = "coupons"


class OrderRepository(FirestoreRepository):
    collection_name = "orders"


class UserRepository(FirestoreRepository):
    collection_name = "users"


class ReviewRepository(FirestoreRepository):
    collection_name = "reviews"


class NotificationRepository(FirestoreRepository):
    collection_name = "notifications"
```

## 10. Forms thay cho Django models nghiệp vụ

Vì không dùng Django ORM cho dữ liệu Book Store, mỗi module cần dùng Django Form để validate dữ liệu trước khi ghi Firestore.

### 10.1. Book form

```python
from django import forms


class BookForm(forms.Form):
    title = forms.CharField(max_length=255)
    author = forms.CharField(max_length=255, required=False)
    publisher = forms.CharField(max_length=255, required=False)
    genre = forms.CharField(max_length=255, required=False)
    pages = forms.IntegerField(min_value=0, required=False)
    price = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2)
    salePrice = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, required=False)
    stock = forms.IntegerField(min_value=0)
    coverImage = forms.URLField(required=False)
    description = forms.CharField(widget=forms.Textarea, required=False)
    availableFormats = forms.MultipleChoiceField(
        choices=[
            ("paperback", "Paperback"),
            ("hardcover", "Hardcover"),
            ("ebook", "Ebook"),
        ],
        required=False,
    )
    isActive = forms.BooleanField(required=False)
    isDeleted = forms.BooleanField(required=False)

    def clean(self):
        cleaned = super().clean()
        price = cleaned.get("price")
        sale_price = cleaned.get("salePrice")
        if price is not None and sale_price is not None and sale_price > price:
            raise forms.ValidationError("Giá sale không được lớn hơn giá gốc.")
        return cleaned
```

### 10.2. Coupon form

```python
class CouponForm(forms.Form):
    code = forms.CharField(max_length=50)
    type = forms.ChoiceField(
        choices=[
            ("percent", "Percent"),
            ("fixed", "Fixed"),
            ("freeShipping", "Free Shipping"),
        ]
    )
    value = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2)
    minSubtotal = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, required=False)
    maxDiscount = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, required=False)
    isActive = forms.BooleanField(required=False)

    def clean(self):
        cleaned = super().clean()
        coupon_type = cleaned.get("type")
        value = cleaned.get("value")
        if coupon_type == "percent" and value and value > 100:
            raise forms.ValidationError("Coupon phần trăm không được vượt quá 100%.")
        return cleaned
```

### 10.3. Order status form

```python
class OrderStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("shipping", "Shipping"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ]
    )
```

## 11. Custom admin views

Dữ liệu nghiệp vụ không dùng `ModelAdmin` mặc định. Thay vào đó tạo custom views được bảo vệ bằng `staff_member_required` và render bằng template Unfold/Django Admin.

### 11.1. URL tổng thể

```python
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin-dashboard/", include("apps.dashboard.urls")),
    path("admin-catalog/", include("apps.catalog.urls")),
    path("admin-sales/", include("apps.sales.urls")),
    path("admin-customers/", include("apps.customers.urls")),
    path("admin-reviews/", include("apps.reviews.urls")),
    path("admin-notifications/", include("apps.notifications.urls")),
]
```

### 11.2. Pattern URL từng module

Ví dụ catalog:

```python
urlpatterns = [
    path("books/", book_list, name="admin_book_list"),
    path("books/create/", book_create, name="admin_book_create"),
    path("books/<str:book_id>/", book_detail, name="admin_book_detail"),
    path("books/<str:book_id>/edit/", book_edit, name="admin_book_edit"),
    path("books/<str:book_id>/delete/", book_soft_delete, name="admin_book_delete"),
    path("categories/", category_list, name="admin_category_list"),
    path("brands/", brand_list, name="admin_brand_list"),
]
```

### 11.3. View list mẫu

```python
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from apps.firebase_client.repositories import BookRepository


@staff_member_required
def book_list(request):
    repo = BookRepository()
    books = repo.list(limit=100, order_by="title", direction="ASCENDING")
    return render(request, "admin_custom/catalog/book_list.html", {"books": books})
```

### 11.4. View edit mẫu

```python
from django.contrib import messages
from django.shortcuts import redirect
from apps.catalog.forms import BookForm


@staff_member_required
def book_edit(request, book_id):
    repo = BookRepository()
    book = repo.get(book_id)
    if not book:
        messages.error(request, "Không tìm thấy sách.")
        return redirect("admin_book_list")

    if request.method == "POST":
        form = BookForm(request.POST, initial=book)
        if form.is_valid():
            data = form.cleaned_data
            data["isOutOfStock"] = data.get("stock", 0) <= 0
            repo.update(book_id, data)
            messages.success(request, "Đã cập nhật sách lên Firestore.")
            return redirect("admin_book_detail", book_id=book_id)
    else:
        form = BookForm(initial=book)

    return render(request, "admin_custom/catalog/book_form.html", {"form": form, "book": book})
```

## 12. Quy tắc dữ liệu Firestore

### 12.1. Không đổi tên field app đang dùng

App Flutter đang dùng camelCase. Admin phải ghi đúng camelCase khi lưu Firestore.

Ví dụ Book phải giữ:

```json
{
  "title": "Tên sách",
  "coverImage": "https://...",
  "salePrice": 120000,
  "soldQuantity": 10,
  "ratingCount": 5,
  "isOutOfStock": false,
  "isActive": true,
  "isDeleted": false,
  "categoryIds": ["cat01"],
  "brandId": "brand01",
  "brandName": "NXB Trẻ"
}
```

### 12.2. Chuẩn status đơn hàng

Admin phải dùng đúng status app hiện tại:

```text
pending
processing
shipping
delivered
cancelled
```

Không dùng:

```text
shipped
canceled
```

### 12.3. Chuẩn coupon type

Admin nên ghi Firestore theo ba type chính:

```text
percent
fixed
freeShipping
```

Khi đọc dữ liệu cũ, có thể map alias:

```text
percentage -> percent
free_shipping -> freeShipping
```

### 12.4. Soft delete

Không xóa cứng mặc định.

- Book: ẩn bằng `isDeleted = true`.
- Review: ẩn bằng `isDeleted = true`.
- Coupon: vô hiệu bằng `isActive = false`.
- Category/Brand: nếu app chưa có `isActive`, cần cân nhắc trước khi thêm field mới.

## 13. Module Catalog

### 13.1. Books

Chức năng:

- Danh sách sách.
- Tìm kiếm theo title, author, publisher, genre.
- Lọc theo active/deleted/out of stock.
- Xem chi tiết sách.
- Thêm sách mới.
- Sửa sách.
- Ẩn/khôi phục sách.
- Cập nhật stock.
- Cập nhật sale price.
- Cập nhật hình ảnh URL.
- Cập nhật danh mục và brand.

Field cần hiển thị:

- Ảnh bìa.
- Tên sách.
- Tác giả.
- NXB.
- Giá gốc.
- Giá sale.
- Tồn kho.
- Đã bán.
- Rating.
- Trạng thái active/deleted/out of stock.

Firestore action:

- `books/{bookId}.update({...})`
- `books/{bookId}.set({...})`

### 13.2. Categories

Chức năng:

- Danh sách danh mục.
- Thêm/sửa danh mục.
- Bật/tắt featured.
- Cập nhật ảnh.

Field:

- `id`
- `name`
- `image`
- `isFeatured`

### 13.3. Brands/NXB

Chức năng:

- Danh sách brand/NXB.
- Thêm/sửa brand.
- Bật/tắt featured.
- Cập nhật ảnh.
- Tính lại `productsCount` nếu cần.

Field:

- `id`
- `name`
- `imageUrl`
- `isFeatured`
- `productsCount`

## 14. Module Sales

### 14.1. Orders

Chức năng:

- Danh sách đơn hàng.
- Tìm kiếm theo orderCode, recipientName, phoneNumber.
- Lọc theo status, paymentMethod, ngày tạo.
- Xem chi tiết đơn.
- Xem danh sách items trong đơn.
- Cập nhật trạng thái đơn.
- Hủy đơn.

Workflow:

```text
pending -> processing -> shipping -> delivered
pending -> cancelled
processing -> cancelled
```

Field chính:

- `orderCode`
- `userId`
- `recipientName`
- `phoneNumber`
- `address`
- `note`
- `subtotal`
- `shippingFee`
- `discountAmount`
- `couponCode`
- `total`
- `totalItems`
- `items`
- `createdAt`
- `status`
- `paymentMethod`

Khi update status:

```python
order_ref.update({"status": new_status})
```

Có thể tạo thêm notification:

```python
notifications_ref.document().set({
    "userId": order["userId"],
    "orderId": order_id,
    "orderStatus": new_status,
    "message": "Đơn hàng của bạn đã được cập nhật trạng thái.",
    "isRead": False,
    "createdAt": firestore.SERVER_TIMESTAMP,
})
```

### 14.2. Coupons

Chức năng:

- Danh sách coupon.
- Tạo coupon.
- Sửa coupon.
- Kích hoạt/vô hiệu hóa coupon.
- Validate giá trị coupon.

Field:

- `code`
- `type`
- `value`
- `minSubtotal`
- `maxDiscount`
- `isActive`

## 15. Module Customers

### 15.1. Customers

Chức năng:

- Danh sách khách hàng từ collection `users`.
- Tìm kiếm theo name/email/phone/username.
- Xem chi tiết khách hàng.
- Xem lịch sử đơn hàng của khách.
- Xem địa chỉ.
- Xem bank accounts nếu có quyền.

Field:

- `id`
- `firstName`
- `lastName`
- `username`
- `email`
- `phone`
- `emailVerified`

Lưu ý:

- Không quản lý password ở Firestore.
- Password/user auth nằm trong Firebase Authentication.
- Nếu cần disable user, dùng Firebase Auth SDK.

### 15.2. Addresses

Path:

```text
users/{uid}/addresses/{addressId}
```

Chức năng:

- Xem danh sách địa chỉ theo customer.
- Thêm/sửa/xóa địa chỉ nếu cần.
- Đảm bảo chỉ một default address.

Field:

- `city`
- `ward`
- `street`
- `number`
- `receiverName`
- `phoneNumber`
- `isDefault`
- `latitude`
- `longitude`

### 15.3. Bank accounts

Path:

```text
users/{uid}/bank_accounts/{bankAccountId}
```

Chức năng:

- Xem danh sách tài khoản ngân hàng.
- Mask số tài khoản ở list view.
- Chỉ super admin/customer support được xem chi tiết.

Field:

- `accountNumber`
- `accountHolderName`
- `bankName`
- `shortName`
- `bankCode`
- `bin`
- `logo`

## 16. Module Reviews

Chức năng:

- Danh sách reviews.
- Tìm kiếm theo userName/comment.
- Lọc theo rating/isDeleted.
- Xem chi tiết review.
- Ẩn review.
- Khôi phục review.

Field:

- `userId`
- `userName`
- `productId`
- `orderId`
- `rating`
- `title`
- `comment`
- `imageUrls`
- `createdAt`
- `isDeleted`

Action:

```python
reviews_ref.document(review_id).update({"isDeleted": True})
```

Nếu cần cập nhật lại rating sách:

1. Query tất cả review của `productId` có `isDeleted == false`.
2. Tính trung bình rating.
3. Update `books/{productId}`:

```python
book_ref.update({
    "rating": avg_rating,
    "ratingCount": rating_count,
})
```

## 17. Module Notifications

Chức năng:

- Danh sách notifications.
- Tạo notification cho một user.
- Tạo notification theo order.
- Đánh dấu đã đọc/chưa đọc nếu cần.
- Gửi notification hàng loạt nếu mở rộng.

Field:

- `userId`
- `orderId`
- `orderStatus`
- `message`
- `isRead`
- `createdAt`

## 18. Dashboard

Dashboard đọc trực tiếp Firestore và tính số liệu runtime.

### 18.1. KPI

- Tổng doanh thu đơn `delivered`.
- Doanh thu tháng hiện tại.
- Tổng đơn hàng.
- Số đơn `pending`.
- Số đơn `processing`.
- Số đơn `shipping`.
- Số đơn `delivered`.
- Số đơn `cancelled`.
- Giá trị đơn hàng trung bình.
- Tổng số sách.
- Số sách sắp hết hàng.
- Tổng khách hàng.
- Tổng review.
- Rating trung bình.

### 18.2. Cách tính

Với dữ liệu nhỏ/demo, có thể stream collection rồi tính bằng Python:

```python
orders = list(db.collection("orders").stream())
books = list(db.collection("books").stream())
users = list(db.collection("users").stream())
reviews = list(db.collection("reviews").stream())
```

Với dữ liệu lớn, cần tối ưu:

- Query theo ngày.
- Dùng Firestore aggregate count nếu phù hợp.
- Lưu collection `admin_stats` để cache số liệu.
- Dùng scheduled job cập nhật thống kê.

### 18.3. Bảng nhanh

- Đơn hàng mới nhất.
- Sách tồn kho thấp.
- Review mới nhất.
- Coupon đang hoạt động.

## 19. Permission và bảo mật

### 19.1. Role đề xuất

| Role | Quyền |
|---|---|
| Super Admin | Toàn quyền |
| Catalog Manager | Quản lý sách, danh mục, brand |
| Sales Staff | Quản lý đơn hàng, coupon |
| Customer Support | Xem khách hàng, địa chỉ, đơn hàng |
| Moderator | Quản lý review |
| Viewer | Chỉ xem dashboard/list |

### 19.2. Cách kiểm tra quyền trong custom view

```python
from django.contrib.auth.decorators import permission_required


@staff_member_required
@permission_required("core.manage_books", raise_exception=True)
def book_list(request):
    ...
```

Vì dữ liệu Firestore không có Django model permission tự động, cần tạo custom permissions trong app `core`.

Ví dụ:

```python
class PermissionAnchor(models.Model):
    class Meta:
        managed = False
        permissions = [
            ("manage_books", "Can manage books"),
            ("manage_orders", "Can manage orders"),
            ("manage_customers", "Can manage customers"),
            ("manage_reviews", "Can manage reviews"),
            ("manage_notifications", "Can manage notifications"),
        ]
```

## 20. Audit log nội bộ

Dù không lưu dữ liệu nghiệp vụ vào SQL, vẫn nên lưu audit log thao tác admin trong SQLite.

Model đề xuất:

```python
class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=50)
    collection = models.CharField(max_length=100)
    document_id = models.CharField(max_length=128, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

Ghi log khi:

- Tạo/sửa/ẩn/khôi phục sách.
- Cập nhật đơn hàng.
- Tạo/sửa coupon.
- Ẩn/khôi phục review.
- Tạo notification.
- Thao tác lỗi với Firestore.

## 21. Roadmap triển khai

### Giai đoạn 1: Khởi tạo Django + Unfold

Thời lượng: 0.5 ngày

Việc cần làm:

1. Tạo virtual environment.
2. Cài Django, Unfold, Firebase Admin SDK.
3. Tạo Django project.
4. Cấu hình `.env`.
5. Cấu hình SQLite mặc định.
6. Cấu hình Unfold.
7. Tạo superuser.
8. Login được `/admin/`.

Kết quả:

- Admin Django chạy được.
- Unfold hiển thị đúng.
- Có superuser.

### Giai đoạn 2: Firebase client + repository

Thời lượng: 0.5 - 1 ngày

Việc cần làm:

1. Tạo app `firebase_client`.
2. Cấu hình service account.
3. Tạo `get_firestore_client()`.
4. Tạo repository base.
5. Tạo repository cho từng collection.
6. Test đọc `books`, `categories`, `orders`.

Kết quả:

- Django đọc được Firestore trực tiếp.

### Giai đoạn 3: Custom admin layout/pages

Thời lượng: 1 ngày

Việc cần làm:

1. Tạo app dashboard/catalog/sales/customers/reviews/notifications.
2. Tạo URLs riêng cho từng module.
3. Tạo template base dùng style Unfold/admin.
4. Tạo list page mẫu.
5. Tạo form page mẫu.
6. Gắn sidebar Unfold.

Kết quả:

- Có khung giao diện admin cho dữ liệu Firestore.

### Giai đoạn 4: Catalog CRUD

Thời lượng: 1 - 2 ngày

Việc cần làm:

1. Books list/detail/create/edit/soft delete/restore.
2. Categories list/create/edit.
3. Brands list/create/edit.
4. Validate dữ liệu sách.
5. Ghi audit log.

Kết quả:

- Quản lý được sách, danh mục, brand trực tiếp trên Firestore.

### Giai đoạn 5: Sales CRUD

Thời lượng: 1 - 2 ngày

Việc cần làm:

1. Orders list/detail.
2. Update order status.
3. Validate workflow trạng thái đơn.
4. Coupons list/create/edit/disable.
5. Tùy chọn tạo notification khi order đổi status.
6. Ghi audit log.

Kết quả:

- Quản lý được đơn hàng và coupon.
- App Flutter nhận thay đổi ngay.

### Giai đoạn 6: Customers, Reviews, Notifications

Thời lượng: 1 - 2 ngày

Việc cần làm:

1. Customers list/detail.
2. Xem addresses subcollection.
3. Xem bank accounts subcollection.
4. Reviews list/detail/hide/restore.
5. Notifications list/create.
6. Ghi audit log.

Kết quả:

- Quản lý được khách hàng, review, notification.

### Giai đoạn 7: Dashboard + Permission + Test

Thời lượng: 1 - 2 ngày

Việc cần làm:

1. Dashboard KPI.
2. Bảng đơn mới, sách sắp hết hàng, review mới.
3. Tạo custom permissions.
4. Tạo groups.
5. Gán quyền.
6. Test toàn bộ luồng.
7. Viết README hướng dẫn chạy.

Kết quả:

- Web Admin hoàn chỉnh ở mức MVP.

## 22. MVP checklist

### Setup

- [ ] Tạo Django project.
- [ ] Cài Django Unfold.
- [ ] Cài Firebase Admin SDK.
- [ ] Cấu hình `.env`.
- [ ] Cấu hình service account.
- [ ] Tạo superuser.
- [ ] Login được admin.

### Firebase

- [ ] Kết nối Firestore thành công.
- [ ] Đọc được collection `books`.
- [ ] Đọc được collection `orders`.
- [ ] Ghi thử một document test hoặc update field test.
- [ ] Xóa document test nếu có.

### Catalog

- [ ] Books list.
- [ ] Book detail.
- [ ] Book create.
- [ ] Book edit.
- [ ] Book soft delete/restore.
- [ ] Categories list/create/edit.
- [ ] Brands list/create/edit.

### Sales

- [ ] Orders list.
- [ ] Order detail.
- [ ] Update order status.
- [ ] Coupons list.
- [ ] Coupon create/edit.
- [ ] Coupon enable/disable.

### Customers

- [ ] Customers list.
- [ ] Customer detail.
- [ ] Customer orders.
- [ ] Customer addresses.
- [ ] Customer bank accounts với quyền phù hợp.

### Reviews/Notifications

- [ ] Reviews list.
- [ ] Review detail.
- [ ] Hide review.
- [ ] Restore review.
- [ ] Notifications list.
- [ ] Create notification.

### Dashboard/Permission

- [ ] Dashboard KPI.
- [ ] Recent orders.
- [ ] Low stock books.
- [ ] Groups/permissions.
- [ ] Audit log.

## 23. Rủi ro và cách xử lý

### 23.1. Django Admin không dùng được ModelAdmin cho Firestore

Rủi ro:

- Không có ORM model nên không dùng được `ModelAdmin` chuẩn cho books/orders.

Cách xử lý:

- Dùng Django Admin chỉ cho auth, group, permission, audit.
- Dùng Unfold + custom views cho dữ liệu Firestore.
- Giao diện vẫn nằm trong admin shell/sidebar.

### 23.2. Firestore query hạn chế hơn SQL

Rủi ro:

- Search contains/full-text khó làm trực tiếp.
- Query nhiều điều kiện cần composite index.

Cách xử lý:

- MVP dùng search/filter phía Python sau khi lấy giới hạn dữ liệu.
- Với dữ liệu lớn, thêm field search keywords.
- Tạo Firestore composite index cho query thường dùng.
- Nếu cần full-text search thật, tích hợp Algolia/Meilisearch sau.

### 23.3. Dashboard chậm khi dữ liệu lớn

Rủi ro:

- Stream toàn bộ orders/books/users sẽ chậm nếu dữ liệu lớn.

Cách xử lý:

- MVP chấp nhận tính runtime.
- Sau đó tạo collection `admin_stats` để cache KPI.
- Dùng scheduled job hoặc Cloud Function cập nhật thống kê.

### 23.4. Ghi sai schema app

Rủi ro:

- App Flutter đọc field camelCase, nếu admin ghi snake_case sẽ lỗi.

Cách xử lý:

- Forms và services dùng đúng field camelCase.
- Tạo constants cho field names.
- Test sau mỗi thao tác bằng app.

### 23.5. Bảo mật service account

Rủi ro:

- Lộ `service-account.json` có thể làm mất quyền kiểm soát Firebase.

Cách xử lý:

- Không commit service account.
- Dùng `.env` hoặc secret manager khi deploy.
- Giới hạn quyền service account nếu có thể.

## 24. Tiêu chí hoàn thành

Hệ thống hoàn thành khi:

1. Admin login được bằng Django Admin.
2. Giao diện Unfold có sidebar các module.
3. Django đọc được Firestore trực tiếp.
4. Quản lý được books/categories/brands.
5. Quản lý được coupons.
6. Xem và cập nhật được orders.
7. Xem được customers, addresses, bank accounts.
8. Ẩn/khôi phục được reviews.
9. Tạo/xem được notifications.
10. Dashboard hiển thị KPI chính.
11. App Flutter nhận thay đổi ngay sau khi admin cập nhật Firestore.
12. Có role/permission cơ bản.
13. Có audit log thao tác quan trọng.
14. Có README hướng dẫn setup, cấu hình Firebase và chạy project.

## 25. Thứ tự ưu tiên triển khai

1. Setup Django + Unfold.
2. Kết nối Firebase Admin SDK.
3. Tạo repository đọc/ghi Firestore.
4. Tạo custom admin layout/sidebar.
5. Làm Books CRUD.
6. Làm Categories/Brands CRUD.
7. Làm Orders list/detail/update status.
8. Làm Coupons CRUD.
9. Làm Customers detail/subcollections.
10. Làm Reviews hide/restore.
11. Làm Notifications.
12. Làm Dashboard.
13. Thêm permission và audit log.
14. Test với app Flutter.
15. Viết README/deploy guide.

## 26. Kết luận

Phương án dùng Firestore trực tiếp là phù hợp nhất cho mục tiêu nhẹ, nhanh và ít rủi ro đồng bộ. Django vẫn đảm nhiệm phần admin shell, xác thực, phân quyền và layout bằng Unfold; còn toàn bộ dữ liệu Book Store được đọc/ghi trực tiếp vào Firestore bằng Firebase Admin SDK.

Cách này giúp giữ app Flutter hiện tại hoạt động nguyên trạng, giảm thời gian triển khai, tránh PostgreSQL và tránh sync hai chiều. Khi hệ thống lớn hơn, có thể bổ sung cache thống kê, search service hoặc database phân tích riêng mà không ảnh hưởng MVP.
