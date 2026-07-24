from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenshotStoreError(Exception):
    """Raised when a screenshot cannot be persisted."""


class ScreenshotStorePort(ABC):
    """Persists a captured screenshot and returns an opaque, durable reference.

    The reference (``screenshot_ref``) is an implementation-defined key (e.g. an
    object-store key) that later stages can resolve back to the image — the raw
    bytes never travel through the pipeline, only the reference does. The store
    owns key generation; callers pass bytes only.
    """

    @abstractmethod
    def store(self, image_bytes: bytes, *, content_type: str = "image/png") -> str:
        raise NotImplementedError

    @abstractmethod
    def presigned_url(self, ref: str, *, expires_in: int = 3600) -> str | None:
        """Return a time-limited URL that grants read access to ``ref``.

        Generated on demand at read time and never persisted; returns ``None``
        when no URL can be produced (e.g. the no-op store).
        """
        raise NotImplementedError
