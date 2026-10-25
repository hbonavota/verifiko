from abc import ABC, abstractmethod

from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.risk_assessment import RiskAssessment


class ScoringService(ABC):
    @abstractmethod
    def calculate(
        self, signals: list[AnalysisSignal], calculation_version: str
    ) -> RiskAssessment:
        raise NotImplementedError
