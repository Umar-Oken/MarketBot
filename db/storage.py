from pathlib import Path

from libcloud.storage.drivers.local import LocalStorageDriver
from sqlalchemy_file.storage import StorageManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEDIA_DIR = PROJECT_ROOT / "media"
ATTACHMENT_DIR = MEDIA_DIR / "attachment"


def configure_file_storage() -> None:
    """Register the local storage used by sqlalchemy-file uploads."""
    ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)

    if "default" in StorageManager._storages:
        return

    container = LocalStorageDriver(str(MEDIA_DIR)).get_container("attachment")
    StorageManager.add_storage("default", container)
