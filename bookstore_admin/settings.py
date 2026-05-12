from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DEBUG", "True").lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.firebase_client",
    "apps.dashboard",
    "apps.catalog",
    "apps.sales",
    "apps.customers",
    "apps.reviews",
    "apps.notifications",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "bookstore_admin.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.admin_shell",
            ],
        },
    },
]

WSGI_APPLICATION = "bookstore_admin.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", str(BASE_DIR / "service-account.json"))
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")

UNFOLD = {
    "SITE_TITLE": "Book Store Admin",
    "SITE_HEADER": "Book Store Admin",
    "SITE_SUBHEADER": "Quản trị Firestore",
    "SITE_URL": "/admin-dashboard/",
    "SITE_SYMBOL": "local_library",
    "SHOW_BACK_BUTTON": True,
    "SIDEBAR": {
        "show_search": True,
        "command_search": True,
        "navigation": [
            {
                "title": "Tổng quan",
                "items": [
                    {"title": "Bảng điều khiển", "icon": "dashboard", "link": "/admin-dashboard/"},
                ],
            },
            {
                "title": "Quản lý sách",
                "items": [
                    {"title": "Sách", "icon": "menu_book", "link": "/admin-catalog/books/"},
                    {"title": "Danh mục", "icon": "category", "link": "/admin-catalog/categories/"},
                    {"title": "Thương hiệu/NXB", "icon": "business", "link": "/admin-catalog/brands/"},
                ],
            },
            {
                "title": "Bán hàng",
                "items": [
                    {"title": "Đơn hàng", "icon": "shopping_cart", "link": "/admin-sales/orders/"},
                    {"title": "Mã giảm giá", "icon": "sell", "link": "/admin-sales/coupons/"},
                ],
            },
            {
                "title": "Khách hàng",
                "items": [
                    {"title": "Hồ sơ khách hàng", "icon": "group", "link": "/admin-customers/"},
                ],
            },
            {
                "title": "Tương tác",
                "items": [
                    {"title": "Đánh giá", "icon": "reviews", "link": "/admin-reviews/"},
                    {"title": "Thông báo", "icon": "notifications", "link": "/admin-notifications/"},
                ],
            },
            {
                "title": "Hệ thống",
                "items": [
                    {"title": "Audit logs", "icon": "history", "link": "/admin/audit/auditlog/"},
                    {"title": "Admin users", "icon": "admin_panel_settings", "link": "/admin/auth/user/"},
                    {"title": "Nhóm quyền", "icon": "shield_person", "link": "/admin/auth/group/"},
                ],
            },
        ],
    },
}
