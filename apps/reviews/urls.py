from django.urls import path

from . import views

urlpatterns = [
    path("", views.review_list, name="admin_review_list"),
    path("<str:review_id>/", views.review_detail, name="admin_review_detail"),
    path("<str:review_id>/toggle-deleted/", views.review_toggle_deleted, name="admin_review_toggle_deleted"),
]
