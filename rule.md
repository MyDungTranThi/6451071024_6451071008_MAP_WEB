# RULE.md - Quy tắc nghiêm ngặt cho Agent khi triển khai Web Admin Book Store

## 1. Mục tiêu bắt buộc

Agent phải triển khai Web Admin Book Store theo đúng plan trong `PLAN_DJANGO_ADMIN.md`.

Stack bắt buộc:

- Django
- Django Admin
- Django Unfold
- Firebase Admin SDK
- Cloud Firestore trực tiếp
- SQLite chỉ cho dữ liệu hệ thống Django

Không được tự ý đổi hướng kiến trúc sang Django ORM database trung gian cho dữ liệu Book Store nếu chưa được user yêu cầu rõ ràng.

## 2. Kiến trúc bắt buộc

### 2.1. Firestore là nguồn dữ liệu nghiệp vụ duy nhất

Toàn bộ dữ liệu nghiệp vụ phải đọc/ghi trực tiếp từ Cloud Firestore:

- `books`
- `categories`
- `brands`
- `coupons`
- `orders`
- `users`
- `users/{uid}/addresses`
- `users/{uid}/bank_accounts`
- `users/{uid}/cartItems`
- `users/{uid}/wishlistItems`
- `reviews`
- `notifications`

### 2.2. Không tạo database trung gian cho Book Store

Không được tạo Django ORM models cho dữ liệu nghiệp vụ chính như:

- Book
- Category
- Brand
- Coupon
- Order
- OrderItem
- Customer
- CustomerAddress
- BankAccount
- Review
- Notification

Ngoại lệ được phép tạo Django ORM model:

- Admin users mặc định của Django
- Groups/permissions mặc định của Django
- Sessions mặc định của Django
- AuditLog nội bộ
- Permission anchor model không managed nếu cần custom permissions

### 2.3. Không sync hai chiều

Không được triển khai cơ chế import/export/sync hai chiều giữa Django DB và Firestore cho dữ liệu nghiệp vụ.

Mọi thao tác CRUD nghiệp vụ phải gọi Firebase Admin SDK và ghi trực tiếp vào Firestore.

## 3. Quy tắc bảo toàn schema Firestore

### 3.1. Không đổi tên collection

Không được đổi tên hoặc tạo collection thay thế nếu app Flutter đang dùng collection có sẵn.

Ví dụ bắt buộc:

- Dùng `books`, không dùng `products`.
- Dùng `users`, không dùng `customers`.
- Dùng `reviews`, không dùng `product_reviews`.
- Dùng `bank_accounts`, không dùng `bankAccounts`.

### 3.2. Không đổi tên field app đang dùng

App Flutter đang dùng camelCase. Khi ghi Firestore phải giữ đúng field name.

Ví dụ Book bắt buộc dùng:

- `title`
- `author`
- `publisher`
- `genre`
- `pages`
- `price`
- `coverImage`
- `availableFormats`
- `description`
- `salePrice`
- `stock`
- `soldQuantity`
- `rating`
- `ratingCount`
- `isOutOfStock`
- `isActive`
- `isDeleted`
- `tags`
- `images`
- `categoryIds`
- `brandId`
- `brandName`

Không được ghi các field snake_case như:

- `cover_image`
- `sale_price`
- `sold_quantity`
- `rating_count`
- `is_out_of_stock`
- `is_active`
- `is_deleted`
- `category_ids`
- `brand_id`
- `brand_name`

### 3.3. Field nội bộ không được ghi bừa vào Firestore

Không được tự ý thêm field nội bộ như:

- `created_by`
- `updated_by`
- `sync_status`
- `django_id`
- `local_id`
- `admin_note`

Nếu cần field mới, phải có lý do rõ ràng và đảm bảo app Flutter không bị ảnh hưởng.

## 4. Quy tắc status và enum

### 4.1. Order status bắt buộc

Chỉ dùng các status app hiện tại đang hỗ trợ:

