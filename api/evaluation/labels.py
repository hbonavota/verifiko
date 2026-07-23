from enum import Enum


class Label(str, Enum):
    """Ground-truth (and predicted) class for a corpus sample.

    ``MALICIOUS`` is treated as the positive class for all metrics.
    """

    MALICIOUS = "malicious"
    BENIGN = "benign"
