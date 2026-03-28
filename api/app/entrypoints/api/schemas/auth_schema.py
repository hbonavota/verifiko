from pydantic import BaseModel, ConfigDict, Field


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=1, max_length=4096)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    avatar_url: str | None
    created_at: str


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str
    user: UserResponse
