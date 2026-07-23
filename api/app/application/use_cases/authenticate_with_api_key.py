from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

from app.application.ports.api_key_token_service import ApiKeyTokenServicePort
from app.domain.entities.user import User
from app.domain.ports.api_key_repository import ApiKeyRepository
from app.domain.ports.user_repository import UserRepository

_DEFAULT_USAGE_WRITE_INTERVAL = timedelta(minutes=5)


@dataclass(slots=True)
class AuthenticateWithApiKeyUseCase:
    """Resolves the owning user for a presented API key secret.

    ``last_used_at`` is refreshed at most once per ``usage_write_interval`` to
    avoid a database write on every single authenticated request.
    """

    api_key_repository: ApiKeyRepository
    user_repository: UserRepository
    token_service: ApiKeyTokenServicePort
    current_time_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    usage_write_interval: timedelta = field(default=_DEFAULT_USAGE_WRITE_INTERVAL)

    def execute(self, plaintext: str) -> User | None:
        candidate = (plaintext or "").strip()
        if not candidate or not self.token_service.looks_like_api_key(candidate):
            return None

        token_hash = self.token_service.hash(candidate)
        api_key = self.api_key_repository.get_by_token_hash(token_hash)
        if api_key is None or not api_key.is_active:
            return None

        user = self.user_repository.get_by_id(api_key.user_id)
        if user is None:
            return None

        now = self.current_time_provider()
        if self._should_record_usage(api_key.last_used_at, now):
            self.api_key_repository.record_usage(api_key.id, now)
        return user

    def _should_record_usage(self, last_used_at: datetime | None, now: datetime) -> bool:
        if last_used_at is None:
            return True
        normalized = (
            last_used_at
            if last_used_at.tzinfo is not None
            else last_used_at.replace(tzinfo=timezone.utc)
        )
        return (now - normalized) >= self.usage_write_interval
