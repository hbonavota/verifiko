from enum import Enum


# Kept as (str, Enum): StrEnum would change str()/format() of members.
class VerdictType(str, Enum):  # noqa: UP042
    TRUSTED = "TRUSTED"
    CAUTION = "CAUTION"
    SUSPICIOUS = "SUSPICIOUS"
    LIKELY_MALICIOUS = "LIKELY_MALICIOUS"
    CONFIRMED_MALICIOUS = "CONFIRMED_MALICIOUS"
