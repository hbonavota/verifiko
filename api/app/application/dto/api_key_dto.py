from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApiKeyDTO:
    id: str
    name: str
    token_prefix: str
    created_at: str
    last_used_at: str | None
    revoked: bool


@dataclass(frozen=True, slots=True)
class CreatedApiKeyDTO:
    api_key: ApiKeyDTO
    plaintext: str
