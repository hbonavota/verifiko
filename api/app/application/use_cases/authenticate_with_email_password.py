from dataclasses import dataclass

from app.application.dto.user_dto import AuthSessionDTO
from app.application.mappers.user_mapper import UserMapper
from app.application.ports.auth_token_service import AuthTokenServicePort
from app.application.ports.password_hasher import PasswordHasherPort
from app.application.services.email_normalizer import normalize_email
from app.domain.ports.user_repository import UserRepository


class InvalidEmailPasswordCredentialsError(Exception):
    """Raised when local credentials cannot be authenticated."""


@dataclass(frozen=True, slots=True)
class AuthenticateWithEmailPasswordCommand:
    email: str
    password: str


@dataclass(slots=True)
class AuthenticateWithEmailPasswordUseCase:
    user_repository: UserRepository
    password_hasher: PasswordHasherPort
    auth_token_service: AuthTokenServicePort

    def execute(self, command: AuthenticateWithEmailPasswordCommand) -> AuthSessionDTO:
        normalized_email = normalize_email(command.email)
        user = self.user_repository.get_by_email(normalized_email)
        if user is None or user.password_hash is None:
            raise InvalidEmailPasswordCredentialsError

        if not self.password_hasher.verify_password(command.password, user.password_hash):
            raise InvalidEmailPasswordCredentialsError

        return AuthSessionDTO(
            access_token=self.auth_token_service.issue_access_token(user.id),
            token_type="Bearer",
            user=UserMapper.to_dto(user),
        )
