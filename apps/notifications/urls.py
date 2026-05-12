from django.urls import path

from . import views

urlpatterns = [
    path("", views.notification_list, name="admin_notification_list"),
    path("new/", views.notification_create, name="admin_notification_create"),
    path("<str:notification_id>/edit/", views.notification_edit, name="admin_notification_edit"),
]
