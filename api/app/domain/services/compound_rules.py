from abc import ABC, abstractmethod

from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.enums.signal_type import SignalType


class CompoundRule(ABC):
    name: str

    @abstractmethod
    def evaluate(self, signal_types: set[SignalType]) -> float | None:
        raise NotImplementedError


class BrandNewLookalikeDomainRule(CompoundRule):
    name = "brand_new_lookalike_domain"

    def evaluate(self, signal_types: set[SignalType]) -> float | None:
        lookalike = {
            SignalType.BRAND_IMPERSONATION,
            SignalType.UNICODE_HOMOGRAPH,
            SignalType.ZERO_WIDTH_CHAR_INJECTION,
            SignalType.TLD_TYPOSQUATTING,
        }
        if SignalType.RECENT_DOMAIN_REGISTRATION in signal_types and signal_types.intersection(lookalike):
            return 10
        return None


class CredentialLurePatternRule(CompoundRule):
    name = "credential_lure_pattern"

    def evaluate(self, signal_types: set[SignalType]) -> float | None:
        if {
            SignalType.BRAND_IMPERSONATION,
            SignalType.PHISHING_KEYWORDS,
        }.issubset(signal_types):
            return 10
        return None


class DeceptiveBrandSubdomainRule(CompoundRule):
    name = "deceptive_brand_subdomain_pattern"

    def evaluate(self, signal_types: set[SignalType]) -> float | None:
        if SignalType.DECEPTIVE_BRAND_SUBDOMAIN not in signal_types:
            return None
        if signal_types.intersection(
            {
                SignalType.PHISHING_KEYWORDS,
                SignalType.INSECURE_TRANSPORT,
                SignalType.CREDENTIAL_HARVEST_FORM,
                SignalType.SUSPICIOUS_LOGIN_INTERFACE,
            }
        ):
            return 10
        return None


class EmailFraudStagingPatternRule(CompoundRule):
    name = "email_fraud_staging_pattern"

    def evaluate(self, signal_types: set[SignalType]) -> float | None:
        if {
            SignalType.TACTICAL_EMAIL_STAGING,
            SignalType.RECENT_DOMAIN_REGISTRATION,
        }.issubset(signal_types):
            return 9
        return None


class RedirectedDeceptionPatternRule(CompoundRule):
    name = "redirected_deception_pattern"

    def evaluate(self, signal_types: set[SignalType]) -> float | None:
        if {
            SignalType.SHORTENED_URL,
            SignalType.SUSPICIOUS_REDIRECT_CHAIN,
        }.issubset(signal_types):
            return 7
        return None


def detected_types(signals: list[AnalysisSignal]) -> set[SignalType]:
    return {signal.signal_type for signal in signals if signal.detected}
