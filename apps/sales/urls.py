from django.urls import path

from . import views

urlpatterns = [
    path("orders/", views.order_list, name="admin_order_list"),
    path("orders/<str:order_id>/", views.order_detail, name="admin_order_detail"),
    path("orders/<str:order_id>/status/", views.order_update_status, name="admin_order_update_status"),
    path("coupons/", views.coupon_list, name="admin_coupon_list"),
    path("coupons/new/", views.coupon_create, name="admin_coupon_create"),
    path("coupons/<str:coupon_id>/edit/", views.coupon_edit, name="admin_coupon_edit"),
]
