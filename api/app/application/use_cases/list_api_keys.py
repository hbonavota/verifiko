from dataclasses import dataclass

from app.application.dto.api_key_dto import ApiKeyDTO
from app.application.mappers.api_key_mapper import ApiKeyMapper
from app.domain.ports.api_key_repository import ApiKeyRepository
from app.domain.value_objects.user_id import UserId


@dataclass(slots=True)
class ListApiKeysUseCase:
    api_key_repository: ApiKeyRepository

    def execute(self, user_id: UserId) -> list[ApiKeyDTO]:
        return [
            ApiKeyMapper.to_dto(api_key)
            for api_key in self.api_key_repository.list_for_user(user_id)
        ]
