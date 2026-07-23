from datetime import datetime, timezone

from app.application.dto.api_key_dto import ApiKeyDTO
from app.domain.entities.api_key import ApiKey


class ApiKeyMapper:
    @staticmethod
    def to_dto(api_key: ApiKey) -> ApiKeyDTO:
        return ApiKeyDTO(
            id=str(api_key.id),
            name=api_key.name,
            token_prefix=api_key.token_prefix,
            created_at=_iso_utc(api_key.created_at),
            last_used_at=_iso_utc(api_key.last_used_at) if api_key.last_used_at else None,
            revoked=not api_key.is_active,
        )


def _iso_utc(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
