from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.permissions import PERM_MANAGE_NOTIFICATIONS, admin_permission_required

from .forms import NotificationForm
from .services import NotificationService


def _notification_service() -> NotificationService:
    return NotificationService()


def _notification_form_options() -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    try:
        service = _notification_service()
        return service.list_user_options(), service.list_order_options(), ""
    except Exception as exc:
        return [], [], f"Không thể đọc users/orders từ Firestore: {exc}"


@admin_permission_required(PERM_MANAGE_NOTIFICATIONS)
def notification_list(request: HttpRequest) -> HttpResponse:
    status = request.GET.get("status", "all")
    if status not in {"all", "read", "unread"}:
        status = "all"
    query = request.GET.get("q", "")
    context = {"notifications": [], "status": status, "query": query, "error_message": ""}
    try:
        context["notifications"] = _notification_service().list_notifications(status=status, query=query)
    except Exception as exc:
        context["error_message"] = f"Không thể đọc Firestore: {exc}"
    return render(request, "admin_custom/notification_list.html", context)


@admin_permission_required(PERM_MANAGE_NOTIFICATIONS)
def notification_create(request: HttpRequest) -> HttpResponse:
    users, orders, option_error = _notification_form_options()
    if request.method == "POST":
        form = NotificationForm(request.POST, users=users, orders=orders)
        if form.is_valid():
            try:
                _notification_service().create_notification(payload=form.to_firestore_payload(), request=request)
                messages.success(request, "Đã tạo notification trên Firestore.")
                return redirect("admin_notification_list")
            except Exception as exc:
                form.add_error(None, f"Không thể ghi Firestore: {exc}")
    else:
        form = NotificationForm(initial={"isRead": False}, users=users, orders=orders)
    return render(
        request,
        "admin_custom/notification_form.html",
        {
            "title": "Tạo notification",
            "form": form,
            "back_url": reverse("admin_notification_list"),
            "orders": orders,
            "option_error": option_error,
        },
    )


@admin_permission_required(PERM_MANAGE_NOTIFICATIONS)
def notification_edit(request: HttpRequest, notification_id: str) -> HttpResponse:
    service = _notification_service()
    users, orders, option_error = _notification_form_options()
    try:
        notification = service.get_notification(notification_id)
    except Exception as exc:
        messages.error(request, f"Không thể đọc Firestore: {exc}")
        return redirect("admin_notification_list")
    if not notification:
        messages.error(request, "Không tìm thấy notification.")
        return redirect("admin_notification_list")

    if request.method == "POST":
        form = NotificationForm(request.POST, initial=notification, users=users, orders=orders)
        if form.is_valid():
            try:
                service.update_notification(notification_id=notification_id, payload=form.to_firestore_payload(), request=request)
                messages.success(request, "Đã cập nhật notification trên Firestore.")
                return redirect("admin_notification_list")
            except Exception as exc:
                form.add_error(None, f"Không thể ghi Firestore: {exc}")
    else:
        form = NotificationForm(initial=notification, users=users, orders=orders)
    return render(
        request,
        "admin_custom/notification_form.html",
        {
            "title": f"Sửa notification: {notification_id}",
            "form": form,
            "back_url": reverse("admin_notification_list"),
            "orders": orders,
            "option_error": option_error,
        },
    )