```text
pending
processing
shipping
delivered
cancelled
```

Không được dùng:

```text
created
shipped
canceled
returned
refunded
complete
completed
```

Trừ khi user yêu cầu cập nhật cả app Flutter để hỗ trợ status mới.

### 4.2. Workflow đơn hàng bắt buộc

Workflow chuẩn:

```text
pending -> processing -> shipping -> delivered
pending -> cancelled
processing -> cancelled
```

Không được cho phép:

- `delivered` chuyển về trạng thái trước đó, trừ superuser.
- `cancelled` chuyển sang trạng thái khác, trừ superuser.
- `shipping` chuyển về `pending`.

### 4.3. Coupon type bắt buộc

Khi ghi Firestore, chỉ dùng:

```text
percent
fixed
freeShipping
```

Khi đọc dữ liệu cũ, được phép map alias:

```text
percentage -> percent
free_shipping -> freeShipping
```

Không được tạo coupon type mới nếu app Flutter chưa hỗ trợ.

### 4.4. Book format bắt buộc

Chỉ dùng các format app hiện tại đang hỗ trợ:

```text
paperback
hardcover
ebook
```

Không được dùng label tiếng Việt làm giá trị lưu Firestore.

## 5. Quy tắc CRUD dữ liệu

### 5.1. Không hard delete mặc định

Không được xóa cứng dữ liệu quan trọng mặc định.

Phải dùng soft delete hoặc disable:

- Book: set `isDeleted = true`.
- Review: set `isDeleted = true`.
- Coupon: set `isActive = false`.
- Category/Brand: nếu app chưa có `isActive`, không tự ý thêm/xóa nếu chưa kiểm tra tác động.

### 5.2. Khi tạo document mới

Khi tạo document Firestore mới, phải đảm bảo:

- Có document id hợp lệ.
- Field `id` trong document phải khớp document id nếu app đang dùng field `id`.
- Không thiếu các field bắt buộc app cần đọc.
- Dữ liệu số là số, không lưu thành string.
- Timestamp dùng Firestore timestamp khi phù hợp.

Ví dụ tạo document:

```python
ref = db.collection("books").document()
ref.set({
    "id": ref.id,
    "title": title,
    "price": price,
    "isActive": True,
    "isDeleted": False,
})
```

### 5.3. Khi update document

Khi update document:

- Chỉ update field cần thay đổi.
- Không overwrite toàn bộ document nếu không cần.
- Không làm mất field app đang dùng.
- Phải validate form trước khi update.
- Phải ghi AuditLog nếu là thao tác quan trọng.

Ưu tiên:

```python
ref.update({"status": new_status})
```

Tránh:

```python
ref.set(data)
```

Trừ khi đang tạo mới hoặc đã merge rõ ràng.

## 6. Quy tắc Django project structure

### 6.1. Cấu trúc app bắt buộc

Ưu tiên tổ chức theo plan:

```text
apps/
├── core/
├── firebase_client/
├── dashboard/
├── catalog/
├── sales/
├── customers/
├── reviews/
├── notifications/
└── audit/
```

### 6.2. Service/repository pattern bắt buộc

Không được gọi Firestore trực tiếp rải rác trong template hoặc nhiều view.

Phải gom logic Firestore vào:

- `apps/firebase_client/client.py`
- `apps/firebase_client/repositories.py`
- service riêng của từng module nếu cần

View chỉ nên:

1. Nhận request.
2. Kiểm tra permission.
3. Gọi form validate.
4. Gọi service/repository.
5. Render template hoặc redirect.

### 6.3. Không để business logic trong template

Template chỉ hiển thị dữ liệu.

Không được đặt logic nghiệp vụ trong template như:

- Tính workflow order phức tạp.
- Tính rating trung bình.
- Validate coupon.
- Query Firestore.

## 7. Quy tắc Firebase Admin SDK

### 7.1. Khởi tạo Firebase duy nhất

Phải đảm bảo Firebase app chỉ initialize một lần.

