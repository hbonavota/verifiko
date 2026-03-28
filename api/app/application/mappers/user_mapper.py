from app.application.dto.user_dto import UserDTO
from app.domain.entities.user import User


class UserMapper:
    @staticmethod
    def to_dto(user: User) -> UserDTO:
        return UserDTO(
            id=str(user.id),
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            created_at=user.created_at.isoformat(),
        )
