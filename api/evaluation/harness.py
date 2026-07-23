from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from evaluation.corpus import CorpusSample
from evaluation.decision import DecisionPolicy
from evaluation.labels import Label
from evaluation.metrics import ConfusionMatrix, confusion_matrix
from evaluation.offline_pipeline import ClassifiedResult, OfflineDeterministicClassifier


class Classifier(Protocol):
    def classify(self, sample: CorpusSample) -> ClassifiedResult: ...


@dataclass(frozen=True, slots=True)
class SampleEvaluation:
    sample: CorpusSample
    result: ClassifiedResult
    predicted: Label

    @property
    def actual(self) -> Label:
        return self.sample.label

    @property
    def correct(self) -> bool:
        return self.predicted is self.actual

    @property
    def is_false_positive(self) -> bool:
        return self.actual is Label.BENIGN and self.predicted is Label.MALICIOUS

    @property
    def is_false_negative(self) -> bool:
        return self.actual is Label.MALICIOUS and self.predicted is Label.BENIGN


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    matrix: ConfusionMatrix
    evaluations: tuple[SampleEvaluation, ...]
    flag_at_or_above: str

    @property
    def false_positives(self) -> tuple[SampleEvaluation, ...]:
        return tuple(item for item in self.evaluations if item.is_false_positive)

    @property
    def false_negatives(self) -> tuple[SampleEvaluation, ...]:
        return tuple(item for item in self.evaluations if item.is_false_negative)

    def render(self) -> str:
        matrix = self.matrix
        lines = [
            "Verifiko detection evaluation",
            "=============================",
            f"Samples            : {matrix.total} "
            f"({matrix.positives} malicious, {matrix.negatives} benign)",
            f"Decision threshold : flag when risk_level >= {self.flag_at_or_above}",
            "",
            "Confusion matrix (positive class = malicious)",
            f"  TP={matrix.true_positive}  FP={matrix.false_positive}  "
            f"TN={matrix.true_negative}  FN={matrix.false_negative}",
            "",
            f"Precision          : {matrix.precision:.3f}",
            f"Recall             : {matrix.recall:.3f}",
            f"F1                 : {matrix.f1:.3f}",
            f"Specificity        : {matrix.specificity:.3f}",
            f"False positive rate: {matrix.false_positive_rate:.3f}",
            f"Accuracy           : {matrix.accuracy:.3f}",
        ]
        if self.false_positives:
            lines.append("")
            lines.append(f"False positives ({len(self.false_positives)}):")
            lines.extend(
                f"  - {item.sample.url}  -> {item.result.risk_level}"
                f"{_note_suffix(item.sample.note)}"
                for item in self.false_positives
            )
        if self.false_negatives:
            lines.append("")
            lines.append(f"False negatives ({len(self.false_negatives)}):")
            lines.extend(
                f"  - {item.sample.url}  -> {item.result.risk_level}"
                f"{_note_suffix(item.sample.note)}"
                for item in self.false_negatives
            )
        return "\n".join(lines)


def _note_suffix(note: str) -> str:
    return f"  ({note})" if note else ""


class DetectionHarness:
    def __init__(
        self,
        classifier: Classifier | None = None,
        policy: DecisionPolicy | None = None,
    ) -> None:
        self._classifier = classifier or OfflineDeterministicClassifier()
        self._policy = policy or DecisionPolicy()

    def evaluate(self, corpus: list[CorpusSample]) -> EvaluationReport:
        evaluations: list[SampleEvaluation] = []
        for sample in corpus:
            result = self._classifier.classify(sample)
            predicted = self._policy.predict(result)
            evaluations.append(
                SampleEvaluation(sample=sample, result=result, predicted=predicted)
            )
        matrix = confusion_matrix((item.actual, item.predicted) for item in evaluations)
        return EvaluationReport(
            matrix=matrix,
            evaluations=tuple(evaluations),
            flag_at_or_above=self._policy.flag_at_or_above,
        )
