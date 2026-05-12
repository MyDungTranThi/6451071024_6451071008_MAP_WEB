from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.core.permissions import PERM_VIEW_DASHBOARD, admin_permission_required

from .services import DashboardService


@admin_permission_required(PERM_VIEW_DASHBOARD)
def dashboard_home(request: HttpRequest) -> HttpResponse:
    context = {"title": "Dashboard", "cards": [], "order_statuses": {}, "charts": {}, "error_message": ""}
    try:
        context.update(DashboardService().get_summary())
    except Exception as exc:
        context["error_message"] = f"Chưa thể đọc Firestore: {exc}"
        context["cards"] = [
            {"label": "Firestore", "value": "Chưa kết nối", "description": "Kiểm tra firebase-admin và credentials"},
            {"label": "Books", "value": "-", "description": "Đọc trực tiếp từ collection books"},
            {"label": "Orders", "value": "-", "description": "Đọc trực tiếp từ collection orders"},
        ]
    return render(request, "admin_custom/dashboard.html", context)
