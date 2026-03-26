from dataclasses import dataclass

from app.application.ports.redirect_resolver import RedirectResolution
from app.domain.entities.analysis_signal import AnalysisSignal


@dataclass(frozen=True, slots=True)
class SignalAnalysisResult:
    signals: tuple[AnalysisSignal, ...] = ()
    warnings: tuple[str, ...] = ()
    redirect_resolution: RedirectResolution | None = None
