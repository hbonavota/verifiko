from app.domain.entities.user import User
from app.domain.enums.user_plan import UserPlan
from app.domain.value_objects.user_id import UserId
from app.infrastructure.persistence.models.base_model import UserModel


class UserModelMapper:
    @staticmethod
    def to_model(user: User) -> UserModel:
        model = UserModel(id=str(user.id))
        UserModelMapper.update_model(model, user)
        return model

    @staticmethod
    def update_model(model: UserModel, user: User) -> UserModel:
        model.email = user.email
        model.google_subject = user.google_subject
        model.display_name = user.display_name
        model.avatar_url = user.avatar_url
        model.plan = user.plan.value
        model.created_at = user.created_at
        model.updated_at = user.updated_at
        return model

    @staticmethod
    def to_domain(model: UserModel) -> User:
        return User(
            id=UserId.from_string(model.id),
            email=model.email,
            google_subject=model.google_subject,
            display_name=model.display_name,
            avatar_url=model.avatar_url,
            plan=UserPlan(model.plan),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
