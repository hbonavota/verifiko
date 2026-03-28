from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.domain.entities.user import User
from app.domain.ports.user_repository import UserRepository
from app.domain.value_objects.user_id import UserId
from app.infrastructure.persistence.mappers.user_model_mapper import UserModelMapper
from app.infrastructure.persistence.models.base_model import UserModel


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def save(self, user: User) -> User:
        with self._session_factory() as session:
            existing = self._get_model_by_id(session, user.id)
            if existing is None:
                model = UserModelMapper.to_model(user)
                session.add(model)
            else:
                UserModelMapper.update_model(existing, user)

            session.commit()
            saved_model = self._get_model_by_id(session, user.id)
            if saved_model is None:
                raise RuntimeError("User persistence failed.")
            return UserModelMapper.to_domain(saved_model)

    def get_by_id(self, user_id: UserId) -> User | None:
        with self._session_factory() as session:
            model = self._get_model_by_id(session, user_id)
            if model is None:
                return None
            return UserModelMapper.to_domain(model)

    def get_by_google_subject(self, google_subject: str) -> User | None:
        with self._session_factory() as session:
            statement = select(UserModel).where(UserModel.google_subject == google_subject)
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return None
            return UserModelMapper.to_domain(model)

    def get_by_email(self, email: str) -> User | None:
        with self._session_factory() as session:
            statement = select(UserModel).where(UserModel.email == email)
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return None
            return UserModelMapper.to_domain(model)

    @staticmethod
    def _get_model_by_id(session, user_id: UserId) -> UserModel | None:
        statement = select(UserModel).where(UserModel.id == str(user_id))
        return session.execute(statement).scalar_one_or_none()
