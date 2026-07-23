from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.api_key import ApiKey
from app.domain.value_objects.api_key_id import ApiKeyId
from app.domain.value_objects.user_id import UserId


class ApiKeyRepository(ABC):
    @abstractmethod
    def save(self, api_key: ApiKey) -> ApiKey:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, api_key_id: ApiKeyId) -> ApiKey | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> ApiKey | None:
        raise NotImplementedError

    @abstractmethod
    def list_for_user(self, user_id: UserId) -> list[ApiKey]:
        raise NotImplementedError

    @abstractmethod
    def record_usage(self, api_key_id: ApiKeyId, used_at: datetime) -> None:
        raise NotImplementedError