Bắt buộc dùng helper kiểu:

```python
_app = None
_db = None


def get_firebase_app():
    global _app
    if _app:
        return _app
    cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
    _app = firebase_admin.initialize_app(cred)
    return _app
```

Không được gọi `firebase_admin.initialize_app()` ở nhiều nơi.

### 7.2. Không hardcode credentials

Không được hardcode:

- Firebase project id
- Service account path tuyệt đối cá nhân
- Private key
- Client email
- API key

Phải đọc từ settings hoặc environment variables.

### 7.3. Không commit service account

File thật `service-account.json` không được commit.

`.gitignore` phải có:

```gitignore
.env
service-account.json
*.sqlite3
```

## 8. Quy tắc forms và validation

### 8.1. Bắt buộc dùng Django Form

Vì dữ liệu nghiệp vụ không dùng Django ORM, mọi create/update phải đi qua Django Form.

Không được ghi `request.POST` trực tiếp vào Firestore.

Sai:

```python
repo.update(book_id, request.POST)
```

Đúng:

```python
form = BookForm(request.POST)
if form.is_valid():
    repo.update(book_id, form.cleaned_data)
```

### 8.2. Validation Book

Bắt buộc kiểm tra:

- `title` không rỗng.
- `price >= 0`.
- `salePrice >= 0` nếu có.
- `salePrice <= price` nếu có.
- `stock >= 0`.
- `pages >= 0`.
- `rating` trong khoảng 0-5 nếu cho sửa.
- `availableFormats` chỉ gồm `paperback`, `hardcover`, `ebook`.

### 8.3. Validation Coupon

Bắt buộc kiểm tra:

- `code` không rỗng.
- `type` thuộc `percent`, `fixed`, `freeShipping`.
- `value >= 0`.
- Nếu `type = percent`, `value <= 100`.
- `minSubtotal >= 0`.
- `maxDiscount >= 0` nếu có.

### 8.4. Validation Order

Bắt buộc kiểm tra:

- Status mới thuộc danh sách cho phép.
- Status transition hợp lệ.
- Không hủy đơn đã `delivered`.
- Không chuyển đơn `cancelled` nếu không phải superuser.

## 9. Quy tắc permission và bảo mật

### 9.1. Mọi custom view phải bảo vệ bằng staff login

Tất cả views admin tùy chỉnh phải có:

```python
@staff_member_required
```

Không được để view quản trị public.

### 9.2. View ghi dữ liệu phải có permission

Các view create/update/delete/action phải có permission cụ thể.

Ví dụ:

```python
@permission_required("core.manage_books", raise_exception=True)
```

### 9.3. Không hiển thị dữ liệu nhạy cảm bừa bãi

Bank account phải được mask ở list view.

Ví dụ:

```text
**** **** **** 1234
```

Chỉ user có quyền phù hợp mới được xem đầy đủ.

### 9.4. Không log dữ liệu nhạy cảm không cần thiết

AuditLog không nên lưu toàn bộ thông tin nhạy cảm như:

- Full bank account number
- Private credential
- Token
- Password

## 10. Quy tắc AuditLog

### 10.1. Bắt buộc log thao tác quan trọng

Phải ghi audit log cho:

- Tạo/sửa/ẩn/khôi phục Book.
- Tạo/sửa Category.
- Tạo/sửa Brand.
- Tạo/sửa/vô hiệu Coupon.
- Cập nhật Order status.
- Ẩn/khôi phục Review.
- Tạo Notification.
- Lỗi ghi Firestore.

### 10.2. Nội dung log tối thiểu

AuditLog phải có:

- Actor/admin user.
- Action.
- Collection.
- Document id.
- Before nếu có.
- After nếu có.
- Success/failure.
- Message.
- Timestamp.

## 11. Quy tắc UI/UX Admin

### 11.1. Dùng Unfold layout

Custom pages phải nằm trong layout admin/Unfold, không tạo giao diện rời rạc.

### 11.2. List page bắt buộc có

