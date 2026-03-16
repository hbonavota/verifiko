from enum import Enum


class SignalType(str, Enum):
    RECENT_DOMAIN_REGISTRATION = "recent_domain_registration"
    BLACKLIST_MATCH = "blacklist_match"
    SSL_HOSTNAME_MISMATCH = "ssl_hostname_mismatch"
    NON_STANDARD_PORT_USAGE = "non_standard_port_usage"
    TACTICAL_EMAIL_STAGING = "tactical_email_staging"
    BRAND_IMPERSONATION = "brand_impersonation"
    MISLEADING_SUBDOMAIN = "misleading_subdomain"
    IP_ADDRESS_URL = "ip_address_url"
    UNICODE_HOMOGRAPH = "unicode_homograph"
    ZERO_WIDTH_CHAR_INJECTION = "zero_width_char_injection"
    HIGH_DOMAIN_ENTROPY = "high_domain_entropy"
    TLD_TYPOSQUATTING = "tld_typosquatting"
    SHORTENED_URL = "shortened_url"
    SUSPICIOUS_REDIRECT_CHAIN = "suspicious_redirect_chain"
    PHISHING_KEYWORDS = "phishing_keywords"
