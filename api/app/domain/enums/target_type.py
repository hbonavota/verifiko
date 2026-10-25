from enum import Enum


# Kept as (str, Enum): StrEnum would change str()/format() of members.
class TargetType(str, Enum):  # noqa: UP042
    URL = "URL"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
