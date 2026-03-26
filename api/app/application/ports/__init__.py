from app.application.ports.domain_age_lookup import (
    DomainAgeLookupPort,
    DomainRegistrationInfo,
    DomainRegistrationLookupError,
)
from app.application.ports.html_fetcher import (
    FetchedHtmlDocument,
    HtmlFetchError,
    HtmlFetcherPort,
)
from app.application.ports.tls_validator import (
    TlsValidationError,
    TlsValidationResult,
    TlsValidatorPort,
)
from app.application.ports.redirect_resolver import (
    RedirectHop,
    RedirectResolution,
    RedirectResolutionError,
    RedirectResolverPort,
)
from app.application.ports.reputation_lookup import (
    ReputationLookupError,
    ReputationLookupPort,
    ReputationMatch,
)

__all__ = [
    "DomainAgeLookupPort",
    "DomainRegistrationInfo",
    "DomainRegistrationLookupError",
    "FetchedHtmlDocument",
    "HtmlFetchError",
    "HtmlFetcherPort",
    "TlsValidationError",
    "TlsValidationResult",
    "TlsValidatorPort",
    "RedirectHop",
    "RedirectResolution",
    "RedirectResolutionError",
    "RedirectResolverPort",
    "ReputationLookupError",
    "ReputationLookupPort",
    "ReputationMatch",
]
