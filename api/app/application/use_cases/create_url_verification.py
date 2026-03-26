from dataclasses import dataclass

from app.application.commands.create_verification_command import CreateVerificationCommand
from app.application.dto.verification_dto import VerificationDTO
from app.application.mappers.verification_mapper import VerificationMapper
from app.application.ports.html_fetcher import HtmlFetchError, HtmlFetcherPort
from app.application.services.analysis_result import SignalAnalysisResult
from app.application.services.domain_recency_signal_analyzer import DomainRecencySignalAnalyzer
from app.application.services.html_credential_signal_analyzer import HtmlCredentialSignalAnalyzer
from app.application.services.transport_security_signal_analyzer import (
    TransportSecuritySignalAnalyzer,
)
from app.application.services.url_signal_analyzer import DeterministicUrlSignalAnalyzer
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.risk_assessment import RiskAssessment
from app.domain.entities.verification import Verification
from app.domain.ports.id_generator import IdGeneratorPort
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.services.risk_scoring_engine import risk_level_for_score, verdict_for_level
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS
from app.domain.services.scoring_service import ScoringService
from app.domain.value_objects.confidence_score import ConfidenceScore


@dataclass(slots=True)
class CreateURLVerificationUseCase:
    repository: VerificationRepository
    id_generator: IdGeneratorPort
    scoring_service: ScoringService
    signal_analyzer: DeterministicUrlSignalAnalyzer
    domain_recency_signal_analyzer: DomainRecencySignalAnalyzer
    html_fetcher: HtmlFetcherPort
    html_credential_signal_analyzer: HtmlCredentialSignalAnalyzer
    transport_security_signal_analyzer: TransportSecuritySignalAnalyzer

    def execute(self, command: CreateVerificationCommand) -> VerificationDTO:
        verification = Verification.create_url(
            input_url=command.url,
            verification_id=self.id_generator.next_verification_id(),
            calculation_version=command.calculation_version,
        )
        verification.set_analyzing()

        analysis_warnings: list[str] = []
        detected_signals = self.signal_analyzer.analyze(verification.normalized_input)
        domain_recency_result = self.domain_recency_signal_analyzer.analyze_with_context(
            verification.normalized_input
        )
        detected_signals.extend(domain_recency_result.signals)
        analysis_warnings.extend(domain_recency_result.warnings)

        transport_result = self.transport_security_signal_analyzer.analyze_with_context(
            verification.normalized_input
        )
        detected_signals.extend(transport_result.signals)
        analysis_warnings.extend(transport_result.warnings)

        html_result = self._analyze_html_content(verification)
        detected_signals.extend(html_result.signals)
        analysis_warnings.extend(html_result.warnings)
        detected_signals.extend(
            [
                AnalysisSignal.create(
                    signal_type=signal.signal_type,
                    category=signal.category,
                    severity=signal.severity,
                    confidence=ConfidenceScore(signal.confidence),
                    title=signal.title,
                    description=signal.description,
                    source=signal.source,
                    base_weight=BASE_SIGNAL_WEIGHTS[signal.signal_type],
                    evidence=signal.evidence,
                    tags=signal.tags,
                )
                for signal in command.signals
            ]
        )

        verification.add_signals(detected_signals)
        verification.complete(self.scoring_service)
        verification.risk_assessment = self._apply_analysis_warnings(
            verification.risk_assessment,
            analysis_warnings,
        )

        saved = self.repository.save(verification)
        return VerificationMapper.to_dto(saved)

    def _analyze_html_content(self, verification: Verification) -> SignalAnalysisResult:
        try:
            fetched_document = self.html_fetcher.fetch(verification.normalized_input.normalized)
        except HtmlFetchError as exc:
            return SignalAnalysisResult(
                warnings=(str(exc) or "HTML content inspection could not be completed.",)
            )

        if fetched_document is None:
            return SignalAnalysisResult()

        return SignalAnalysisResult(
            signals=tuple(
                self.html_credential_signal_analyzer.analyze(
                    verification.normalized_input,
                    fetched_document,
                )
            )
        )

    def _apply_analysis_warnings(
        self,
        risk_assessment: RiskAssessment | None,
        warnings: list[str],
    ) -> RiskAssessment | None:
        if risk_assessment is None or not warnings:
            return risk_assessment

        deduplicated_warnings = tuple(dict.fromkeys(warnings))
        summary = (
            "Analysis coverage degraded: "
            f"{' '.join(deduplicated_warnings)} "
            f"{risk_assessment.summary}"
        )

        adjusted_score = risk_assessment.score
        adjusted_risk_level = risk_assessment.risk_level
        adjusted_verdict = risk_assessment.verdict
        if not risk_assessment.terminal_override and risk_assessment.score.value > 80:
            adjusted_score = ConfidenceScore(80)
            adjusted_risk_level = risk_level_for_score(adjusted_score.value)
            adjusted_verdict = verdict_for_level(adjusted_risk_level)

        return RiskAssessment(
            score=adjusted_score,
            risk_level=adjusted_risk_level,
            verdict=adjusted_verdict,
            summary=summary,
            top_signals=risk_assessment.top_signals,
            category_breakdown=risk_assessment.category_breakdown,
            terminal_override=risk_assessment.terminal_override,
            terminal_reason=risk_assessment.terminal_reason,
            calculation_version=risk_assessment.calculation_version,
            calculated_at=risk_assessment.calculated_at,
        )
