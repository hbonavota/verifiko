from enum import Enum


# Kept as (str, Enum): StrEnum would change str()/format() of members.
class RiskLevel(str, Enum):  # noqa: UP042
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
