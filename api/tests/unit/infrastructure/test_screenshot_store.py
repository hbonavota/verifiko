import pytest

from app.application.ports.screenshot_store import ScreenshotStoreError
from app.infrastructure.storage.screenshot_store import (
    NullScreenshotStore,
    R2ScreenshotStore,
)


class _RecordingS3Client:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict] = []

    def put_object(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return {"ETag": "stub"}


def test_r2_store_puts_object_and_returns_key() -> None:
    s3 = _RecordingS3Client()
    store = R2ScreenshotStore(s3_client=s3, bucket="verifiko-screenshots")

    ref = store.store(b"\x89PNG payload", content_type="image/png")

    assert len(s3.calls) == 1
    call = s3.calls[0]
    assert call["Bucket"] == "verifiko-screenshots"
    assert call["Body"] == b"\x89PNG payload"
    assert call["ContentType"] == "image/png"
    # The store owns key generation: an opaque, unique screenshots/<uuid>.png key,
    # and the returned reference is exactly that key.
    assert call["Key"] == ref
    assert ref.startswith("screenshots/")
    assert ref.endswith(".png")


def test_r2_store_generates_a_unique_key_per_call() -> None:
    s3 = _RecordingS3Client()
    store = R2ScreenshotStore(s3_client=s3, bucket="b")

    first = store.store(b"a")
    second = store.store(b"b")

    assert first != second


def test_r2_store_wraps_backend_errors() -> None:
    s3 = _RecordingS3Client(error=RuntimeError("boom"))
    store = R2ScreenshotStore(s3_client=s3, bucket="b")

    with pytest.raises(ScreenshotStoreError):
        store.store(b"a")


def test_null_store_returns_none() -> None:
    assert NullScreenshotStore().store(b"anything") is None
