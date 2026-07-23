"""Offline detection-quality evaluation harness.

This package measures the quality of Verifiko's URL detection over a labeled
corpus and reports precision/recall/F1/FPR so that every change to the scoring
rules can be evaluated objectively. It exercises the real verification use case
with deterministic, network-free stubs, so results are reproducible in CI.

Nothing under ``app/`` imports this package: it is a development and CI tool
that depends on the application, never the other way around.
"""
