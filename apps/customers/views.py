from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.permissions import PERM_MANAGE_CUSTOMERS, admin_permission_required

from .forms import AddressForm, BankAccountForm, CustomerForm
from .services import CustomerService, address_service, bank_account_service


def _customer_service() -> CustomerService:
    return CustomerService()


@admin_permission_required(PERM_MANAGE_CUSTOMERS)
def customer_list(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "")
    context = {"customers": [], "query": query, "error_message": ""}
    try:
        context["customers"] = _customer_service().list_customers(query=query)
    except Exception as exc:
        context["error_message"] = f"Không thể đọc Firestore: {exc}"
    return render(request, "admin_custom/customer_list.html", context)


@admin_permission_required(PERM_MANAGE_CUSTOMERS)
def customer_detail(request: HttpRequest, customer_id: str) -> HttpResponse:
    customer = None
    addresses = []
    bank_accounts = []
    customer_orders = []
    order_summary = {
        "totalOrders": 0,
        "totalSpent": "0 đ",
        "averageOrderValue": "0 đ",
        "latestPurchase": "-",
    }
    error_message = ""
    try:
        service = _customer_service()
        customer = service.get_customer(customer_id)
        if customer:
            addresses = address_service().list_items(customer_id=customer_id)
            bank_accounts = bank_account_service().list_items(customer_id=customer_id)
            customer_orders = service.list_customer_orders(customer_id=customer_id)
            order_summary = service.get_order_summary(customer_orders)
    except Exception as exc:
        error_message = f"Không thể đọc Firestore: {exc}"
    return render(
        request,
        "admin_custom/customer_detail.html",
        {
            "customer": customer,
            "addresses": addresses,
            "bank_accounts": bank_accounts,
            "customer_orders": customer_orders,
            "order_summary": order_summary,
            "error_message": error_message,
        },
    )


@admin_permission_required(PERM_MANAGE_CUSTOMERS)
def customer_edit(request: HttpRequest, customer_id: str) -> HttpResponse:
    service = _customer_service()
    try:
        customer = service.get_customer(customer_id)
    except Exception as exc:
        messages.error(request, f"Không thể đọc Firestore: {exc}")
        return redirect("admin_customer_list")
    if not customer:
        messages.error(request, "Không tìm thấy customer.")
        return redirect("admin_customer_list")

    if request.method == "POST":
        form = CustomerForm(request.POST, request.FILES, initial=customer)
        if form.is_valid():
            try:
                if hasattr(form, "apply_image_uploads"):
                    form.apply_image_uploads(request)
                service.update_customer(customer_id=customer_id, payload=form.to_firestore_payload(), request=request)
                messages.success(request, "Đã cập nhật customer trên Firestore.")
                return redirect("admin_customer_detail", customer_id=customer_id)
            except Exception as exc:
                form.add_error(None, f"Không thể ghi Firestore: {exc}")
    else:
        form = CustomerForm(initial=customer)
    return render(
        request,
        "admin_custom/book_form.html",
        {"title": f"Sửa customer: {customer.get('email', customer_id)}", "form": form, "back_url": reverse("admin_customer_detail", args=[customer_id])},
    )


def _subcollection_form_view(
    request: HttpRequest,
    *,
    customer_id: str,
    item_id: str | None,
    form_class,
    service_factory,
    title: str,
) -> HttpResponse:
    service = service_factory()
    item = None
    if item_id:
        try:
            item = service.get_item(customer_id=customer_id, item_id=item_id)
        except Exception as exc:
            messages.error(request, f"Không thể đọc Firestore: {exc}")
            return redirect("admin_customer_detail", customer_id=customer_id)
        if not item:
            messages.error(request, "Không tìm thấy dữ liệu.")
            return redirect("admin_customer_detail", customer_id=customer_id)

    if request.method == "POST":
        form = form_class(request.POST, request.FILES, initial=item or {})
        if form.is_valid():
            try:
                if hasattr(form, "apply_image_uploads"):
                    form.apply_image_uploads(request)
                if item_id:
                    service.update_item(customer_id=customer_id, item_id=item_id, payload=form.to_firestore_payload(), request=request)
                else:
                    service.create_item(customer_id=customer_id, payload=form.to_firestore_payload(), request=request)
                messages.success(request, "Đã ghi dữ liệu lên Firestore.")
                return redirect("admin_customer_detail", customer_id=customer_id)
            except Exception as exc:
                form.add_error(None, f"Không thể ghi Firestore: {exc}")
    else:
        form = form_class(initial=item or {})
    return render(
        request,
        "admin_custom/book_form.html",
        {"title": title, "form": form, "back_url": reverse("admin_customer_detail", args=[customer_id])},
    )


@admin_permission_required(PERM_MANAGE_CUSTOMERS)
def address_create(request: HttpRequest, customer_id: str) -> HttpResponse:
    return _subcollection_form_view(
        request,
        customer_id=customer_id,
        item_id=None,
        form_class=AddressForm,
        service_factory=address_service,
        title="Thêm địa chỉ",
    )


@admin_permission_required(PERM_MANAGE_CUSTOMERS)
def address_edit(request: HttpRequest, customer_id: str, address_id: str) -> HttpResponse:
    return _subcollection_form_view(
        request,
        customer_id=customer_id,
        item_id=address_id,
        form_class=AddressForm,
        service_factory=address_service,
        title="Sửa địa chỉ",
    )


@admin_permission_required(PERM_MANAGE_CUSTOMERS)
def bank_create(request: HttpRequest, customer_id: str) -> HttpResponse:
    return _subcollection_form_view(
        request,
        customer_id=customer_id,
        item_id=None,
        form_class=BankAccountForm,
        service_factory=bank_account_service,
        title="Thêm tài khoản ngân hàng",
    )


@admin_permission_required(PERM_MANAGE_CUSTOMERS)
def bank_edit(request: HttpRequest, customer_id: str, bank_id: str) -> HttpResponse:
    return _subcollection_form_view(
        request,
        customer_id=customer_id,
        item_id=bank_id,
        form_class=BankAccountForm,
        service_factory=bank_account_service,
        title="Sửa tài khoản ngân hàng",
    )
