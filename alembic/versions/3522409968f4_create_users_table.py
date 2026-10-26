"""Create users table

Revision ID: 3522409968f4
Revises: 7f2974b1b258
Create Date: 2026-07-17 17:50:04.594801

"""
from __future__ import annotations

import json
import mimetypes
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3522409968f4"
down_revision: Union[str, Sequence[str], None] = "7f2974b1b258"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ATTACHMENT_DIR = PROJECT_ROOT / "media" / "attachment"


def _content_type(path: str) -> str:
    return mimetypes.guess_type(path)[0] or "image/jpeg"


def _product_photo_path(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"images/products/{slug or 'no-photo'}.jpg"


def _metadata_for_photo(photo: str, product_name: str) -> dict[str, object]:
    legacy_path = photo.strip() or _product_photo_path(product_name)
    source_path = Path(legacy_path)
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source_path

    filename = Path(legacy_path).name or "photo.jpg"
    file_id = filename
    size = 0
    files: list[str] = []
    url = legacy_path

    if source_path.is_file():
        ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
        file_id = f"{uuid4().hex}{source_path.suffix}"
        storage_path = ATTACHMENT_DIR / file_id
        shutil.copyfile(source_path, storage_path)
        size = storage_path.stat().st_size
        files = [f"default/{file_id}"]
        url = str(storage_path)

    return {
        "filename": filename,
        "content_type": _content_type(filename),
        "size": size,
        "files": files,
        "file_id": file_id,
        "upload_storage": "default",
        "uploaded_at": datetime.utcnow().isoformat(),
        "path": f"default/{file_id}",
        "url": url,
        "saved": True,
        "legacy_path": legacy_path,
    }


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("products", sa.Column("photo_data", sa.JSON(), nullable=True))

    connection = op.get_bind()
    update_stmt = sa.text(
        "UPDATE products "
        "SET photo_data = CAST(:photo_data AS JSON) "
        "WHERE id = :product_id"
    )
    products = list(connection.execute(sa.text("SELECT id, name, photo FROM products")).mappings())
    for product in products:
        metadata = _metadata_for_photo(product["photo"] or "", product["name"] or "")
        connection.execute(
            update_stmt,
            {
                "product_id": product["id"],
                "photo_data": json.dumps(metadata),
            },
        )

    op.drop_column("products", "photo")
    op.alter_column(
        "products",
        "photo_data",
        new_column_name="photo",
        existing_type=sa.JSON(),
        existing_nullable=True,
    )
    op.alter_column(
        "products",
        "photo",
        existing_type=sa.JSON(),
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("products", sa.Column("photo_text", sa.String(length=150), nullable=True))
    op.execute(
        "UPDATE products "
        "SET photo_text = LEFT("
        "COALESCE(NULLIF(photo ->> 'legacy_path', ''), "
        "NULLIF(photo ->> 'url', ''), "
        "'images/products/no-photo.jpg'), 150)"
    )

    op.drop_column("products", "photo")
    op.alter_column(
        "products",
        "photo_text",
        new_column_name="photo",
        existing_type=sa.String(length=150),
        existing_nullable=True,
    )
    op.alter_column(
        "products",
        "photo",
        existing_type=sa.String(length=150),
        nullable=False,
    )
