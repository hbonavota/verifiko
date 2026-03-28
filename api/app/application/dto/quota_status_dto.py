from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class QuotaStatusDTO:
    subject_type: str
    is_authenticated: bool
    plan: str
    daily_limit: int
    used_today: int
    remaining_today: int
    reset_at_utc: datetime
    reset_in_seconds: int
    blocked: bool
