from abc import ABC, abstractmethod

from app.domain.entities.user import User
from app.domain.value_objects.user_id import UserId


class UserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: UserId) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_google_subject(self, google_subject: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        raise NotImplementedError
