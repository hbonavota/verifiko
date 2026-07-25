from functools import lru_cache

from app.application.ports.auth_token_service import AuthTokenServicePort
from app.application.ports.google_identity_verifier import GoogleIdentityVerifierPort
from app.application.ports.password_hasher import PasswordHasherPort
from app.application.services.quota_status_service import QuotaStatusService
from app.application.services.domain_recency_signal_analyzer import DomainRecencySignalAnalyzer
from app.domain.services.user_quota_policy import UserQuotaPolicy
from app.application.services.html_credential_signal_analyzer import HtmlCredentialSignalAnalyzer
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
from app.application.ports.api_key_token_service import ApiKeyTokenServicePort
from app.application.ports.domain_age_lookup import DomainAgeLookupPort
from app.application.ports.infrastructure_lookup import InfrastructureLookupPort
from app.application.ports.reputation_lookup import ReputationLookupPort
from app.application.use_cases.authenticate_with_api_key import AuthenticateWithApiKeyUseCase
from app.application.use_cases.authenticate_with_email_password import (
    AuthenticateWithEmailPasswordUseCase,
)
from app.application.use_cases.authenticate_with_google import AuthenticateWithGoogleUseCase
from app.application.services.behavioral_signal_analyzer import BehavioralSignalAnalyzer
from app.application.ports.headless_detonation import HeadlessDetonationPort
from app.application.services.verification_scan_processor import VerificationScanProcessor
from app.domain.services.detonation_policy import DetonationPolicy
from app.application.ports.screenshot_store import ScreenshotStorePort
from app.infrastructure.detonation.browserless_detonation_client import (
    BrowserlessDetonationClient,
    NullHeadlessDetonation,
    build_urllib_detonation_poster,
)
from app.infrastructure.storage.screenshot_store import (
    NullScreenshotStore,
    R2ScreenshotStore,
    build_r2_s3_client,
)
from app.application.use_cases.authenticate_with_magic_link import (
    AuthenticateWithMagicLinkUseCase,
)
from app.application.use_cases.create_api_key import CreateApiKeyUseCase
from app.application.use_cases.request_magic_link import RequestMagicLinkUseCase
from app.application.use_cases.get_verification_scan import GetVerificationScanUseCase
from app.application.use_cases.list_api_keys import ListApiKeysUseCase
from app.application.use_cases.revoke_api_key import RevokeApiKeyUseCase
from app.application.use_cases.submit_verification_scan import SubmitVerificationScanUseCase
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
from app.infrastructure.persistence.repositories.sqlalchemy_magic_link_store import (
    SqlAlchemyMagicLinkStore,
)
from app.infrastructure.email.logging_email_sender import LoggingEmailSender
from app.infrastructure.email.resend_email_sender import (
    ResendEmailSender,
    build_urllib_email_poster,
)
from app.infrastructure.jobs.scan_dispatchers import ThreadPoolVerificationJobDispatcher
from app.infrastructure.webhooks.http_scan_webhook_notifier import (
    HttpScanWebhookNotifier,
    build_urllib_webhook_poster,
)
from app.domain.services.risk_scoring_engine import RiskScoringEngine
from app.infrastructure.cache.caching_domain_age_lookup import CachingDomainAgeLookup
from app.infrastructure.cache.caching_infrastructure_lookup import CachingInfrastructureLookup
from app.infrastructure.cache.caching_reputation_lookup import CachingReputationLookup
from app.infrastructure.cache.json_redis_cache import JsonRedisCache
from app.infrastructure.external_services.blacklist.urlhaus_reputation_client import (
    UrlhausReputationClient,
)
from app.infrastructure.reputation.aggregating_reputation_lookup import (
    AggregatingReputationLookup,
)
from app.infrastructure.reputation.circuit_breaker_reputation_lookup import (
    CircuitBreakerReputationLookup,
)
from app.infrastructure.reputation.openphish_reputation_client import (
    OpenPhishReputationClient,
    build_openphish_feed_fetcher,
)
from app.infrastructure.resilience.circuit_breaker import CircuitBreaker
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
from app.infrastructure.persistence.repositories.sqlalchemy_api_key_repository import (
    SQLAlchemyApiKeyRepository,
)
from app.infrastructure.persistence.repositories.sqlalchemy_verification_job_store import (
    SqlAlchemyVerificationJobStore,
)
from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from app.infrastructure.security.sha256_api_key_token_service import Sha256ApiKeyTokenService
from app.infrastructure.security.fixed_window_rate_limiter import FixedWindowRateLimiter
from app.infrastructure.security.redis_client import build_redis_client
from app.infrastructure.security.redis_fixed_window_rate_limiter import (
    RedisFixedWindowRateLimiter,
)
from app.infrastructure.security.signed_auth_token_service import SignedAuthTokenService
from app.infrastructure.security.sqlalchemy_utc_day_quota_limiter import (
    SqlAlchemyAuthenticatedUtcDayQuotaLimiter,
    SqlAlchemyUtcDayQuotaLimiter,
)
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
def get_domain_age_lookup() -> DomainAgeLookupPort:
    inner = RdapDomainAgeLookup()
    redis_client = get_rate_limit_redis_client()
    if redis_client is None:
        return inner
    settings = get_settings()
    return CachingDomainAgeLookup(
        inner=inner,
        cache=JsonRedisCache(
            redis_client=redis_client,
            key_prefix=settings.analysis_cache_key_prefix,
            ttl_seconds=settings.analysis_cache_domain_age_ttl_seconds,
        ),
    )


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
def get_reputation_lookup() -> ReputationLookupPort:
    settings = get_settings()
    providers = [
        _guarded_reputation_provider(
            UrlhausReputationClient(), "urlhaus.abuse.ch", settings
        ),
    ]
    if settings.openphish_reputation_enabled:
        providers.append(
            _guarded_reputation_provider(
                OpenPhishReputationClient(
                    feed_fetcher=build_openphish_feed_fetcher(
                        feed_url=settings.openphish_feed_url,
                        timeout_seconds=settings.openphish_feed_timeout_seconds,
                    ),
                    refresh_seconds=settings.openphish_feed_refresh_seconds,
                    confidence=settings.openphish_reputation_confidence,
                ),
                "openphish.com",
                settings,
            )
        )

    aggregated: ReputationLookupPort = AggregatingReputationLookup(
        providers=tuple(providers),
        consensus_threshold=settings.reputation_consensus_threshold,
    )

    redis_client = get_rate_limit_redis_client()
    if redis_client is None:
        return aggregated
    return CachingReputationLookup(
        inner=aggregated,
        cache=JsonRedisCache(
            redis_client=redis_client,
            key_prefix=settings.analysis_cache_key_prefix,
            ttl_seconds=settings.analysis_cache_reputation_ttl_seconds,
        ),
    )


