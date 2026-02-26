from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator


class UrlScanIn(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("URL cannot be empty")
        return v


class ScanOut(BaseModel):
    id: str
    status: Optional[str] = None
    score: Optional[int] = None  # noqa: UP045
    verdict: Optional[str] = None  # noqa: UP045
    created_at: Optional[str] = None
    engine_version: Optional[str] = None
    ruleset_version: Optional[str] = None
