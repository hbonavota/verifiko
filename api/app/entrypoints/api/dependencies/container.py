from functools import lru_cache

from app.application.ports.auth_token_service import AuthTokenServicePort
from app.application.ports.google_identity_verifier import GoogleIdentityVerifierPort
from app.application.ports.password_hasher import PasswordHasherPort
from app.application.services.quota_status_service import QuotaStatusService
from app.application.services.domain_recency_signal_analyzer import DomainRecencySignalAnalyzer
from app.domain.services.user_quota_policy import UserQuotaPolicy
from app.application.services.html_credential_signal_analyzer import HtmlCredentialSignalAnalyzer
from app.infrastructure.security.authenticated_utc_day_quota_limiter import (
    AuthenticatedUtcDayQuotaLimiter,
)
from app.application.services.infrastructure_signal_analyzer import (
    InfrastructureSignalAnalyzer,
)
from app.application.services.redirect_signal_analyzer import RedirectSignalAnalyzer
from app.application.services.reputation_signal_analyzer import ReputationSignalAnalyzer
from app.application.services.resolved_destination_signal_analyzer import (
    ResolvedDestinationSignalAnalyzer,
)
from app.application.services.transport_security_signal_analyzer import (
    TransportSecuritySignalAnalyzer,
)
from app.application.services.url_signal_analyzer import DeterministicUrlSignalAnalyzer
from app.application.use_cases.authenticate_with_email_password import (
    AuthenticateWithEmailPasswordUseCase,
)
from app.application.use_cases.authenticate_with_google import AuthenticateWithGoogleUseCase
from app.application.use_cases.create_url_verification import CreateURLVerificationUseCase
from app.application.use_cases.get_verification_result import GetVerificationResultUseCase
from app.application.use_cases.get_owned_verification_result import GetOwnedVerificationResultUseCase
from app.application.use_cases.list_verifications import ListVerificationsUseCase
from app.application.use_cases.list_owned_verifications import ListOwnedVerificationsUseCase
from app.application.use_cases.register_with_email_password import (
    RegisterWithEmailPasswordUseCase,
)
from app.infrastructure.external_services.google.google_tokeninfo_identity_verifier import (
    GoogleTokeninfoIdentityVerifier,
)
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.infrastructure.external_services.blacklist.urlhaus_reputation_client import (
    UrlhausReputationClient,
)
from app.infrastructure.external_services.domain_age.rdap_domain_age_lookup import RdapDomainAgeLookup
from app.infrastructure.external_services.dns.socket_infrastructure_lookup import (
    SocketInfrastructureLookup,
)
from app.infrastructure.external_services.html.simple_html_fetcher import SimpleHtmlFetcher
from app.infrastructure.external_services.outbound_target_guard import assert_safe_outbound_url
from app.infrastructure.external_services.redirects.http_redirect_resolver import (
    HttpRedirectResolver,
)
from app.infrastructure.external_services.tls.tls_client import SocketTlsValidator
from app.infrastructure.ids.id_generator import UUIDVerificationIdGenerator
from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.database import get_session_factory
from app.infrastructure.persistence.repositories.sqlalchemy_verification_repository import (
    SQLAlchemyVerificationRepository,
)
from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from app.infrastructure.security.fixed_window_rate_limiter import FixedWindowRateLimiter
from app.infrastructure.security.redis_client import build_redis_client
from app.infrastructure.security.redis_fixed_window_rate_limiter import (
    RedisFixedWindowRateLimiter,
)
from app.infrastructure.security.redis_utc_day_quota_limiter import (
    RedisAuthenticatedUtcDayQuotaLimiter,
    RedisUtcDayQuotaLimiter,
)
from app.infrastructure.security.signed_auth_token_service import SignedAuthTokenService
from app.infrastructure.security.utc_day_quota_limiter import UtcDayQuotaLimiter
from app.infrastructure.time.system_time_provider import SystemTimeProvider


@lru_cache(maxsize=1)
def get_verification_repository() -> SQLAlchemyVerificationRepository:
    return SQLAlchemyVerificationRepository(session_factory=get_session_factory())


@lru_cache(maxsize=1)
def get_user_repository() -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(session_factory=get_session_factory())


@lru_cache(maxsize=1)
def get_id_generator() -> UUIDVerificationIdGenerator:
    return UUIDVerificationIdGenerator()


