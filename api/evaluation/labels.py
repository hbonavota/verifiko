from enum import Enum


# Kept as (str, Enum): StrEnum would change str()/format() of members.
class Label(str, Enum):  # noqa: UP042
    """Ground-truth (and predicted) class for a corpus sample.

    ``MALICIOUS`` is treated as the positive class for all metrics.
    """

    MALICIOUS = "malicious"
    BENIGN = "benign"
