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
