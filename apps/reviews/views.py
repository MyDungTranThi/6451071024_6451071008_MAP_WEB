from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render

from apps.core.permissions import PERM_MANAGE_REVIEWS, admin_permission_required

from .services import ReviewService


def _review_service() -> ReviewService:
    return ReviewService()


@admin_permission_required(PERM_MANAGE_REVIEWS)
def review_list(request: HttpRequest) -> HttpResponse:
    status = request.GET.get("status", "active")
    if status not in {"active", "deleted", "all"}:
        status = "active"
    query = request.GET.get("q", "")
    context = {"reviews": [], "status": status, "query": query, "error_message": ""}
    try:
        context["reviews"] = _review_service().list_reviews(status=status, query=query)
    except Exception as exc:
        context["error_message"] = f"Không thể đọc Firestore: {exc}"
    return render(request, "admin_custom/review_list.html", context)


@admin_permission_required(PERM_MANAGE_REVIEWS)
def review_detail(request: HttpRequest, review_id: str) -> HttpResponse:
    review = None
    error_message = ""
    try:
        review = _review_service().get_review(review_id)
    except Exception as exc:
        error_message = f"Không thể đọc Firestore: {exc}"
    return render(request, "admin_custom/review_detail.html", {"review": review, "error_message": error_message})


@admin_permission_required(PERM_MANAGE_REVIEWS)
def review_toggle_deleted(request: HttpRequest, review_id: str) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        service = _review_service()
        review = service.get_review(review_id) or {}
        service.set_deleted(review_id=review_id, is_deleted=not review.get("isDeleted", False), request=request)
        messages.success(request, "Đã cập nhật trạng thái review.")
    except Exception as exc:
        messages.error(request, f"Không thể ghi Firestore: {exc}")
    return redirect("admin_review_detail", review_id=review_id)
