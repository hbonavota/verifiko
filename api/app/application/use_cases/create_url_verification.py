from dataclasses import dataclass
from dataclasses import replace
from typing import Callable

from app.application.commands.create_verification_command import CreateVerificationCommand
from app.application.dto.verification_dto import VerificationDTO
from app.application.mappers.verification_mapper import VerificationMapper
from app.application.ports.html_fetcher import HtmlFetchError, HtmlFetcherPort
from app.application.services.analysis_trace_builder import AnalysisTraceBuilder
from app.application.services.analysis_result import SignalAnalysisResult
from app.application.services.domain_recency_signal_analyzer import DomainRecencySignalAnalyzer
from app.application.services.html_credential_signal_analyzer import HtmlCredentialSignalAnalyzer
from app.application.services.infrastructure_signal_analyzer import (
    InfrastructureSignalAnalyzer,
)
from app.application.services.redirect_signal_analyzer import RedirectSignalAnalyzer
from app.application.services.reputation_signal_analyzer import ReputationSignalAnalyzer
from app.application.services.resolved_destination_signal_analyzer import (
    ResolvedDestinationSignalAnalyzer,
)
from app.application.services.transport_security_signal_analyzer import (
    TransportSecuritySignalAnalyzer,
)
from app.application.services.url_signal_analyzer import DeterministicUrlSignalAnalyzer
from app.application.services.message_resolver import normalize_warning_message, resolve_message
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.analysis_trace_stage import AnalysisTraceStage
from app.domain.entities.risk_assessment import RiskAssessment
from app.domain.entities.verification import Verification
from app.domain.exceptions.domain_exception import DomainException
from app.domain.ports.id_generator import IdGeneratorPort
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.services.risk_scoring_engine import risk_level_for_score, verdict_for_level
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS
from app.domain.services.scoring_service import ScoringService
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.infrastructure.external_services.outbound_target_guard import UnsafeOutboundTargetError


