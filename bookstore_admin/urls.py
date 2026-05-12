from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.shortcuts import redirect


urlpatterns = [
    path("", lambda request: redirect("/admin-dashboard/")),
    path("admin/", admin.site.urls),
    path("admin-dashboard/", include("apps.dashboard.urls")),
    path("admin-catalog/", include("apps.catalog.urls")),
    path("admin-sales/", include("apps.sales.urls")),
    path("admin-customers/", include("apps.customers.urls")),
    path("admin-reviews/", include("apps.reviews.urls")),
    path("admin-notifications/", include("apps.notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
