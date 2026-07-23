import math

from evaluation.labels import Label
from evaluation.metrics import ConfusionMatrix, confusion_matrix


def test_confusion_matrix_counts_each_quadrant() -> None:
    pairs = [
        (Label.MALICIOUS, Label.MALICIOUS),  # TP
        (Label.MALICIOUS, Label.MALICIOUS),  # TP
        (Label.MALICIOUS, Label.MALICIOUS),  # TP
        (Label.BENIGN, Label.MALICIOUS),  # FP
        (Label.BENIGN, Label.BENIGN),  # TN
        (Label.BENIGN, Label.BENIGN),  # TN
        (Label.BENIGN, Label.BENIGN),  # TN
        (Label.BENIGN, Label.BENIGN),  # TN
        (Label.MALICIOUS, Label.BENIGN),  # FN
        (Label.MALICIOUS, Label.BENIGN),  # FN
    ]

    matrix = confusion_matrix(pairs)

    assert (matrix.true_positive, matrix.false_positive, matrix.true_negative, matrix.false_negative) == (3, 1, 4, 2)
    assert matrix.total == 10
    assert matrix.positives == 5
    assert matrix.negatives == 5


def test_confusion_matrix_derived_metrics() -> None:
    matrix = ConfusionMatrix(true_positive=3, false_positive=1, true_negative=4, false_negative=2)

    assert math.isclose(matrix.precision, 0.75)
    assert math.isclose(matrix.recall, 0.6)
    assert math.isclose(matrix.specificity, 0.8)
    assert math.isclose(matrix.false_positive_rate, 0.2)
    assert math.isclose(matrix.accuracy, 0.7)
    assert math.isclose(matrix.f1, 2 * 0.75 * 0.6 / (0.75 + 0.6))


def test_metrics_are_zero_safe_on_empty_input() -> None:
    matrix = confusion_matrix([])

    assert matrix.total == 0
    assert matrix.precision == 0.0
    assert matrix.recall == 0.0
    assert matrix.f1 == 0.0
    assert matrix.false_positive_rate == 0.0
