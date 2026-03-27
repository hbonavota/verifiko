from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType

SEVERITY_MULTIPLIERS: dict[SignalSeverity, float] = {
    SignalSeverity.LOW: 0.5,
    SignalSeverity.MEDIUM: 1.0,
    SignalSeverity.HIGH: 1.5,
    SignalSeverity.CRITICAL: 2.0,
}

BASE_SIGNAL_WEIGHTS: dict[SignalType, float] = {
    SignalType.BLACKLIST_MATCH: 30,
    SignalType.SSL_HOSTNAME_MISMATCH: 20,
    SignalType.TLS_VALIDATION_FAILURE: 18,
    SignalType.INSECURE_TRANSPORT: 14,
    SignalType.DECEPTIVE_BRAND_SUBDOMAIN: 20,
    SignalType.CREDENTIAL_HARVEST_FORM: 20,
    SignalType.SUSPICIOUS_LOGIN_INTERFACE: 12,
    SignalType.TACTICAL_EMAIL_STAGING: 16,
    SignalType.BRAND_IMPERSONATION: 18,
    SignalType.RECENT_DOMAIN_REGISTRATION: 14,
    SignalType.IP_ADDRESS_URL: 18,
    SignalType.UNICODE_HOMOGRAPH: 18,
    SignalType.ZERO_WIDTH_CHAR_INJECTION: 18,
    SignalType.HIGH_DOMAIN_ENTROPY: 14,
    SignalType.TLD_TYPOSQUATTING: 12,
    SignalType.MISLEADING_SUBDOMAIN: 14,
    SignalType.SUSPICIOUS_REDIRECT_CHAIN: 10,
    SignalType.SUSPICIOUS_INFRASTRUCTURE_PATTERN: 15,
    SignalType.SHORTENED_URL: 8,
    SignalType.PHISHING_KEYWORDS: 7,
    SignalType.NON_STANDARD_PORT_USAGE: 7,
    SignalType.LOW_INFORMATION_PAGE: 16,
    SignalType.RECOGNIZED_REPUTABLE_DOMAIN: 0,
}

CATEGORY_CAPS: dict[SignalCategory, float] = {
    SignalCategory.DOMAIN_REPUTATION: 35,
    SignalCategory.DOMAIN_STRUCTURE: 40,
    SignalCategory.NETWORK_TRANSPORT: 30,
    SignalCategory.NAVIGATION_BEHAVIOR: 20,
    SignalCategory.CONTENT_BEHAVIOR: 15,
}

SIGNAL_CATEGORY_MAP: dict[SignalType, SignalCategory] = {
    SignalType.RECENT_DOMAIN_REGISTRATION: SignalCategory.DOMAIN_REPUTATION,
    SignalType.BLACKLIST_MATCH: SignalCategory.DOMAIN_REPUTATION,
    SignalType.DECEPTIVE_BRAND_SUBDOMAIN: SignalCategory.DOMAIN_STRUCTURE,
    SignalType.CREDENTIAL_HARVEST_FORM: SignalCategory.CONTENT_BEHAVIOR,
    SignalType.SUSPICIOUS_LOGIN_INTERFACE: SignalCategory.CONTENT_BEHAVIOR,
    SignalType.TLS_VALIDATION_FAILURE: SignalCategory.NETWORK_TRANSPORT,
    SignalType.INSECURE_TRANSPORT: SignalCategory.NETWORK_TRANSPORT,
    SignalType.SSL_HOSTNAME_MISMATCH: SignalCategory.NETWORK_TRANSPORT,
    SignalType.NON_STANDARD_PORT_USAGE: SignalCategory.NETWORK_TRANSPORT,
    SignalType.TACTICAL_EMAIL_STAGING: SignalCategory.CONTENT_BEHAVIOR,
    SignalType.BRAND_IMPERSONATION: SignalCategory.CONTENT_BEHAVIOR,
    SignalType.MISLEADING_SUBDOMAIN: SignalCategory.DOMAIN_STRUCTURE,
    SignalType.IP_ADDRESS_URL: SignalCategory.DOMAIN_STRUCTURE,
    SignalType.UNICODE_HOMOGRAPH: SignalCategory.DOMAIN_STRUCTURE,
    SignalType.ZERO_WIDTH_CHAR_INJECTION: SignalCategory.DOMAIN_STRUCTURE,
    SignalType.HIGH_DOMAIN_ENTROPY: SignalCategory.DOMAIN_STRUCTURE,
    SignalType.TLD_TYPOSQUATTING: SignalCategory.DOMAIN_STRUCTURE,
    SignalType.SHORTENED_URL: SignalCategory.NAVIGATION_BEHAVIOR,
    SignalType.SUSPICIOUS_REDIRECT_CHAIN: SignalCategory.NAVIGATION_BEHAVIOR,
    SignalType.SUSPICIOUS_INFRASTRUCTURE_PATTERN: SignalCategory.DOMAIN_REPUTATION,
    SignalType.PHISHING_KEYWORDS: SignalCategory.CONTENT_BEHAVIOR,
    SignalType.LOW_INFORMATION_PAGE: SignalCategory.CONTENT_BEHAVIOR,
    SignalType.RECOGNIZED_REPUTABLE_DOMAIN: SignalCategory.DOMAIN_REPUTATION,
}
