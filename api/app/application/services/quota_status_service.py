from dataclasses import dataclass

from app.application.dto.quota_status_dto import QuotaStatusDTO
from app.domain.entities.user import User
from app.infrastructure.security.authenticated_utc_day_quota_limiter import (
    AuthenticatedUtcDayQuotaLimiter,
)
from app.infrastructure.security.utc_day_quota_limiter import UtcDayQuotaLimiter


@dataclass(slots=True)
class QuotaStatusService:
    anonymous_quota_limiter: UtcDayQuotaLimiter
    authenticated_quota_limiter: AuthenticatedUtcDayQuotaLimiter

    def for_anonymous(self, key: str) -> QuotaStatusDTO:
        status = self.anonymous_quota_limiter.get_status(key)
        return QuotaStatusDTO(
            subject_type="ANONYMOUS",
            is_authenticated=False,
            plan="ANONYMOUS",
            daily_limit=status.daily_limit,
            used_today=status.used_today,
            remaining_today=status.remaining_today,
            reset_at_utc=status.reset_at_utc,
            reset_in_seconds=status.reset_in_seconds,
            blocked=status.remaining_today == 0,
        )

    def for_user(self, user: User) -> QuotaStatusDTO:
        status = self.authenticated_quota_limiter.get_status(user)
        return QuotaStatusDTO(
            subject_type="USER",
            is_authenticated=True,
            plan=user.plan.value,
            daily_limit=status.daily_limit,
            used_today=status.used_today,
            remaining_today=status.remaining_today,
            reset_at_utc=status.reset_at_utc,
            reset_in_seconds=status.reset_in_seconds,
            blocked=status.remaining_today == 0,
        )
