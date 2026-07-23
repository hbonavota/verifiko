from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from app.application.exceptions.application_exception import ApiKeyNotFoundError
from app.domain.ports.api_key_repository import ApiKeyRepository
from app.domain.value_objects.api_key_id import ApiKeyId
from app.domain.value_objects.user_id import UserId


@dataclass(frozen=True, slots=True)
class RevokeApiKeyCommand:
    user_id: UserId
    api_key_id: str


@dataclass(slots=True)
class RevokeApiKeyUseCase:
    api_key_repository: ApiKeyRepository
    current_time_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

    def execute(self, command: RevokeApiKeyCommand) -> None:
        try:
            api_key_id = ApiKeyId.from_string(command.api_key_id)
        except (ValueError, AttributeError) as exc:
            raise ApiKeyNotFoundError(command.api_key_id) from exc

        api_key = self.api_key_repository.get_by_id(api_key_id)
        # Ownership check doubles as a non-enumeration guard: keys that do not
        # belong to the caller are indistinguishable from keys that do not exist.
        if api_key is None or api_key.user_id != command.user_id:
            raise ApiKeyNotFoundError(command.api_key_id)

        if not api_key.is_active:
            return

        api_key.revoke(self.current_time_provider())
        self.api_key_repository.save(api_key)
