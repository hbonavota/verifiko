from enum import Enum


class SignalCategory(str, Enum):
    DOMAIN_REPUTATION = "domain_reputation"
    DOMAIN_STRUCTURE = "domain_structure"
    NETWORK_TRANSPORT = "network_transport"
    NAVIGATION_BEHAVIOR = "navigation_behavior"
    CONTENT_BEHAVIOR = "content_behavior"