Mỗi list page cần có:

- Tiêu đề rõ ràng.
- Search nếu phù hợp.
- Filter nếu phù hợp.
- Pagination hoặc limit.
- Link detail/edit.
- Empty state.
- Thông báo lỗi nếu Firestore lỗi.

### 11.3. Form page bắt buộc có

Mỗi form page cần có:

- Hiển thị lỗi validation.
- Nút lưu.
- Nút quay lại.
- Confirm với thao tác nguy hiểm.

### 11.4. Action nguy hiểm phải xác nhận

Các thao tác sau phải có confirm:

- Hide/delete/restore.
- Cancel order.
- Disable coupon.
- Hide review.

## 12. Quy tắc Dashboard

### 12.1. MVP dashboard được tính runtime

Với dữ liệu nhỏ/demo, được phép đọc Firestore rồi tính bằng Python.

### 12.2. Không query vô hạn nếu không cần

Các list page phải có limit/pagination.

Không được stream toàn bộ collection lớn trong list page nếu không có lý do.

### 12.3. Tối ưu khi dữ liệu lớn

Nếu dashboard chậm, phải chuyển sang:

- Firestore aggregate count.
- Query theo khoảng ngày.
- Cache collection `admin_stats`.
- Scheduled job/Cloud Function.

## 13. Quy tắc search/filter Firestore

### 13.1. MVP search

Với MVP, được phép:

- Query limit Firestore.
- Filter/search phía Python trên dữ liệu đã lấy.

### 13.2. Không giả vờ Firestore có full-text search

Firestore không hỗ trợ contains/full-text search tốt như SQL.

Nếu cần search lớn, phải đề xuất:

- Search keywords field.
- Algolia.
- Meilisearch.
- Typesense.

### 13.3. Composite index

Nếu Firestore báo thiếu index, phải ghi lại query và tạo composite index tương ứng.

## 14. Quy tắc test

### 14.1. Test tối thiểu sau mỗi module

Sau khi làm xong module, phải test:

- List page load được.
- Detail page load được.
- Create nếu có.
- Edit nếu có.
- Action nếu có.
- Firestore data thay đổi đúng field.
- App Flutter không bị vỡ schema.

### 14.2. Test với dữ liệu thật cẩn thận

Không được xóa dữ liệu thật trong Firestore khi test.

Nếu cần test destructive action:

- Tạo document test riêng.
- Xóa/ẩn document test.
- Không thao tác trên dữ liệu thật nếu chưa chắc chắn.

## 15. Quy tắc triển khai theo thứ tự

Agent phải ưu tiên triển khai theo thứ tự:

1. Setup Django + Unfold.
2. Cấu hình `.env` và `.gitignore`.
3. Kết nối Firebase Admin SDK.
4. Tạo repository base Firestore.
5. Tạo AuditLog.
6. Tạo custom permissions.
7. Tạo dashboard shell.
8. Làm Books CRUD.
9. Làm Categories CRUD.
10. Làm Brands CRUD.
11. Làm Orders list/detail/update status.
12. Làm Coupons CRUD.
13. Làm Customers detail/subcollections.
14. Làm Reviews hide/restore.
15. Làm Notifications.
16. Làm Dashboard KPI.
17. Kiểm thử end-to-end với app Flutter.
18. Viết README hướng dẫn chạy.

Không được nhảy sang module sau nếu module nền tảng trước đó chưa chạy được, trừ khi có lý do rõ ràng.

## 16. Quy tắc code style

### 16.1. Python/Django

- Code rõ ràng, dễ đọc.
- Không viết function quá dài nếu có thể tách service.
- Không duplicate query Firestore nhiều nơi.
- Dùng constants cho collection names, status, coupon types.
- Có type hints ở service/repository nếu phù hợp.
- Xử lý exception từ Firebase rõ ràng.

### 16.2. Template

- Không duplicate layout.
- Dùng base template.
- Dùng include/component nếu bảng/form lặp lại.
- Không nhúng logic Python phức tạp vào template.