@lru_cache(maxsize=1)
def get_risk_scoring_engine() -> RiskScoringEngine:
    return RiskScoringEngine()


@lru_cache(maxsize=1)
def get_url_signal_analyzer() -> DeterministicUrlSignalAnalyzer:
    return DeterministicUrlSignalAnalyzer()


@lru_cache(maxsize=1)
def get_domain_age_lookup() -> RdapDomainAgeLookup:
    return RdapDomainAgeLookup()


@lru_cache(maxsize=1)
def get_time_provider() -> SystemTimeProvider:
    return SystemTimeProvider()


@lru_cache(maxsize=1)
def get_domain_recency_signal_analyzer() -> DomainRecencySignalAnalyzer:
    return DomainRecencySignalAnalyzer(
        domain_age_lookup=get_domain_age_lookup(),
        current_time_provider=get_time_provider().now,
    )


@lru_cache(maxsize=1)
def get_html_fetcher() -> SimpleHtmlFetcher:
    return SimpleHtmlFetcher()


@lru_cache(maxsize=1)
def get_html_credential_signal_analyzer() -> HtmlCredentialSignalAnalyzer:
    return HtmlCredentialSignalAnalyzer()


@lru_cache(maxsize=1)
def get_redirect_resolver() -> HttpRedirectResolver:
    return HttpRedirectResolver()


@lru_cache(maxsize=1)
def get_redirect_signal_analyzer() -> RedirectSignalAnalyzer:
    return RedirectSignalAnalyzer(redirect_resolver=get_redirect_resolver())


@lru_cache(maxsize=1)
def get_reputation_lookup() -> UrlhausReputationClient:
    return UrlhausReputationClient()


@lru_cache(maxsize=1)
def get_reputation_signal_analyzer() -> ReputationSignalAnalyzer:
    return ReputationSignalAnalyzer(reputation_lookup=get_reputation_lookup())


@lru_cache(maxsize=1)
def get_infrastructure_lookup() -> SocketInfrastructureLookup:
    return SocketInfrastructureLookup()


@lru_cache(maxsize=1)
def get_infrastructure_signal_analyzer() -> InfrastructureSignalAnalyzer:
    return InfrastructureSignalAnalyzer(infrastructure_lookup=get_infrastructure_lookup())


@lru_cache(maxsize=1)
def get_resolved_destination_signal_analyzer() -> ResolvedDestinationSignalAnalyzer:
    return ResolvedDestinationSignalAnalyzer(
        url_signal_analyzer=get_url_signal_analyzer(),
        html_fetcher=get_html_fetcher(),
        html_credential_signal_analyzer=get_html_credential_signal_analyzer(),
    )


@lru_cache(maxsize=1)
def get_tls_validator() -> SocketTlsValidator:
    return SocketTlsValidator()


@lru_cache(maxsize=1)
def get_transport_security_signal_analyzer() -> TransportSecuritySignalAnalyzer:
    return TransportSecuritySignalAnalyzer(tls_validator=get_tls_validator())


@lru_cache(maxsize=1)
def get_create_verification_rate_limiter() -> UtcDayQuotaLimiter:
    settings = get_settings()
    redis_client = get_rate_limit_redis_client()
    if redis_client is not None:
        return RedisUtcDayQuotaLimiter(
            redis_client=redis_client,
            daily_limit=settings.anonymous_daily_verification_limit,
            current_time_provider=get_time_provider().now,
            key_prefix=f"{settings.rate_limit_key_prefix}:anonymous",
        )
    return UtcDayQuotaLimiter(
        daily_limit=settings.anonymous_daily_verification_limit,
        current_time_provider=get_time_provider().now,
    )


@lru_cache(maxsize=1)
def get_create_verification_burst_rate_limiter():
    settings = get_settings()
    redis_client = get_rate_limit_redis_client()
    if redis_client is not None:
        return RedisFixedWindowRateLimiter(
            redis_client=redis_client,
            max_requests=settings.verification_burst_limit_requests,
            window_seconds=settings.verification_burst_limit_window_seconds,
            key_prefix=f"{settings.rate_limit_key_prefix}:burst:verifications",
        )
    return FixedWindowRateLimiter(
        max_requests=settings.verification_burst_limit_requests,
        window_seconds=settings.verification_burst_limit_window_seconds,
    )


