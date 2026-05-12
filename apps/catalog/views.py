from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.permissions import (
    PERM_MANAGE_BOOKS,
    PERM_MANAGE_BRANDS,
    PERM_MANAGE_CATEGORIES,
    admin_permission_required,
)

from .forms import BookForm, BrandForm, CategoryForm
from .services import BookService, brand_service, category_service


def _book_service() -> BookService:
    return BookService()


def _book_form_options() -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    try:
        return category_service().list_items(limit=300), brand_service().list_items(limit=300), ""
    except Exception as exc:
        return [], [], f"Không thể đọc danh mục/NXB từ Firestore: {exc}"


@admin_permission_required(PERM_MANAGE_BOOKS)
def book_list(request: HttpRequest) -> HttpResponse:
    status = request.GET.get("status", "active")
    if status not in {"active", "all", "deleted", "inactive"}:
        status = "active"
    query = request.GET.get("q", "")
    context = {"books": [], "query": query, "status": status, "error_message": ""}
    try:
        context["books"] = _book_service().list_books(status=status, query=query, limit=100)
    except Exception as exc:
        context["error_message"] = f"Không thể đọc Firestore: {exc}"
    return render(request, "admin_custom/book_list.html", context)


@admin_permission_required(PERM_MANAGE_BOOKS)
def book_detail(request: HttpRequest, book_id: str) -> HttpResponse:
    book = None
    error_message = ""
    try:
        book = _book_service().get_book(book_id)
    except Exception as exc:
        error_message = f"Không thể đọc Firestore: {exc}"
    return render(request, "admin_custom/book_detail.html", {"book": book, "error_message": error_message})


@admin_permission_required(PERM_MANAGE_BOOKS)
def book_create(request: HttpRequest) -> HttpResponse:
    categories, brands, option_error = _book_form_options()
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES, is_create=True, categories=categories, brands=brands)
        if form.is_valid():
            try:
                form.apply_image_uploads(request)
                book_id = _book_service().create_book(
                    payload=form.to_firestore_payload(),
                    document_id=form.cleaned_data.get("documentId") or None,
                    request=request,
                )
                messages.success(request, "Đã tạo sách trên Firestore.")
                return redirect("admin_book_detail", book_id=book_id)
            except Exception as exc:
                form.add_error(None, f"Không thể ghi Firestore: {exc}")
    else:
        form = BookForm(is_create=True, categories=categories, brands=brands)
    return render(
        request,
        "admin_custom/book_form.html",
        {"title": "Thêm sách", "form": form, "back_url": reverse("admin_book_list"), "option_error": option_error},
    )


@admin_permission_required(PERM_MANAGE_BOOKS)
def book_edit(request: HttpRequest, book_id: str) -> HttpResponse:
    service = _book_service()
    try:
        book = service.get_book(book_id)
    except Exception as exc:
        messages.error(request, f"Không thể đọc Firestore: {exc}")
        return redirect("admin_book_list")

    if not book:
        messages.error(request, "Không tìm thấy sách.")
        return redirect("admin_book_list")

    categories, brands, option_error = _book_form_options()
    if request.method == "POST":
        form = BookForm(
            request.POST,
            request.FILES,
            initial=book,
            is_create=False,
            categories=categories,
            brands=brands,
        )
        if form.is_valid():
            try:
                form.apply_image_uploads(request)
                service.update_book(book_id=book_id, payload=form.to_firestore_payload(), request=request)
                messages.success(request, "Đã cập nhật sách trên Firestore.")
                return redirect("admin_book_detail", book_id=book_id)
            except Exception as exc:
                form.add_error(None, f"Không thể ghi Firestore: {exc}")
    else:
        form = BookForm(initial=book, is_create=False, categories=categories, brands=brands)

    return render(
        request,
        "admin_custom/book_form.html",
        {
            "title": f"Sửa sách: {book.get('title', book_id)}",
            "form": form,
            "back_url": reverse("admin_book_detail", kwargs={"book_id": book_id}),
            "option_error": option_error,
        },
    )


@admin_permission_required(PERM_MANAGE_BOOKS)
def book_toggle_active(request: HttpRequest, book_id: str) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    service = _book_service()
    try:
        book = service.get_book(book_id) or {}
        service.set_active(book_id=book_id, is_active=not bool(book.get("isActive", True)), request=request)
        messages.success(request, "Đã cập nhật trạng thái hiển thị.")
    except Exception as exc:
        messages.error(request, f"Không thể ghi Firestore: {exc}")
    return redirect("admin_book_detail", book_id=book_id)


@admin_permission_required(PERM_MANAGE_BOOKS)
def book_soft_delete(request: HttpRequest, book_id: str) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        _book_service().soft_delete_book(book_id=book_id, request=request)
        messages.success(request, "Đã xóa mềm sách.")
    except Exception as exc:
        messages.error(request, f"Không thể ghi Firestore: {exc}")
    return redirect("admin_book_detail", book_id=book_id)


