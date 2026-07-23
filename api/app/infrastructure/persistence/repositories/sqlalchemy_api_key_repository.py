from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker

from app.domain.entities.api_key import ApiKey
from app.domain.ports.api_key_repository import ApiKeyRepository
from app.domain.value_objects.api_key_id import ApiKeyId
from app.domain.value_objects.user_id import UserId
from app.infrastructure.persistence.mappers.api_key_model_mapper import ApiKeyModelMapper
from app.infrastructure.persistence.models.base_model import ApiKeyModel


class SQLAlchemyApiKeyRepository(ApiKeyRepository):
    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def save(self, api_key: ApiKey) -> ApiKey:
        with self._session_factory() as session:
            existing = self._get_model_by_id(session, api_key.id)
            if existing is None:
                model = ApiKeyModelMapper.to_model(api_key)
                session.add(model)
            else:
                ApiKeyModelMapper.update_model(existing, api_key)

            session.commit()
            saved_model = self._get_model_by_id(session, api_key.id)
            if saved_model is None:
                raise RuntimeError("API key persistence failed.")
            return ApiKeyModelMapper.to_domain(saved_model)

    def get_by_id(self, api_key_id: ApiKeyId) -> ApiKey | None:
        with self._session_factory() as session:
            model = self._get_model_by_id(session, api_key_id)
            if model is None:
                return None
            return ApiKeyModelMapper.to_domain(model)

    def get_by_token_hash(self, token_hash: str) -> ApiKey | None:
        with self._session_factory() as session:
            statement = select(ApiKeyModel).where(ApiKeyModel.token_hash == token_hash)
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return None
            return ApiKeyModelMapper.to_domain(model)

    def list_for_user(self, user_id: UserId) -> list[ApiKey]:
        with self._session_factory() as session:
            statement = (
                select(ApiKeyModel)
                .where(ApiKeyModel.user_id == str(user_id))
                .order_by(ApiKeyModel.created_at.desc())
            )
            models = session.execute(statement).scalars().all()
            return [ApiKeyModelMapper.to_domain(model) for model in models]

    def record_usage(self, api_key_id: ApiKeyId, used_at: datetime) -> None:
        with self._session_factory() as session:
            session.execute(
                update(ApiKeyModel)
                .where(ApiKeyModel.id == str(api_key_id))
                .values(last_used_at=used_at)
            )
            session.commit()

    @staticmethod
    def _get_model_by_id(session, api_key_id: ApiKeyId) -> ApiKeyModel | None:
        statement = select(ApiKeyModel).where(ApiKeyModel.id == str(api_key_id))
        return session.execute(statement).scalar_one_or_none()
