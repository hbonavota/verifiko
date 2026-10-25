"""CLI runner for the detection evaluation harness.

Usage (from the ``api`` directory):

    python -m evaluation.run_evaluation
    python -m evaluation.run_evaluation --flag-at-or-above HIGH
    python -m evaluation.run_evaluation --min-precision 0.9 --min-recall 0.8 --max-fpr 0.1

Exits non-zero when any provided threshold is not met, so it can gate CI.
"""  # noqa: E501 (usage example)

from __future__ import annotations

import argparse
import sys

from evaluation.corpus import DEFAULT_CORPUS_PATH, load_corpus
from evaluation.decision import DecisionPolicy
from evaluation.harness import DetectionHarness


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate Verifiko URL detection quality."
    )
    parser.add_argument(
        "--corpus", default=str(DEFAULT_CORPUS_PATH), help="Path to a JSONL corpus."
    )
    parser.add_argument(
        "--flag-at-or-above",
        default="MEDIUM",
        choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        help="Lowest risk level counted as a malicious prediction.",
    )
    parser.add_argument("--min-precision", type=float, default=None)
    parser.add_argument("--min-recall", type=float, default=None)
    parser.add_argument("--max-fpr", type=float, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    corpus = load_corpus(args.corpus)
    harness = DetectionHarness(
        policy=DecisionPolicy(flag_at_or_above=args.flag_at_or_above)
    )
    report = harness.evaluate(corpus)
    print(report.render())

    failures: list[str] = []
    matrix = report.matrix
    if args.min_precision is not None and matrix.precision < args.min_precision:
        failures.append(f"precision {matrix.precision:.3f} < {args.min_precision}")
    if args.min_recall is not None and matrix.recall < args.min_recall:
        failures.append(f"recall {matrix.recall:.3f} < {args.min_recall}")
    if args.max_fpr is not None and matrix.false_positive_rate > args.max_fpr:
        failures.append(
            f"false positive rate {matrix.false_positive_rate:.3f} > {args.max_fpr}"
        )

    if failures:
        print("\nTHRESHOLDS NOT MET:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
