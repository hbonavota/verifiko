import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9-]+(?:\.[A-Z0-9-]+)+$",
    re.IGNORECASE,
)


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=1, max_length=4096)


class LocalRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if not EMAIL_PATTERN.match(normalized_value):
            raise ValueError("Enter a valid email address.")
        return normalized_value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        stripped_value = value.strip()
        if len(stripped_value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not any(character.isalpha() for character in stripped_value):
            raise ValueError("Password must include at least one letter.")
        if not any(character.isdigit() for character in stripped_value):
            raise ValueError("Password must include at least one number.")
        return value

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        stripped_value = value.strip()
        if len(stripped_value) < 2:
            raise ValueError("Display name must be at least 2 characters long.")
        return stripped_value


class LocalLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if not EMAIL_PATTERN.match(normalized_value):
            raise ValueError("Enter a valid email address.")
        return normalized_value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    avatar_url: str | None
    plan: str
    created_at: str


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str
    user: UserResponse
