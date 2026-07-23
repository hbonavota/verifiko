from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from app.application.dto.api_key_dto import CreatedApiKeyDTO
from app.application.mappers.api_key_mapper import ApiKeyMapper
from app.application.ports.api_key_token_service import ApiKeyTokenServicePort
from app.domain.entities.api_key import ApiKey
from app.domain.ports.api_key_repository import ApiKeyRepository
from app.domain.value_objects.user_id import UserId


@dataclass(frozen=True, slots=True)
class CreateApiKeyCommand:
    user_id: UserId
    name: str


@dataclass(slots=True)
class CreateApiKeyUseCase:
    api_key_repository: ApiKeyRepository
    token_service: ApiKeyTokenServicePort
    current_time_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

    def execute(self, command: CreateApiKeyCommand) -> CreatedApiKeyDTO:
        generated = self.token_service.generate()
        api_key = ApiKey.issue(
            user_id=command.user_id,
            name=command.name,
            token_prefix=generated.token_prefix,
            token_hash=generated.token_hash,
            now=self.current_time_provider(),
        )
        saved = self.api_key_repository.save(api_key)
        return CreatedApiKeyDTO(
            api_key=ApiKeyMapper.to_dto(saved),
            plaintext=generated.plaintext,
        )