def _guarded_reputation_provider(
    inner: ReputationLookupPort,
    provider_name: str,
    settings,
) -> ReputationLookupPort:
    return CircuitBreakerReputationLookup(
        inner=inner,
        breaker=CircuitBreaker(
            failure_threshold=settings.reputation_circuit_breaker_failure_threshold,
            reset_seconds=settings.reputation_circuit_breaker_reset_seconds,
        ),
        provider_name=provider_name,
    )


@lru_cache(maxsize=1)
def get_reputation_signal_analyzer() -> ReputationSignalAnalyzer:
    return ReputationSignalAnalyzer(reputation_lookup=get_reputation_lookup())


@lru_cache(maxsize=1)
def get_infrastructure_lookup() -> InfrastructureLookupPort:
    inner = SocketInfrastructureLookup()
    redis_client = get_rate_limit_redis_client()
    if redis_client is None:
        return inner
    settings = get_settings()
    return CachingInfrastructureLookup(
        inner=inner,
        cache=JsonRedisCache(
            redis_client=redis_client,
            key_prefix=settings.analysis_cache_key_prefix,
            ttl_seconds=settings.analysis_cache_infrastructure_ttl_seconds,
        ),
    )


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
def get_create_verification_rate_limiter() -> SqlAlchemyUtcDayQuotaLimiter:
    # The daily quota lives in Postgres: durable, race-safe (atomic conditional
    # UPSERT), and off the Redis critical path. The Redis limiter classes remain
    # importable for other deployment shapes but are no longer wired here.
    settings = get_settings()
    return SqlAlchemyUtcDayQuotaLimiter(
        session_factory=get_session_factory(),
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
def get_authenticated_verification_rate_limiter() -> SqlAlchemyAuthenticatedUtcDayQuotaLimiter:
    # Postgres-backed per-user daily quota (see the anonymous limiter above).
    return SqlAlchemyAuthenticatedUtcDayQuotaLimiter(
        session_factory=get_session_factory(),
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


@lru_cache(maxsize=1)
def get_api_key_repository() -> SQLAlchemyApiKeyRepository:
    return SQLAlchemyApiKeyRepository(session_factory=get_session_factory())


@lru_cache(maxsize=1)
def get_api_key_token_service() -> ApiKeyTokenServicePort:
    return Sha256ApiKeyTokenService()


def get_create_api_key_use_case() -> CreateApiKeyUseCase:
    return CreateApiKeyUseCase(
        api_key_repository=get_api_key_repository(),
        token_service=get_api_key_token_service(),
        current_time_provider=get_time_provider().now,
    )


def get_list_api_keys_use_case() -> ListApiKeysUseCase:
    return ListApiKeysUseCase(api_key_repository=get_api_key_repository())


def get_revoke_api_key_use_case() -> RevokeApiKeyUseCase:
    return RevokeApiKeyUseCase(
        api_key_repository=get_api_key_repository(),
        current_time_provider=get_time_provider().now,
    )


def get_authenticate_with_api_key_use_case() -> AuthenticateWithApiKeyUseCase:
    return AuthenticateWithApiKeyUseCase(
        api_key_repository=get_api_key_repository(),
        user_repository=get_user_repository(),
        token_service=get_api_key_token_service(),
        current_time_provider=get_time_provider().now,
    )


@lru_cache(maxsize=1)
def get_email_sender():
    settings = get_settings()
    if settings.resend_api_key:
        return ResendEmailSender(
            api_key=settings.resend_api_key,
            from_email=settings.magic_link_from_email,
            http_poster=build_urllib_email_poster(),
        )
    return LoggingEmailSender()


@lru_cache(maxsize=1)
def get_magic_link_store():
    # Backed by the primary database (not Redis), so tokens are durable and
    # shared across serverless invocations independent of the Redis quota.
    return SqlAlchemyMagicLinkStore(
        session_factory=get_session_factory(),
        current_time_provider=get_time_provider().now,
    )


@lru_cache(maxsize=1)
def get_magic_link_request_rate_limiter():
    settings = get_settings()
    redis_client = get_rate_limit_redis_client()
    if redis_client is not None:
        return RedisFixedWindowRateLimiter(
            redis_client=redis_client,
            max_requests=settings.magic_link_request_limit_requests,
            window_seconds=settings.magic_link_request_limit_window_seconds,
            key_prefix=f"{settings.rate_limit_key_prefix}:magic-link",
        )
    return FixedWindowRateLimiter(
        max_requests=settings.magic_link_request_limit_requests,
        window_seconds=settings.magic_link_request_limit_window_seconds,
    )


def get_request_magic_link_use_case() -> RequestMagicLinkUseCase:
    settings = get_settings()
    return RequestMagicLinkUseCase(
        magic_link_store=get_magic_link_store(),
        email_sender=get_email_sender(),
        link_base_url=settings.magic_link_base_url,
        ttl_seconds=settings.magic_link_ttl_seconds,
    )


def get_authenticate_with_magic_link_use_case() -> AuthenticateWithMagicLinkUseCase:
    return AuthenticateWithMagicLinkUseCase(
        magic_link_store=get_magic_link_store(),
        user_repository=get_user_repository(),
        auth_token_service=get_auth_token_service(),
    )


@lru_cache(maxsize=1)
def get_screenshot_store() -> ScreenshotStorePort:
    # Only build the real R2 store when storage is enabled and a bucket +
    # credentials are configured; otherwise the no-op store keeps screenshots off.
    settings = get_settings()
    if (
        settings.screenshot_storage_enabled
        and settings.r2_bucket
        and settings.r2_account_id
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
    ):
        return R2ScreenshotStore(
            s3_client=build_r2_s3_client(
                account_id=settings.r2_account_id,
                access_key_id=settings.r2_access_key_id,
                secret_access_key=settings.r2_secret_access_key,
            ),
            bucket=settings.r2_bucket,
        )
    return NullScreenshotStore()


@lru_cache(maxsize=1)
def get_headless_detonation() -> HeadlessDetonationPort:
    # Only build the real Browserless client when detonation is enabled and an
    # endpoint (which carries the token) is configured. Otherwise fall back to the
    # no-op backend so an accidental call can never fabricate risk.
    settings = get_settings()
    if settings.detonation_enabled and settings.browserless_endpoint:
        return BrowserlessDetonationClient(
            endpoint=settings.browserless_endpoint,
            http_poster=build_urllib_detonation_poster(
                settings.detonation_timeout_seconds
            ),
            capture_screenshot=settings.detonation_capture_screenshot,
            screenshot_store=get_screenshot_store(),
        )
    return NullHeadlessDetonation()


@lru_cache(maxsize=1)
def get_detonation_policy() -> DetonationPolicy:
    return DetonationPolicy()


@lru_cache(maxsize=1)
def get_behavioral_signal_analyzer() -> BehavioralSignalAnalyzer:
    return BehavioralSignalAnalyzer()


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
        parallel_analysis_enabled=get_settings().verification_parallel_analysis_enabled,
        fast_path_enabled=get_settings().verification_fast_path_enabled,
        headless_detonation=get_headless_detonation(),
        detonation_policy=get_detonation_policy(),
        behavioral_signal_analyzer=get_behavioral_signal_analyzer(),
        detonation_enabled=get_settings().detonation_enabled,
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


@lru_cache(maxsize=1)
def get_verification_job_store():
    # Scan job state lives in the primary database: shared across serverless
    # invocations and independent of the Redis command quota. (The in-memory and
    # Redis stores remain available for tests / other deployment shapes.)
    return SqlAlchemyVerificationJobStore(session_factory=get_session_factory())


@lru_cache(maxsize=1)
def get_scan_webhook_notifier() -> HttpScanWebhookNotifier:
    settings = get_settings()
    return HttpScanWebhookNotifier(
        signing_secret=settings.scan_webhook_signing_secret,
        target_validator=assert_safe_outbound_url,
        http_poster=build_urllib_webhook_poster(settings.scan_webhook_timeout_seconds),
        max_attempts=settings.scan_webhook_max_attempts,
        current_time_provider=get_time_provider().now,
    )


@lru_cache(maxsize=1)
def get_verification_scan_processor() -> VerificationScanProcessor:
    return VerificationScanProcessor(
        job_store=get_verification_job_store(),
        create_use_case=get_create_url_verification_use_case(),
        webhook_notifier=get_scan_webhook_notifier(),
        current_time_provider=get_time_provider().now,
    )


@lru_cache(maxsize=1)
def get_verification_scan_dispatcher() -> ThreadPoolVerificationJobDispatcher:
    return ThreadPoolVerificationJobDispatcher(
        processor=get_verification_scan_processor(),
        max_workers=get_settings().scan_worker_max_workers,
    )


def get_submit_verification_scan_use_case() -> SubmitVerificationScanUseCase:
    return SubmitVerificationScanUseCase(
        job_store=get_verification_job_store(),
        dispatcher=get_verification_scan_dispatcher(),
        current_time_provider=get_time_provider().now,
    )


def get_get_verification_scan_use_case() -> GetVerificationScanUseCase:
    return GetVerificationScanUseCase(job_store=get_verification_job_store())


def get_list_owned_verifications_use_case() -> ListOwnedVerificationsUseCase:
    return ListOwnedVerificationsUseCase(repository=get_verification_repository())
