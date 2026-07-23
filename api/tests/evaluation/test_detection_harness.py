from dataclasses import dataclass

from evaluation.corpus import CorpusSample, load_corpus
from evaluation.decision import DecisionPolicy
from evaluation.harness import DetectionHarness
from evaluation.labels import Label
from evaluation.offline_pipeline import ClassifiedResult


@dataclass
class _FixedRiskClassifier:
    """Deterministic stand-in that maps each URL to a preset risk level."""

    by_url: dict[str, str]

    def classify(self, sample: CorpusSample) -> ClassifiedResult:
        return ClassifiedResult(
            risk_level=self.by_url[sample.url],
            score=0.0,
            verdict="STUB",
            terminal_override=False,
            signal_types=(),
            analysis_warnings=(),
        )


def _sample(url: str, label: Label) -> CorpusSample:
    return CorpusSample(url=url, label=label)


def test_harness_reports_false_positives_and_false_negatives() -> None:
    corpus = [
        _sample("https://flagged-benign.example/", Label.BENIGN),  # -> HIGH  => FP
        _sample("https://missed-malicious.example/", Label.MALICIOUS),  # -> SAFE => FN
        _sample("https://caught.example/", Label.MALICIOUS),  # -> CRITICAL => TP
        _sample("https://clean.example/", Label.BENIGN),  # -> SAFE => TN
    ]
    classifier = _FixedRiskClassifier(
        by_url={
            "https://flagged-benign.example/": "HIGH",
            "https://missed-malicious.example/": "SAFE",
            "https://caught.example/": "CRITICAL",
            "https://clean.example/": "SAFE",
        }
    )
    harness = DetectionHarness(classifier=classifier, policy=DecisionPolicy("MEDIUM"))

    report = harness.evaluate(corpus)

    assert (report.matrix.true_positive, report.matrix.false_positive) == (1, 1)
    assert (report.matrix.true_negative, report.matrix.false_negative) == (1, 1)
    assert {item.sample.url for item in report.false_positives} == {"https://flagged-benign.example/"}
    assert {item.sample.url for item in report.false_negatives} == {"https://missed-malicious.example/"}
    assert "Precision" in report.render()


def test_decision_policy_threshold_shifts_predictions() -> None:
    result = ClassifiedResult(
        risk_level="MEDIUM",
        score=50.0,
        verdict="SUSPICIOUS",
        terminal_override=False,
        signal_types=(),
        analysis_warnings=(),
    )

    assert DecisionPolicy("LOW").predict(result) is Label.MALICIOUS
    assert DecisionPolicy("MEDIUM").predict(result) is Label.MALICIOUS
    assert DecisionPolicy("HIGH").predict(result) is Label.BENIGN


# --- Regression gate over the real offline detection pipeline ---------------


def test_bundled_corpus_is_non_trivial_and_balanced() -> None:
    corpus = load_corpus()

    assert len(corpus) >= 30
    labels = {sample.label for sample in corpus}
    assert labels == {Label.MALICIOUS, Label.BENIGN}


def test_detection_quality_meets_precision_and_fpr_floor_at_medium() -> None:
    """Guards the high-value property: official/benign traffic is not flagged.

    Baseline at the MEDIUM threshold: precision 1.00, recall 0.78, FPR 0.00.
    Thresholds sit below baseline so this fails only on a real regression.
    """
    report = DetectionHarness(policy=DecisionPolicy("MEDIUM")).evaluate(load_corpus())

    assert report.matrix.precision >= 0.90, report.render()
    assert report.matrix.false_positive_rate <= 0.05, report.render()
    assert report.matrix.recall >= 0.72, report.render()


def test_detection_separates_malicious_from_benign_at_safe_boundary() -> None:
    """At the LOW threshold (anything not SAFE is flagged) the current corpus is
    perfectly separated: recall 1.00 with zero false positives."""
    report = DetectionHarness(policy=DecisionPolicy("LOW")).evaluate(load_corpus())

    assert report.matrix.recall >= 0.95, report.render()
    assert report.matrix.false_positive_rate <= 0.05, report.render()


def test_official_auth_flows_are_never_flagged() -> None:
    report = DetectionHarness(policy=DecisionPolicy("LOW")).evaluate(load_corpus())
    official = {item for item in report.false_positives if "official" in item.sample.note}

    assert official == set(), report.render()
