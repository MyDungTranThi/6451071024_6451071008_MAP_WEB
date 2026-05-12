from django.urls import path

from . import views

urlpatterns = [
    path("books/", views.book_list, name="admin_book_list"),
    path("books/new/", views.book_create, name="admin_book_create"),
    path("books/<str:book_id>/", views.book_detail, name="admin_book_detail"),
    path("books/<str:book_id>/edit/", views.book_edit, name="admin_book_edit"),
    path("books/<str:book_id>/toggle-active/", views.book_toggle_active, name="admin_book_toggle_active"),
    path("books/<str:book_id>/soft-delete/", views.book_soft_delete, name="admin_book_soft_delete"),
    path("books/<str:book_id>/restore/", views.book_restore, name="admin_book_restore"),
    path("categories/", views.category_list, name="admin_category_list"),
    path("categories/new/", views.category_create, name="admin_category_create"),
    path("categories/<str:item_id>/edit/", views.category_edit, name="admin_category_edit"),
    path("brands/", views.brand_list, name="admin_brand_list"),
    path("brands/new/", views.brand_create, name="admin_brand_create"),
    path("brands/<str:item_id>/edit/", views.brand_edit, name="admin_brand_edit"),
]
