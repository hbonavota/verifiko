from app.domain.entities.api_key import ApiKey
from app.domain.value_objects.api_key_id import ApiKeyId
from app.domain.value_objects.user_id import UserId
from app.infrastructure.persistence.models.base_model import ApiKeyModel


class ApiKeyModelMapper:
    @staticmethod
    def to_model(api_key: ApiKey) -> ApiKeyModel:
        model = ApiKeyModel(id=str(api_key.id))
        ApiKeyModelMapper.update_model(model, api_key)
        return model

    @staticmethod
    def update_model(model: ApiKeyModel, api_key: ApiKey) -> ApiKeyModel:
        model.user_id = str(api_key.user_id)
        model.name = api_key.name
        model.token_prefix = api_key.token_prefix
        model.token_hash = api_key.token_hash
        model.created_at = api_key.created_at
        model.last_used_at = api_key.last_used_at
        model.revoked_at = api_key.revoked_at
        return model

    @staticmethod
    def to_domain(model: ApiKeyModel) -> ApiKey:
        return ApiKey(
            id=ApiKeyId.from_string(model.id),
            user_id=UserId.from_string(model.user_id),
            name=model.name,
            token_prefix=model.token_prefix,
            token_hash=model.token_hash,
            created_at=model.created_at,
            last_used_at=model.last_used_at,
            revoked_at=model.revoked_at,
        )
