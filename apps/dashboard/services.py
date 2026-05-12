from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from django.utils import timezone

from apps.core.constants import (
    COLLECTION_BOOKS,
    COLLECTION_COUPONS,
    COLLECTION_NOTIFICATIONS,
    COLLECTION_ORDERS,
    COLLECTION_REVIEWS,
    COLLECTION_USERS,
    ORDER_STATUSES,
)
from apps.firebase_client.repositories import FirestoreRepository


class DashboardService:
    def __init__(self, repositories: dict[str, FirestoreRepository] | None = None):
        self.repositories = repositories or {}

    def _repository(self, collection_name: str) -> FirestoreRepository:
        return self.repositories.get(collection_name) or FirestoreRepository(collection_name)

    def _safe_list(
        self,
        collection_name: str,
        *,
        limit: int = 500,
        order_by: str | None = None,
        descending: bool = False,
    ) -> list[dict[str, Any]]:
        return self._repository(collection_name).list(limit=limit, order_by=order_by, descending=descending).items

    @staticmethod
    def _as_date(value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except ValueError:
                return None
        return None

    @staticmethod
    def _stock_bucket(stock: Any) -> str:
        try:
            amount = int(float(stock or 0))
        except (TypeError, ValueError):
            amount = 0
        if amount <= 0:
            return "Hết hàng"
        if amount <= 5:
            return "Sắp hết"
        if amount <= 20:
            return "Ổn định"
        return "Nhiều hàng"

    def _build_charts(
        self,
        *,
        books: list[dict[str, Any]],
        orders: list[dict[str, Any]],
        reviews: list[dict[str, Any]],
        notifications: list[dict[str, Any]],
        by_status: dict[str, int],
    ) -> dict[str, Any]:
        today = timezone.localdate()
        days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        revenue_by_day = {day: 0.0 for day in days}
        order_count_by_day = {day: 0 for day in days}

        for order in orders:
            order_date = self._as_date(order.get("createdAt"))
            if order_date not in revenue_by_day:
                continue
            order_count_by_day[order_date] += 1
            if order.get("status") != "cancelled":
                revenue_by_day[order_date] += float(order.get("total") or 0)

        stock_counts = defaultdict(int)
        for book in books:
            stock_counts[self._stock_bucket(book.get("stock"))] += 1

        rating_counts = {str(value): 0 for value in range(1, 6)}
        for review in reviews:
            try:
                rating = round(float(review.get("rating") or 0))
            except (TypeError, ValueError):
                rating = 0
            if 1 <= rating <= 5:
                rating_counts[str(rating)] += 1

        read_count = len([item for item in notifications if item.get("isRead", False)])
        unread_count = len(notifications) - read_count

        return {
            "orderStatus": {
                "labels": list(by_status.keys()),
                "values": list(by_status.values()),
            },
            "revenue7Days": {
                "labels": [day.strftime("%d/%m") for day in days],
                "revenue": [round(revenue_by_day[day], 2) for day in days],
                "orders": [order_count_by_day[day] for day in days],
            },
            "stock": {
                "labels": ["Hết hàng", "Sắp hết", "Ổn định", "Nhiều hàng"],
                "values": [stock_counts[label] for label in ["Hết hàng", "Sắp hết", "Ổn định", "Nhiều hàng"]],
            },
            "ratings": {
                "labels": ["1 sao", "2 sao", "3 sao", "4 sao", "5 sao"],
                "values": [rating_counts[str(value)] for value in range(1, 6)],
            },
            "notifications": {
                "labels": ["Chưa đọc", "Đã đọc"],
                "values": [unread_count, read_count],
            },
        }

    def get_summary(self) -> dict[str, Any]:
        books = self._safe_list(COLLECTION_BOOKS, order_by="title")
        orders = self._safe_list(COLLECTION_ORDERS, order_by="createdAt", descending=True)
        users = self._safe_list(COLLECTION_USERS, order_by="email")
        reviews = self._safe_list(COLLECTION_REVIEWS, order_by="createdAt", descending=True)
        coupons = self._safe_list(COLLECTION_COUPONS, order_by="code")
        notifications = self._safe_list(COLLECTION_NOTIFICATIONS, order_by="createdAt", descending=True)

        revenue = sum(float(order.get("total") or 0) for order in orders if order.get("status") != "cancelled")
        by_status = {status: 0 for status in ORDER_STATUSES}
        for order in orders:
            status = order.get("status")
            if status in by_status:
                by_status[status] += 1

        return {
            "cards": [
                {"label": "Books", "value": len(books), "description": "Tổng sách trong Firestore"},
                {"label": "Orders", "value": len(orders), "description": "Tổng đơn hàng"},
                {"label": "Revenue", "value": f"{revenue:,.0f}", "description": "Doanh thu chưa gồm đơn cancelled"},
                {"label": "Customers", "value": len(users), "description": "Tổng users"},
                {"label": "Reviews", "value": len(reviews), "description": "Tổng reviews"},
                {"label": "Coupons", "value": len(coupons), "description": "Tổng coupons"},
                {
                    "label": "Unread notifications",
                    "value": len([item for item in notifications if not item.get("isRead", False)]),
                    "description": "Thông báo chưa đọc",
                },
            ],
            "order_statuses": by_status,
            "charts": self._build_charts(
                books=books,
                orders=orders,
                reviews=reviews,
                notifications=notifications,
                by_status=by_status,
            ),
        }
