from dataclasses import dataclass

from app.application.dto.user_dto import AuthSessionDTO
from app.application.mappers.user_mapper import UserMapper
from app.application.ports.auth_token_service import AuthTokenServicePort
from app.application.ports.google_identity_verifier import GoogleIdentityVerifierPort
from app.application.services.email_normalizer import normalize_email
from app.domain.entities.user import User
from app.domain.ports.user_repository import UserRepository


@dataclass(slots=True)
class AuthenticateWithGoogleUseCase:
    google_identity_verifier: GoogleIdentityVerifierPort
    user_repository: UserRepository
    auth_token_service: AuthTokenServicePort

    def execute(self, id_token: str) -> AuthSessionDTO:
        identity = self.google_identity_verifier.verify(id_token)
        normalized_email = normalize_email(identity.email)
        user = self.user_repository.get_by_google_subject(identity.subject)
        if user is None:
            user = self.user_repository.get_by_email(normalized_email)

        if user is None:
            user = User.create_google_user(
                email=normalized_email,
                google_subject=identity.subject,
                display_name=identity.display_name,
                avatar_url=identity.avatar_url,
            )
        else:
            user.sync_google_profile(
                email=normalized_email,
                google_subject=identity.subject,
                display_name=identity.display_name,
                avatar_url=identity.avatar_url,
            )

        saved_user = self.user_repository.save(user)
        return AuthSessionDTO(
            access_token=self.auth_token_service.issue_access_token(saved_user.id),
            token_type="Bearer",
            user=UserMapper.to_dto(saved_user),
        )
