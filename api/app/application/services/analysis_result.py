from dataclasses import dataclass

from app.domain.entities.analysis_signal import AnalysisSignal


@dataclass(frozen=True, slots=True)
class SignalAnalysisResult:
    signals: tuple[AnalysisSignal, ...] = ()
    warnings: tuple[str, ...] = ()
