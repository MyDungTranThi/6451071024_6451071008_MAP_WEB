from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from django.core.files.storage import default_storage
from django.http import HttpRequest
from django.utils.text import get_valid_filename


def save_admin_image_upload(request: HttpRequest, uploaded_file, *, folder: str) -> str:
    """Save an admin-uploaded image and return an absolute URL for Firestore."""

    suffix = Path(uploaded_file.name).suffix.lower()
    filename = f"{uuid4().hex}{suffix}"
    safe_folder = get_valid_filename(folder).strip("_") or "images"
    relative_path = default_storage.save(f"admin_uploads/{safe_folder}/{filename}", uploaded_file)
    media_path = default_storage.url(relative_path)
    return request.build_absolute_uri(media_path)
