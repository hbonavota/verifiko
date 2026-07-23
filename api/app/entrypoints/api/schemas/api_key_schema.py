from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("API key name cannot be empty.")
        return stripped_value


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    token_prefix: str
    created_at: str
    last_used_at: str | None
    revoked: bool


class CreatedApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    token_prefix: str
    created_at: str
    # The full secret, returned exactly once at creation time.
    api_key: str
