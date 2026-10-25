from enum import Enum


# Kept as (str, Enum): StrEnum would change str()/format() of members.
class VerificationJobStatus(str, Enum):  # noqa: UP042
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
