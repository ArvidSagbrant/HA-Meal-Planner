"""Validated local image storage for meal artwork."""

from __future__ import annotations

import os
import tempfile
from hashlib import sha256
from dataclasses import dataclass
from pathlib import Path


MAX_IMAGE_BYTES = 5 * 1024 * 1024


class InvalidImageError(ValueError):
    """Raised when uploaded bytes are not a supported image."""


@dataclass(frozen=True, slots=True)
class StoredImage:
    filename: str
    media_type: str
    size_bytes: int


class MealImageStore:
    """Store only validated image bytes beneath the add-on data directory."""

    def __init__(self, data_dir: Path) -> None:
        self.directory = data_dir / "images"

    def save(self, meal_id: str, data: bytes) -> StoredImage:
        if not data:
            raise InvalidImageError("The uploaded image is empty")
        if len(data) > MAX_IMAGE_BYTES:
            raise InvalidImageError("The uploaded image exceeds the 5 MB limit")
        extension, media_type = self._detect(data)
        self.directory.mkdir(parents=True, exist_ok=True)
        digest = sha256(data).hexdigest()[:16]
        filename = f"{meal_id}-{digest}.{extension}"
        destination = self.directory / filename
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{meal_id}-", dir=self.directory
        )
        try:
            with os.fdopen(descriptor, "wb") as temporary:
                temporary.write(data)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, destination)
        except Exception:
            Path(temporary_name).unlink(missing_ok=True)
            raise
        return StoredImage(filename, media_type, len(data))

    def path(self, filename: str) -> Path:
        if not filename or Path(filename).name != filename:
            raise InvalidImageError("Invalid stored image path")
        return self.directory / filename

    def delete(self, filename: str | None) -> None:
        if filename:
            self.path(filename).unlink(missing_ok=True)

    def prune(self, valid_filenames: set[str]) -> None:
        if not self.directory.is_dir():
            return
        for path in self.directory.iterdir():
            if path.is_file() and path.name not in valid_filenames:
                path.unlink(missing_ok=True)

    @staticmethod
    def _detect(data: bytes) -> tuple[str, str]:
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png", "image/png"
        if data.startswith(b"\xff\xd8\xff"):
            return "jpg", "image/jpeg"
        if data.startswith((b"GIF87a", b"GIF89a")):
            return "gif", "image/gif"
        if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "webp", "image/webp"
        raise InvalidImageError("Only PNG, JPEG, GIF, and WebP images are supported")
