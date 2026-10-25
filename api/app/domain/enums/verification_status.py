from enum import Enum


# Kept as (str, Enum): StrEnum would change str()/format() of members.
class VerificationStatus(str, Enum):  # noqa: UP042
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
