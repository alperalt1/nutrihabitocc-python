"""Guardado de imágenes: bucket S3 (Neon) o carpeta local. Misma interfaz para ambos."""
from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import Optional

import requests

from config import settings

_EXT_POR_MIME = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}


def _slug(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", texto).strip("_")[:100] or "sin_sku"


class ImageStore:
    def key_para(self, tienda: str, sku: str, ext: str) -> str:
        return f"{settings.S3_PREFIX}/{tienda}/{_slug(sku)}.{ext}"

    def exists(self, key: str) -> bool: ...
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def url(self, key: str, expira: int = 3600) -> Optional[str]: ...

    def guardar_desde_url(self, tienda: str, sku: str, url: str) -> Optional[str]:
        """Descarga la imagen y la guarda. Devuelve la key o None si falla."""
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": settings.USER_AGENT})
            r.raise_for_status()
            mime = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
            ext = _EXT_POR_MIME.get(mime) or (mimetypes.guess_extension(mime) or ".jpg").lstrip(".")
            key = self.key_para(tienda, sku, ext)
            self.put(key, r.content, mime or "image/jpeg")
            return key
        except Exception as e:  # noqa: BLE001
            print(f"  ! imagen no guardada ({url}): {e}")
            return None


class LocalImageStore(ImageStore):
    def _path(self, key: str) -> Path:
        return settings.LOCAL_IMAGES_DIR / key.replace(settings.S3_PREFIX + "/", "", 1)

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def put(self, key: str, data: bytes, content_type: str) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def url(self, key: str, expira: int = 3600) -> Optional[str]:
        return f"/imagenes/{key.replace(settings.S3_PREFIX + '/', '', 1)}" if key else None


class S3ImageStore(ImageStore):
    def __init__(self):
        import boto3
        from botocore.config import Config

        self.bucket = settings.S3_BUCKET
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_ENDPOINT_URL_S3,
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": settings.S3_ADDRESSING_STYLE},
            ),
        )

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def url(self, key: str, expira: int = 3600) -> Optional[str]:
        if not key:
            return None
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expira
        )


def get_image_store() -> ImageStore:
    return S3ImageStore() if settings.IMAGE_STORAGE == "s3" else LocalImageStore()
