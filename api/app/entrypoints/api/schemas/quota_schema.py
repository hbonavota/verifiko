from datetime import datetime

from pydantic import BaseModel


class QuotaStatusResponse(BaseModel):
    subject_type: str
    is_authenticated: bool
    plan: str
    daily_limit: int
    used_today: int
    remaining_today: int
    reset_at_utc: datetime
    reset_in_seconds: int
    blocked: bool
