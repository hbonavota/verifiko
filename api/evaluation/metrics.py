from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from evaluation.labels import Label


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


@dataclass(frozen=True, slots=True)
class ConfusionMatrix:
    """Binary confusion matrix with MALICIOUS as the positive class."""

    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int

    @property
    def total(self) -> int:
        return (
            self.true_positive
            + self.false_positive
            + self.true_negative
            + self.false_negative
        )

    @property
    def positives(self) -> int:
        """Number of actually-malicious samples."""
        return self.true_positive + self.false_negative

    @property
    def negatives(self) -> int:
        """Number of actually-benign samples."""
        return self.true_negative + self.false_positive

    @property
    def precision(self) -> float:
        return _safe_ratio(self.true_positive, self.true_positive + self.false_positive)

    @property
    def recall(self) -> float:
        return _safe_ratio(self.true_positive, self.true_positive + self.false_negative)

    @property
    def specificity(self) -> float:
        return _safe_ratio(self.true_negative, self.true_negative + self.false_positive)

    @property
    def false_positive_rate(self) -> float:
        return _safe_ratio(self.false_positive, self.true_negative + self.false_positive)

    @property
    def f1(self) -> float:
        precision = self.precision
        recall = self.recall
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    @property
    def accuracy(self) -> float:
        return _safe_ratio(self.true_positive + self.true_negative, self.total)


def confusion_matrix(pairs: Iterable[tuple[Label, Label]]) -> ConfusionMatrix:
    """Build a confusion matrix from (actual, predicted) label pairs."""
    tp = fp = tn = fn = 0
    for actual, predicted in pairs:
        if actual is Label.MALICIOUS and predicted is Label.MALICIOUS:
            tp += 1
        elif actual is Label.BENIGN and predicted is Label.MALICIOUS:
            fp += 1
        elif actual is Label.BENIGN and predicted is Label.BENIGN:
            tn += 1
        else:
            fn += 1
    return ConfusionMatrix(
        true_positive=tp,
        false_positive=fp,
        true_negative=tn,
        false_negative=fn,
    )
