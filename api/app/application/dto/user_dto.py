from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: str
    email: str
    display_name: str
    avatar_url: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class AuthSessionDTO:
    access_token: str
    token_type: str
    user: UserDTO
