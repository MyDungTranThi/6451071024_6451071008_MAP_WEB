from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


_FIREBASE_APP_NAME = "bookstore_admin"


def _load_firebase_modules():
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError as exc:
        raise ImproperlyConfigured(
            "firebase-admin chưa được cài. Hãy chạy: python -m pip install -r requirements.txt"
        ) from exc
    return firebase_admin, credentials, firestore


def _resolve_service_account_path() -> Path:
    configured_path = getattr(settings, "FIREBASE_SERVICE_ACCOUNT_PATH", "")
    if not configured_path:
        raise ImproperlyConfigured("Thiếu FIREBASE_SERVICE_ACCOUNT_PATH trong .env")

    path = Path(configured_path)
    if not path.is_absolute():
        path = settings.BASE_DIR / path
    if not path.exists():
        raise ImproperlyConfigured(f"Không tìm thấy Firebase service account: {path}")
    return path


@lru_cache(maxsize=1)
def get_firebase_app() -> Any:
    """Return a lazily initialized Firebase app.

    This function is intentionally lazy so Django commands such as check and
    migrate can run without Firebase credentials until Firestore is actually used.
    """

    firebase_admin, credentials, _firestore = _load_firebase_modules()

    for app in firebase_admin._apps.values():  # pylint: disable=protected-access
        if app.name == _FIREBASE_APP_NAME:
            return app

    credential = credentials.Certificate(str(_resolve_service_account_path()))
    options = {}
    project_id = getattr(settings, "FIREBASE_PROJECT_ID", "")
    if project_id:
        options["projectId"] = project_id
    return firebase_admin.initialize_app(credential, options=options, name=_FIREBASE_APP_NAME)


@lru_cache(maxsize=1)
def get_firestore_client() -> Any:
    """Return a cached Cloud Firestore client."""

    _firebase_admin, _credentials, firestore = _load_firebase_modules()
    return firestore.client(app=get_firebase_app())


def reset_firebase_cache() -> None:
    """Clear cached Firebase handles. Intended for tests and local debugging."""

    get_firestore_client.cache_clear()
    get_firebase_app.cache_clear()
