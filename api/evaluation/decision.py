from __future__ import annotations

from dataclasses import dataclass

from evaluation.labels import Label
from evaluation.offline_pipeline import ClassifiedResult

# Ordinal severity of each risk level, low to high.
_RISK_ORDER: dict[str, int] = {
    "SAFE": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    """Turns a graded risk assessment into a binary malicious/benign call.

    ``flag_at_or_above`` is the lowest risk level that counts as a malicious
    prediction. The default (``MEDIUM``) treats SAFE/LOW (verdicts TRUSTED and
    CAUTION) as allowed and MEDIUM+ (SUSPICIOUS or worse) as flagged. Tightening
    it to HIGH trades recall for precision; loosening to LOW does the reverse.
    """

    flag_at_or_above: str = "MEDIUM"

    def __post_init__(self) -> None:
        if self.flag_at_or_above not in _RISK_ORDER:
            raise ValueError(f"Unknown risk level: {self.flag_at_or_above!r}")

    def predict(self, result: ClassifiedResult) -> Label:
        if _RISK_ORDER[result.risk_level] >= _RISK_ORDER[self.flag_at_or_above]:
            return Label.MALICIOUS
        return Label.BENIGN
