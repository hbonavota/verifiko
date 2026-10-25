from enum import Enum


# Kept as (str, Enum): StrEnum would change str()/format() of members.
class SignalCategory(str, Enum):  # noqa: UP042
    DOMAIN_REPUTATION = "domain_reputation"
    DOMAIN_STRUCTURE = "domain_structure"
    NETWORK_TRANSPORT = "network_transport"
    NAVIGATION_BEHAVIOR = "navigation_behavior"
    CONTENT_BEHAVIOR = "content_behavior"
