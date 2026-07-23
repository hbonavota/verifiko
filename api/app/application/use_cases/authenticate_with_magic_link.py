from dataclasses import dataclass

from app.application.dto.user_dto import AuthSessionDTO
from app.application.mappers.user_mapper import UserMapper
from app.application.ports.auth_token_service import AuthTokenServicePort
from app.application.ports.magic_link_store import MagicLinkStorePort
from app.application.services.magic_link_token import hash_magic_link_token
from app.domain.entities.user import User
from app.domain.ports.user_repository import UserRepository


class InvalidMagicLinkError(Exception):
    """Raised when a magic-link token is unknown, expired, or already used."""


@dataclass(slots=True)
class AuthenticateWithMagicLinkUseCase:
    magic_link_store: MagicLinkStorePort
    user_repository: UserRepository
    auth_token_service: AuthTokenServicePort

    def execute(self, token: str) -> AuthSessionDTO:
        email = self.magic_link_store.consume(hash_magic_link_token(token))
        if email is None:
            raise InvalidMagicLinkError

        user = self.user_repository.get_by_email(email)
        if user is None:
            user = self.user_repository.save(
                User.create_email_user(email=email, display_name=_display_name(email))
            )

        return AuthSessionDTO(
            access_token=self.auth_token_service.issue_access_token(user.id),
            token_type="Bearer",
            user=UserMapper.to_dto(user),
        )


def _display_name(email: str) -> str:
    local_part = email.split("@", 1)[0].strip()
    return local_part or email