@lru_cache(maxsize=1)
def get_user_quota_policy() -> UserQuotaPolicy:
    settings = get_settings()
    return UserQuotaPolicy(
        free_daily_limit=settings.free_authenticated_daily_verification_limit,
        pro_daily_limit=settings.pro_authenticated_daily_verification_limit,
    )


@lru_cache(maxsize=1)
def get_authenticated_verification_rate_limiter() -> AuthenticatedUtcDayQuotaLimiter:
    settings = get_settings()
    redis_client = get_rate_limit_redis_client()
    if redis_client is not None:
        return RedisAuthenticatedUtcDayQuotaLimiter(
            redis_client=redis_client,
            quota_policy=get_user_quota_policy(),
            current_time_provider=get_time_provider().now,
            key_prefix=f"{settings.rate_limit_key_prefix}:user",
        )
    return AuthenticatedUtcDayQuotaLimiter(
        quota_policy=get_user_quota_policy(),
        current_time_provider=get_time_provider().now,
    )


@lru_cache(maxsize=1)
def get_quota_status_service() -> QuotaStatusService:
    return QuotaStatusService(
        anonymous_quota_limiter=get_create_verification_rate_limiter(),
        authenticated_quota_limiter=get_authenticated_verification_rate_limiter(),
    )


@lru_cache(maxsize=1)
def get_rate_limit_redis_client():
    redis_url = get_settings().redis_url
    if not redis_url:
        return None
    return build_redis_client(redis_url)


@lru_cache(maxsize=1)
def get_google_identity_verifier() -> GoogleIdentityVerifierPort:
    settings = get_settings()
    return GoogleTokeninfoIdentityVerifier(client_id=settings.google_client_id)


@lru_cache(maxsize=1)
def get_auth_token_service() -> AuthTokenServicePort:
    settings = get_settings()
    return SignedAuthTokenService(
        secret=settings.auth_token_secret,
        ttl_seconds=settings.auth_token_ttl_seconds,
    )


@lru_cache(maxsize=1)
def get_password_hasher() -> PasswordHasherPort:
    return Argon2PasswordHasher()


def get_create_url_verification_use_case() -> CreateURLVerificationUseCase:
    return CreateURLVerificationUseCase(
        repository=get_verification_repository(),
        id_generator=get_id_generator(),
        scoring_service=get_risk_scoring_engine(),
        signal_analyzer=get_url_signal_analyzer(),
        domain_recency_signal_analyzer=get_domain_recency_signal_analyzer(),
        redirect_signal_analyzer=get_redirect_signal_analyzer(),
        reputation_signal_analyzer=get_reputation_signal_analyzer(),
        infrastructure_signal_analyzer=get_infrastructure_signal_analyzer(),
        resolved_destination_signal_analyzer=get_resolved_destination_signal_analyzer(),
        html_fetcher=get_html_fetcher(),
        html_credential_signal_analyzer=get_html_credential_signal_analyzer(),
        transport_security_signal_analyzer=get_transport_security_signal_analyzer(),
        public_target_validator=assert_safe_outbound_url,
    )


def get_get_verification_result_use_case() -> GetVerificationResultUseCase:
    return GetVerificationResultUseCase(repository=get_verification_repository())


def get_list_verifications_use_case() -> ListVerificationsUseCase:
    return ListVerificationsUseCase(repository=get_verification_repository())


def get_authenticate_with_google_use_case() -> AuthenticateWithGoogleUseCase:
    return AuthenticateWithGoogleUseCase(
        google_identity_verifier=get_google_identity_verifier(),
        user_repository=get_user_repository(),
        auth_token_service=get_auth_token_service(),
    )


def get_register_with_email_password_use_case() -> RegisterWithEmailPasswordUseCase:
    return RegisterWithEmailPasswordUseCase(
        user_repository=get_user_repository(),
        password_hasher=get_password_hasher(),
        auth_token_service=get_auth_token_service(),
    )


def get_authenticate_with_email_password_use_case() -> AuthenticateWithEmailPasswordUseCase:
    return AuthenticateWithEmailPasswordUseCase(
        user_repository=get_user_repository(),
        password_hasher=get_password_hasher(),
        auth_token_service=get_auth_token_service(),
    )


def get_get_owned_verification_result_use_case() -> GetOwnedVerificationResultUseCase:
    return GetOwnedVerificationResultUseCase(repository=get_verification_repository())


def get_list_owned_verifications_use_case() -> ListOwnedVerificationsUseCase:
    return ListOwnedVerificationsUseCase(repository=get_verification_repository())
