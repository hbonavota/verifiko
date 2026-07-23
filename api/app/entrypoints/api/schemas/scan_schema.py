from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.entrypoints.api.schemas.verification_schema import VerificationResponse


class SubmitScanRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)


class SubmitScanBatchRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=50)


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
