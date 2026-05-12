from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.constants import ORDER_STATUSES
from apps.core.permissions import PERM_MANAGE_COUPONS, PERM_MANAGE_ORDERS, admin_permission_required

from .forms import CouponForm, OrderStatusForm
from .services import CouponService, OrderService


def _order_service() -> OrderService:
    return OrderService()


def _coupon_service() -> CouponService:
    return CouponService()


@admin_permission_required(PERM_MANAGE_ORDERS)
def order_list(request: HttpRequest) -> HttpResponse:
    status = request.GET.get("status", "all")
    if status != "all" and status not in ORDER_STATUSES:
        status = "all"
    query = request.GET.get("q", "")
    context = {"orders": [], "statuses": ORDER_STATUSES, "status": status, "query": query, "error_message": ""}
    try:
        context["orders"] = _order_service().list_orders(status=status, query=query)
    except Exception as exc:
        context["error_message"] = f"Không thể đọc Firestore: {exc}"
    return render(request, "admin_custom/order_list.html", context)


@admin_permission_required(PERM_MANAGE_ORDERS)
def order_detail(request: HttpRequest, order_id: str) -> HttpResponse:
    order = None
    error_message = ""
    try:
        order = _order_service().get_order(order_id)
    except Exception as exc:
        error_message = f"Không thể đọc Firestore: {exc}"
    status_form = OrderStatusForm(initial={"status": (order or {}).get("status", "pending")})
    return render(
        request,
        "admin_custom/order_detail.html",
        {"order": order, "status_form": status_form, "error_message": error_message},
    )


@admin_permission_required(PERM_MANAGE_ORDERS)
def order_update_status(request: HttpRequest, order_id: str) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    form = OrderStatusForm(request.POST)
    if form.is_valid():
        try:
            _order_service().update_status(order_id=order_id, status=form.cleaned_data["status"], request=request)
            messages.success(request, "Đã cập nhật trạng thái đơn hàng.")
        except Exception as exc:
            messages.error(request, f"Không thể ghi Firestore: {exc}")
    else:
        messages.error(request, "Trạng thái đơn hàng không hợp lệ.")
    return redirect("admin_order_detail", order_id=order_id)


@admin_permission_required(PERM_MANAGE_COUPONS)
def coupon_list(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "")
    context = {"coupons": [], "query": query, "error_message": ""}
    try:
        context["coupons"] = _coupon_service().list_coupons(query=query)
    except Exception as exc:
        context["error_message"] = f"Không thể đọc Firestore: {exc}"
    return render(request, "admin_custom/coupon_list.html", context)


@admin_permission_required(PERM_MANAGE_COUPONS)
def coupon_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CouponForm(request.POST, is_create=True)
        if form.is_valid():
            try:
                _coupon_service().create_coupon(payload=form.to_firestore_payload(), request=request)
                messages.success(request, "Đã tạo coupon trên Firestore.")
                return redirect("admin_coupon_list")
            except Exception as exc:
                form.add_error(None, f"Không thể ghi Firestore: {exc}")
    else:
        form = CouponForm(is_create=True)
    return render(
        request,
        "admin_custom/book_form.html",
        {"title": "Thêm coupon", "form": form, "back_url": reverse("admin_coupon_list")},
    )


@admin_permission_required(PERM_MANAGE_COUPONS)
def coupon_edit(request: HttpRequest, coupon_id: str) -> HttpResponse:
    service = _coupon_service()
    try:
        coupon = service.get_coupon(coupon_id)
    except Exception as exc:
        messages.error(request, f"Không thể đọc Firestore: {exc}")
        return redirect("admin_coupon_list")
    if not coupon:
        messages.error(request, "Không tìm thấy coupon.")
        return redirect("admin_coupon_list")

    if request.method == "POST":
        form = CouponForm(request.POST, initial=coupon, is_create=False)
        if form.is_valid():
            try:
                service.update_coupon(coupon_id=coupon_id, payload=form.to_firestore_payload(), request=request)
                messages.success(request, "Đã cập nhật coupon trên Firestore.")
                return redirect("admin_coupon_list")
            except Exception as exc:
                form.add_error(None, f"Không thể ghi Firestore: {exc}")
    else:
        form = CouponForm(initial=coupon, is_create=False)
    return render(
        request,
        "admin_custom/book_form.html",
        {"title": f"Sửa coupon: {coupon_id}", "form": form, "back_url": reverse("admin_coupon_list")},
    )