@admin_permission_required(PERM_MANAGE_BOOKS)
def book_restore(request: HttpRequest, book_id: str) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        _book_service().restore_book(book_id=book_id, request=request)
        messages.success(request, "Đã khôi phục sách.")
    except Exception as exc:
        messages.error(request, f"Không thể ghi Firestore: {exc}")
    return redirect("admin_book_detail", book_id=book_id)


def _simple_list(
    request: HttpRequest,
    *,
    service_factory,
    title: str,
    description: str,
    create_route: str,
    edit_route: str,
    show_products_count: bool = False,
) -> HttpResponse:
    query = request.GET.get("q", "")
    context = {
        "title": title,
        "description": description,
        "items": [],
        "query": query,
        "create_url": reverse(create_route),
        "show_products_count": show_products_count,
        "error_message": "",
    }
    try:
        items = service_factory().list_items(query=query)
        for item in items:
            item["editUrl"] = reverse(edit_route, kwargs={"item_id": item["id"]})
            item["displayImage"] = item.get("image") or item.get("imageUrl") or item.get("logo") or "-"
        context["items"] = items
    except Exception as exc:
        context["error_message"] = f"Không thể đọc Firestore: {exc}"
    return render(request, "admin_custom/simple_crud_list.html", context)


def _simple_form(
    request: HttpRequest,
    *,
    service_factory,
    form_class,
    item_id: str | None,
    title: str,
    list_route: str,
) -> HttpResponse:
    service = service_factory()
    item = None
    if item_id:
        try:
            item = service.get_item(item_id)
        except Exception as exc:
            messages.error(request, f"Không thể đọc Firestore: {exc}")
            return redirect(list_route)
        if not item:
            messages.error(request, "Không tìm thấy dữ liệu.")
            return redirect(list_route)

    is_create = item_id is None
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, initial=item or {}, is_create=is_create)
        if form.is_valid():
            try:
                if hasattr(form, "apply_image_uploads"):
                    form.apply_image_uploads(request)
                if is_create:
                    service.create_item(
                        payload=form.to_firestore_payload(),
                        document_id=form.cleaned_data.get("documentId") or None,
                        request=request,
                    )
                    messages.success(request, "Đã tạo dữ liệu trên Firestore.")
                    return redirect(list_route)
                service.update_item(item_id=item_id, payload=form.to_firestore_payload(), request=request)
                messages.success(request, "Đã cập nhật dữ liệu trên Firestore.")
                return redirect(list_route)
            except Exception as exc:
                form.add_error(None, f"Không thể ghi Firestore: {exc}")
    else:
        form = form_class(initial=item or {}, is_create=is_create)

    return render(
        request,
        "admin_custom/book_form.html",
        {"title": title, "form": form, "back_url": reverse(list_route)},
    )


@admin_permission_required(PERM_MANAGE_CATEGORIES)
def category_list(request: HttpRequest) -> HttpResponse:
    return _simple_list(
        request,
        service_factory=category_service,
        title="Categories",
        description="Quản lý trực tiếp collection categories trên Firestore.",
        create_route="admin_category_create",
        edit_route="admin_category_edit",
    )


@admin_permission_required(PERM_MANAGE_CATEGORIES)
def category_create(request: HttpRequest) -> HttpResponse:
    return _simple_form(
        request,
        service_factory=category_service,
        form_class=CategoryForm,
        item_id=None,
        title="Thêm category",
        list_route="admin_category_list",
    )


@admin_permission_required(PERM_MANAGE_CATEGORIES)
def category_edit(request: HttpRequest, item_id: str) -> HttpResponse:
    return _simple_form(
        request,
        service_factory=category_service,
        form_class=CategoryForm,
        item_id=item_id,
        title="Sửa category",
        list_route="admin_category_list",
    )


@admin_permission_required(PERM_MANAGE_BRANDS)
def brand_list(request: HttpRequest) -> HttpResponse:
    return _simple_list(
        request,
        service_factory=brand_service,
        title="Brands/NXB",
        description="Quản lý trực tiếp collection brands trên Firestore.",
        create_route="admin_brand_create",
        edit_route="admin_brand_edit",
        show_products_count=True,
    )


@admin_permission_required(PERM_MANAGE_BRANDS)
def brand_create(request: HttpRequest) -> HttpResponse:
    return _simple_form(
        request,
        service_factory=brand_service,
        form_class=BrandForm,
        item_id=None,
        title="Thêm brand/NXB",
        list_route="admin_brand_list",
    )


@admin_permission_required(PERM_MANAGE_BRANDS)
def brand_edit(request: HttpRequest, item_id: str) -> HttpResponse:
    return _simple_form(
        request,
        service_factory=brand_service,
        form_class=BrandForm,
        item_id=item_id,
        title="Sửa brand/NXB",
        list_route="admin_brand_list",
    )


@admin_permission_required(PERM_MANAGE_BOOKS)
def placeholder(request: HttpRequest, title: str) -> HttpResponse:
    return render(
        request,
        "admin_custom/list.html",
        {"title": title, "description": "Module sẽ đọc/ghi trực tiếp Firestore ở các giai đoạn tiếp theo.", "items": []},
    )
