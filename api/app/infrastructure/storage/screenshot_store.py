from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from app.application.ports.screenshot_store import (
    ScreenshotStoreError,
    ScreenshotStorePort,
)


class NullScreenshotStore(ScreenshotStorePort):
    """No-op store used when screenshot storage is disabled or in tests.

    Deliberately returns ``None`` (never a fabricated reference) so a caller can
    treat "no store configured" and "no screenshot" identically.
    """

    def store(self, image_bytes: bytes, *, content_type: str = "image/png") -> None:
        return None

    def presigned_url(self, ref: str, *, expires_in: int = 3600) -> None:
        return None


class S3PutClient(Protocol):
    """The minimal slice of a boto3 S3 client this adapter needs. Injecting it
    keeps ``R2ScreenshotStore`` fully unit-testable without network or boto3."""

    def put_object(self, **kwargs: Any) -> Any: ...

    def generate_presigned_url(self, *args: Any, **kwargs: Any) -> str: ...


@dataclass(slots=True)
class R2ScreenshotStore(ScreenshotStorePort):
    """Persists screenshots to Cloudflare R2 via its S3-compatible API.

    The S3 client is injected (built by ``build_r2_s3_client`` in the container),
    so this adapter neither imports boto3 nor touches the network on its own. The
    object key is generated internally; the caller only supplies bytes.
    """

    s3_client: S3PutClient
    bucket: str

    def store(self, image_bytes: bytes, *, content_type: str = "image/png") -> str:
        key = f"screenshots/{uuid.uuid4()}.png"
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=image_bytes,
                ContentType=content_type,
            )
        except Exception as exc:  # noqa: BLE001 - surface any backend error uniformly
            raise ScreenshotStoreError(f"Failed to store screenshot: {exc}") from exc
        return key

    def presigned_url(self, ref: str, *, expires_in: int = 3600) -> str | None:
        try:
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": ref},
                ExpiresIn=expires_in,
            )
        except Exception:  # noqa: BLE001 - a missing URL must never break a scan read
            return None


def build_r2_s3_client(
    *,
    account_id: str,
    access_key_id: str,
    secret_access_key: str,
) -> S3PutClient:
    """Build a boto3 S3 client pointed at the Cloudflare R2 endpoint.

    boto3 is imported lazily so it is only required when screenshot storage is
    actually enabled and wired.
    """
    import boto3  # noqa: PLC0415 - lazy import keeps boto3 optional

    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name="auto",
    )