@dataclass(slots=True)
class CreateURLVerificationUseCase:
    repository: VerificationRepository
    id_generator: IdGeneratorPort
    scoring_service: ScoringService
    signal_analyzer: DeterministicUrlSignalAnalyzer
    domain_recency_signal_analyzer: DomainRecencySignalAnalyzer
    redirect_signal_analyzer: RedirectSignalAnalyzer
    reputation_signal_analyzer: ReputationSignalAnalyzer
    infrastructure_signal_analyzer: InfrastructureSignalAnalyzer
    resolved_destination_signal_analyzer: ResolvedDestinationSignalAnalyzer
    html_fetcher: HtmlFetcherPort
    html_credential_signal_analyzer: HtmlCredentialSignalAnalyzer
    transport_security_signal_analyzer: TransportSecuritySignalAnalyzer
    public_target_validator: Callable[[str], None] | None = None

    def execute(self, command: CreateVerificationCommand) -> VerificationDTO:
        verification = Verification.create_url(
            input_url=command.url,
            verification_id=self.id_generator.next_verification_id(),
            calculation_version=command.calculation_version,
        )
        self._assert_public_target(verification)
        verification.set_analyzing()

        analysis_warnings: list[str] = []
        analysis_trace: list[AnalysisTraceStage] = []
        detected_signals = self.signal_analyzer.analyze(verification.normalized_input)
        analysis_trace.append(
            self._build_trace_stage(
                stage="url_analysis",
                source=self.signal_analyzer.source,
                signals=tuple(detected_signals),
                warnings=(),
            )
        )
        domain_recency_result = self.domain_recency_signal_analyzer.analyze_with_context(
            verification.normalized_input
        )
        detected_signals.extend(domain_recency_result.signals)
        analysis_warnings.extend(domain_recency_result.warnings)
        analysis_trace.append(
            self._build_trace_stage(
                stage="domain_recency",
                source=self.domain_recency_signal_analyzer.source,
                signals=domain_recency_result.signals,
                warnings=domain_recency_result.warnings,
            )
        )

        redirect_result = self.redirect_signal_analyzer.analyze_with_context(
            verification.normalized_input
        )
        detected_signals.extend(redirect_result.signals)
        analysis_warnings.extend(redirect_result.warnings)
        analysis_trace.append(
            self._build_trace_stage(
                stage="redirect_resolution",
                source=self.redirect_signal_analyzer.source,
                signals=redirect_result.signals,
                warnings=redirect_result.warnings,
            )
        )

        reputation_result = self.reputation_signal_analyzer.analyze_with_context(
            verification.normalized_input,
            redirect_resolution=redirect_result.redirect_resolution,
        )
        detected_signals.extend(reputation_result.signals)
        analysis_warnings.extend(reputation_result.warnings)
        analysis_trace.append(
            self._build_trace_stage(
                stage="reputation",
                source=self.reputation_signal_analyzer.source,
                signals=reputation_result.signals,
                warnings=reputation_result.warnings,
            )
        )

        infrastructure_result = self.infrastructure_signal_analyzer.analyze_with_context(
            verification.normalized_input,
            redirect_resolution=redirect_result.redirect_resolution,
        )
        detected_signals.extend(infrastructure_result.signals)
        analysis_warnings.extend(infrastructure_result.warnings)
        analysis_trace.append(
            self._build_trace_stage(
                stage="infrastructure",
                source=self.infrastructure_signal_analyzer.source,
                signals=infrastructure_result.signals,
                warnings=infrastructure_result.warnings,
            )
        )

        resolved_destination_result = (
            self.resolved_destination_signal_analyzer.analyze_with_context(
                verification.normalized_input,
                redirect_resolution=redirect_result.redirect_resolution,
            )
        )
        detected_signals.extend(resolved_destination_result.signals)
        analysis_warnings.extend(resolved_destination_result.warnings)
        analysis_trace.append(
            self._build_trace_stage(
                stage="resolved_destination",
                source="resolved-destination-analysis",
                signals=resolved_destination_result.signals,
                warnings=resolved_destination_result.warnings,
            )
        )

        transport_result = self.transport_security_signal_analyzer.analyze_with_context(
            verification.normalized_input
        )
        detected_signals.extend(transport_result.signals)
        analysis_warnings.extend(transport_result.warnings)
        analysis_trace.append(
            self._build_trace_stage(
                stage="transport_security",
                source=self.transport_security_signal_analyzer.source,
                signals=transport_result.signals,
                warnings=transport_result.warnings,
            )
        )

        html_result = self._analyze_html_content(verification)
        detected_signals.extend(html_result.signals)
        analysis_warnings.extend(html_result.warnings)
        analysis_trace.append(
            self._build_trace_stage(
                stage="html_content",
                source=self.html_credential_signal_analyzer.source,
                signals=html_result.signals,
                warnings=html_result.warnings,
            )
        )
        trusted_signals = [
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
        detected_signals.extend(trusted_signals)
        if trusted_signals:
            analysis_trace.append(
                self._build_trace_stage(
                    stage="trusted_signal_inputs",
                    source="trusted-signal-input",
                    signals=tuple(trusted_signals),
                    warnings=(),
                )
            )

        verification.add_signals(detected_signals)
        verification.complete(self.scoring_service)
        verification.risk_assessment = self._apply_analysis_warnings(
            verification.risk_assessment,
            analysis_warnings,
            analysis_trace,
        )

        trace = AnalysisTraceBuilder.build(
            verification.signals,
            layers_executed=self._layers_executed(command),
        )

        saved = self.repository.save(verification)
        return VerificationMapper.to_dto(saved, trace=trace)

    def _analyze_html_content(self, verification: Verification) -> SignalAnalysisResult:
        try:
            fetched_document = self.html_fetcher.fetch(verification.normalized_input.normalized)
        except HtmlFetchError as exc:
            return SignalAnalysisResult(
                warnings=(
                    normalize_warning_message(
                        str(exc),
                        default_key="warning.html_content_inspection_unavailable",
                    ),
                )
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
        analysis_trace: list[AnalysisTraceStage],
    ) -> RiskAssessment | None:
        if risk_assessment is None:
            return None

        deduplicated_warnings = tuple(dict.fromkeys(warnings))
        summary = risk_assessment.summary
        if deduplicated_warnings:
            summary = resolve_message(
                "summary.analysis_coverage_degraded",
                {
                    "warnings": " ".join(deduplicated_warnings),
                    "summary": risk_assessment.summary,
                },
            )

        adjusted_score = risk_assessment.score
        adjusted_risk_level = risk_assessment.risk_level
        adjusted_verdict = risk_assessment.verdict
        if (
            deduplicated_warnings
            and not risk_assessment.terminal_override
            and risk_assessment.score.value > 80
            and any(value > 0 for value in risk_assessment.category_breakdown.values())
        ):
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
            analysis_warnings=deduplicated_warnings,
            analysis_trace=tuple(analysis_trace),
            score_breakdown=(
                replace(
                    risk_assessment.score_breakdown,
                    final_score=adjusted_score.rounded(),
                )
                if risk_assessment.score_breakdown is not None
                else None
            ),
            calculated_at=risk_assessment.calculated_at,
        )

    def _build_trace_stage(
        self,
        stage: str,
        source: str,
        signals: tuple[AnalysisSignal, ...],
        warnings: tuple[str, ...],
    ) -> AnalysisTraceStage:
        if warnings:
            status = "degraded"
        elif signals:
            status = "signals_detected"
        else:
            status = "clean"

        return AnalysisTraceStage(
            stage=stage,
            source=source,
            status=status,
            signal_count=len(signals),
            signal_titles=tuple(signal.title for signal in signals[:3]),
            warnings=warnings,
        )

    def _layers_executed(self, command: CreateVerificationCommand) -> tuple[str, ...]:
        layers = [
            self.signal_analyzer.source,
            self.domain_recency_signal_analyzer.source,
            self.redirect_signal_analyzer.source,
            self.reputation_signal_analyzer.source,
            self.infrastructure_signal_analyzer.source,
            self.resolved_destination_signal_analyzer.url_source,
            self.resolved_destination_signal_analyzer.html_source,
            self.transport_security_signal_analyzer.source,
            self.html_credential_signal_analyzer.source,
        ]
        if command.signals:
            layers.extend(signal.source for signal in command.signals)
        return tuple(dict.fromkeys(layers))

    def _assert_public_target(self, verification: Verification) -> None:
        if self.public_target_validator is None:
            return
        try:
            self.public_target_validator(verification.normalized_input.normalized)
        except UnsafeOutboundTargetError as exc:
            raise DomainException(str(exc)) from exc
