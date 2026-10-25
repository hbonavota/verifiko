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
        self.presign_calls: list[dict] = []

    def put_object(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return {"ETag": "stub"}

    def generate_presigned_url(self, operation, *, Params, ExpiresIn):
        self.presign_calls.append(
            {"operation": operation, "Params": Params, "ExpiresIn": ExpiresIn}
        )
        if self.error is not None:
            raise self.error
        return f"https://signed.example/{Params['Key']}?exp={ExpiresIn}"


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


def test_r2_store_presigned_url_calls_boto3_with_bucket_and_key() -> None:
    s3 = _RecordingS3Client()
    store = R2ScreenshotStore(s3_client=s3, bucket="verifiko-screenshots")

    url = store.presigned_url("screenshots/abc.png", expires_in=120)

    assert len(s3.presign_calls) == 1
    call = s3.presign_calls[0]
    assert call["operation"] == "get_object"
    assert call["Params"] == {
        "Bucket": "verifiko-screenshots",
        "Key": "screenshots/abc.png",
    }
    assert call["ExpiresIn"] == 120
    assert url == "https://signed.example/screenshots/abc.png?exp=120"


def test_r2_store_presigned_url_returns_none_on_backend_error() -> None:
    s3 = _RecordingS3Client(error=RuntimeError("boom"))
    store = R2ScreenshotStore(s3_client=s3, bucket="b")

    assert store.presigned_url("screenshots/x.png") is None


def test_null_store_returns_none() -> None:
    assert NullScreenshotStore().store(b"anything") is None
    assert NullScreenshotStore().presigned_url("screenshots/x.png") is None