### 16.3. Naming

- Python code dùng snake_case.
- Firestore payload dùng đúng camelCase của app.
- Tên URL rõ nghĩa: `admin_book_list`, `admin_order_detail`.
- Tên service rõ nghĩa: `BookService`, `OrderService`, `AuditService`.

## 17. Quy tắc lỗi và fallback

### 17.1. Khi Firestore lỗi

Phải hiển thị message dễ hiểu cho admin.

Không được để traceback thô trên production.

### 17.2. Khi document không tồn tại

Phải xử lý bằng redirect/message hoặc 404 admin-friendly.

Không được để `NoneType` error.

### 17.3. Khi permission bị từ chối

Phải trả 403 hoặc message phù hợp.

Không được silently ignore.

## 18. Quy tắc Git và file nhạy cảm

### 18.1. Không commit file nhạy cảm

Không được commit:

- `.env`
- `service-account.json`
- Firebase private key
- Local database thật nếu có dữ liệu nhạy cảm

### 18.2. File cấu hình mẫu

Phải tạo hoặc cập nhật:

- `.env.example`
- README hướng dẫn cấu hình Firebase
- `.gitignore`

### 18.3. Không sửa app Flutter nếu không được yêu cầu

Mục tiêu hiện tại là Web Admin.

Không được sửa app Flutter để phù hợp admin, trừ khi user yêu cầu rõ.

## 19. Quy tắc tham chiếu plan

Trước khi triển khai mỗi module, agent phải kiểm tra lại:

- `PLAN_DJANGO_ADMIN.md`
- `rule.md`
- Schema app Flutter liên quan nếu chưa chắc

Nếu có mâu thuẫn:

1. Ưu tiên schema app Flutter thực tế.
2. Sau đó ưu tiên `rule.md`.
3. Sau đó ưu tiên `PLAN_DJANGO_ADMIN.md`.
4. Nếu vẫn chưa rõ, hỏi user.

## 20. Điều cấm tuyệt đối

Agent không được:

1. Tạo PostgreSQL/MySQL database cho dữ liệu Book Store khi chưa được yêu cầu.
2. Tạo ORM models nghiệp vụ thay thế Firestore.
3. Sync hai chiều Django DB <-> Firestore cho dữ liệu nghiệp vụ.
4. Đổi collection/field Firestore đang được app dùng.
5. Ghi snake_case field vào Firestore thay camelCase.
6. Hard delete dữ liệu quan trọng mặc định.
7. Commit service account hoặc secret.
8. Để custom admin view không có `staff_member_required`.
9. Ghi `request.POST` trực tiếp vào Firestore.
10. Bỏ qua validation form.
11. Bỏ qua audit log cho thao tác quan trọng.
12. Tự ý sửa app Flutter nếu chưa được yêu cầu.
13. Tự ý thêm order status/coupon type app chưa hỗ trợ.
14. Tạo UI tách khỏi admin/Unfold layout.
15. Bỏ qua test sau khi hoàn thành module.

## 21. Definition of Done

Một module chỉ được coi là xong khi:

- Có URL/view/template hoặc admin page tương ứng.
- Có permission bảo vệ.
- Có form validation nếu có ghi dữ liệu.
- Đọc/ghi đúng Firestore collection và field.
- Có xử lý lỗi Firestore.
- Có audit log cho thao tác ghi dữ liệu.
- Có empty state/list state phù hợp.
- Có test thủ công tối thiểu.
- Không làm app Flutter vỡ schema.
- Không tạo dữ liệu SQL nghiệp vụ ngoài audit/permission/session.

## 22. Ghi nhớ cuối cùng

Mục tiêu là **nhẹ, nhanh, đúng schema app, không sync hai nguồn dữ liệu**.

Django là admin shell và permission layer. Firestore là database nghiệp vụ chính. Unfold là giao diện. Firebase Admin SDK là cầu nối đọc/ghi dữ liệu.
