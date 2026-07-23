from __future__ import annotations

from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.entrypoints.api.schemas.verification_schema import VerificationResponse


def _validate_webhook_url(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if urlsplit(stripped).scheme not in {"http", "https"}:
        raise ValueError("webhook_url must be an http(s) URL.")
    return stripped


class SubmitScanRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)
    webhook_url: str | None = Field(default=None, max_length=2048)

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, value: str | None) -> str | None:
        return _validate_webhook_url(value)


class SubmitScanBatchRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=50)
    webhook_url: str | None = Field(default=None, max_length=2048)

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, value: str | None) -> str | None:
        return _validate_webhook_url(value)


class ScanAcceptedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: str
    status: str
    url: str


class ScanBatchAcceptedResponse(BaseModel):
    scans: tuple[ScanAcceptedResponse, ...]


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: str
    status: str
    url: str
    created_at: str
    updated_at: str
    result_verification_id: str | None = None
    result: VerificationResponse | None = None
    error: str | None = None
