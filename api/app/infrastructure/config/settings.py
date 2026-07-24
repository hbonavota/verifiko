from functools import lru_cache
from ipaddress import IPv4Network, IPv6Network, ip_network

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
    verification_burst_limit_requests: int = 10
    verification_burst_limit_window_seconds: int = 60
    verification_parallel_analysis_enabled: bool = True
    # Fail-fast orchestrator: when the URL-only analysis already yields a
    # decisively malicious verdict, skip the expensive network-bound waves.
    # Off by default; enable in production to cut latency/cost on obvious cases.
    verification_fast_path_enabled: bool = False
    # Headless detonation (Phase B). Off by default; requires a Browserless
    # endpoint (its URL carries the token). Runs only on the async scan path.
    detonation_enabled: bool = False
    browserless_endpoint: str = ""
    detonation_timeout_seconds: float = 30.0
    detonation_capture_screenshot: bool = True
    analysis_cache_key_prefix: str = "verifiko:analysis"
    # Reputation stays short: a freshly blacklisted host must not be served as
    # "clean" for long. Domain age (registration date) is effectively immutable
    # and infrastructure (DNS/hosting) changes slowly, so both cache far longer
    # to cut repeated GET/SETEX traffic against Redis.
    analysis_cache_reputation_ttl_seconds: int = 600
    analysis_cache_domain_age_ttl_seconds: int = 604_800
    analysis_cache_infrastructure_ttl_seconds: int = 21_600
    reputation_consensus_threshold: int = 2
    reputation_circuit_breaker_failure_threshold: int = 3
    reputation_circuit_breaker_reset_seconds: float = 30.0
    openphish_reputation_enabled: bool = False
    openphish_feed_url: str = "https://openphish.com/feed.txt"
    openphish_feed_refresh_seconds: float = 1_800.0
    openphish_feed_timeout_seconds: float = 5.0
    openphish_reputation_confidence: float = 95.0
    scan_job_key_prefix: str = "verifiko:scan"
    scan_job_ttl_seconds: int = 86_400
    scan_worker_max_workers: int = 4
    scan_webhook_signing_secret: str = "verifiko-dev-webhook-secret"
    scan_webhook_timeout_seconds: float = 5.0
    scan_webhook_max_attempts: int = 3
    resend_api_key: str = ""
    magic_link_from_email: str = "login@verifiko.es"
    magic_link_base_url: str = "https://www.verifiko.es"
    magic_link_ttl_seconds: int = 900
    magic_link_store_key_prefix: str = "verifiko:magic-link"
    magic_link_request_limit_requests: int = 5
    magic_link_request_limit_window_seconds: int = 300
    trusted_proxy_ips: str = ""
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

    @property
    def trusted_proxy_networks(self) -> list[IPv4Network | IPv6Network]:
        return [
            ip_network(entry.strip(), strict=False)
            for entry in self.trusted_proxy_ips.split(",")
            if entry.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
