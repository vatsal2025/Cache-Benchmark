import os
import uuid
from pathlib import Path
from app.core.config import settings


class LocalStorage:
    def __init__(self, base_path: str):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    def get_upload_url(self, org_id: str, resource_type: str, resource_id: str, filename: str) -> tuple[str, str]:
        key = f"{settings.ENVIRONMENT}/{org_id}/{resource_type}/{resource_id}/{filename}"
        full_path = self.base / key
        full_path.parent.mkdir(parents=True, exist_ok=True)
        presigned_url = f"/v1/storage/upload/{key}"
        return presigned_url, key

    def get_download_url(self, key: str) -> str:
        return f"/v1/storage/download/{key}"

    def exists(self, key: str) -> bool:
        return (self.base / key).exists()

    def save(self, key: str, data: bytes) -> None:
        path = self.base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def load(self, key: str) -> bytes:
        return (self.base / key).read_bytes()


def get_storage() -> LocalStorage:
    return LocalStorage(settings.STORAGE_PATH)
