from abc import ABC, abstractmethod

from app.domain.value_objects.user_id import UserId


class AuthTokenError(Exception):
    """Raised when an authentication token cannot be issued or verified."""


class AuthTokenServicePort(ABC):
    @abstractmethod
    def issue_access_token(self, user_id: UserId) -> str:
        raise NotImplementedError

    @abstractmethod
    def resolve_user_id(self, token: str) -> UserId:
        raise NotImplementedError
