from dataclasses import dataclass

from app.application.dto.user_dto import AuthSessionDTO
from app.application.mappers.user_mapper import UserMapper
from app.application.ports.auth_token_service import AuthTokenServicePort
from app.application.ports.password_hasher import PasswordHasherPort
from app.application.services.email_normalizer import normalize_email
from app.domain.entities.user import User
from app.domain.ports.user_repository import UserRepository


class EmailAlreadyRegisteredError(Exception):
    """Raised when a local registration email is already in use."""


@dataclass(frozen=True, slots=True)
class RegisterWithEmailPasswordCommand:
    email: str
    password: str
    display_name: str


@dataclass(slots=True)
class RegisterWithEmailPasswordUseCase:
    user_repository: UserRepository
    password_hasher: PasswordHasherPort
    auth_token_service: AuthTokenServicePort

    def execute(self, command: RegisterWithEmailPasswordCommand) -> AuthSessionDTO:
        normalized_email = normalize_email(command.email)
        existing_user = self.user_repository.get_by_email(normalized_email)
        if existing_user is not None:
            raise EmailAlreadyRegisteredError

        password_hash = self.password_hasher.hash_password(command.password)
        user = User.create_local_user(
            email=normalized_email,
            password_hash=password_hash,
            display_name=command.display_name.strip(),
        )
        saved_user = self.user_repository.save(user)

        return AuthSessionDTO(
            access_token=self.auth_token_service.issue_access_token(saved_user.id),
            token_type="Bearer",
            user=UserMapper.to_dto(saved_user),
        )
