from __future__ import annotations

import mimetypes
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sqlalchemy_file import File

from db.storage import ATTACHMENT_DIR, PROJECT_ROOT


def _guess_content_type(path: str) -> str:
    return mimetypes.guess_type(path)[0] or "image/jpeg"


def legacy_photo_metadata(path: str) -> dict[str, Any]:
    clean_path = path.strip() or "images/products/no-photo.jpg"
    filename = Path(clean_path).name or "photo.jpg"

    return {
        "filename": filename,
        "content_type": _guess_content_type(filename),
        "size": 0,
        "files": [],
        "file_id": filename,
        "upload_storage": "default",
        "path": f"default/{filename}",
        "url": clean_path,
        "saved": True,
        "legacy_path": clean_path,
    }


def product_photo_file(path: str) -> File:
    clean_path = path.strip() or "images/products/no-photo.jpg"
    source_path = Path(clean_path)
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source_path

    if source_path.is_file():
        return File(content_path=str(source_path))

    return File(legacy_photo_metadata(clean_path))


def product_photo_source(photo: Any) -> str | None:
    if not photo:
        return None

    if isinstance(photo, str):
        source = photo.strip()
        return source or None

    if isinstance(photo, Mapping):
        for key in ("legacy_path", "url"):
            value = photo.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        storage_path = photo.get("path")
        if isinstance(storage_path, str):
            storage, _, file_id = storage_path.partition("/")
            if storage == "default" and file_id:
                path = ATTACHMENT_DIR / file_id
                if path.is_file():
                    return str(path)

    return None


def product_photo_public_path(photo: Any) -> str | None:
    source = product_photo_source(photo)
    if not source:
        return None

    if source.startswith(("http://", "https://")):
        return source

    path = Path(source)
    if path.is_absolute():
        try:
            source = path.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return None

    return source.lstrip("/")
