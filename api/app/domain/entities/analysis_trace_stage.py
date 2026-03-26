from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalysisTraceStage:
    stage: str
    source: str
    status: str
    signal_count: int
    signal_titles: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
