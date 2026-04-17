from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Verifiko API"
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "postgresql+psycopg://verifiko:verifiko@localhost:5432/verifiko"
    cors_allowed_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:4173,"
        "http://127.0.0.1:4173"
    )
    cors_allowed_origin_regex: str | None = None
    anonymous_daily_verification_limit: int = 3
    free_authenticated_daily_verification_limit: int = 10
    pro_authenticated_daily_verification_limit: int = 200
    redis_url: str | None = None
    rate_limit_key_prefix: str = "verifiko:quota"
    google_client_id: str = ""
    auth_token_secret: str = "verifiko-dev-auth-secret"
    auth_token_ttl_seconds: int = 60 * 60 * 24 * 7

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
