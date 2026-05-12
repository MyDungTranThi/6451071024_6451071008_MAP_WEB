from django.urls import path

from . import views

urlpatterns = [
    path("", views.customer_list, name="admin_customer_list"),
    path("<str:customer_id>/", views.customer_detail, name="admin_customer_detail"),
    path("<str:customer_id>/edit/", views.customer_edit, name="admin_customer_edit"),
    path("<str:customer_id>/addresses/new/", views.address_create, name="admin_customer_address_create"),
    path("<str:customer_id>/addresses/<str:address_id>/edit/", views.address_edit, name="admin_customer_address_edit"),
    path("<str:customer_id>/banks/new/", views.bank_create, name="admin_customer_bank_create"),
    path("<str:customer_id>/banks/<str:bank_id>/edit/", views.bank_edit, name="admin_customer_bank_edit"),
]
