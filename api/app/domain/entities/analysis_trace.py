from dataclasses import dataclass

from app.domain.entities.analysis_signal import AnalysisSignal


@dataclass(frozen=True, slots=True)
class AnalysisTrace:
    layers_executed: tuple[str, ...]
    signals_by_source: dict[str, tuple[AnalysisSignal, ...]]
    total_signals: int
