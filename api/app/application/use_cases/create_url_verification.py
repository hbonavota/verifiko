from dataclasses import dataclass

from app.application.commands.create_verification_command import CreateVerificationCommand
from app.application.dto.verification_dto import VerificationDTO
from app.application.mappers.verification_mapper import VerificationMapper
from app.application.ports.html_fetcher import HtmlFetchError, HtmlFetcherPort
from app.application.services.domain_recency_signal_analyzer import DomainRecencySignalAnalyzer
from app.application.services.html_credential_signal_analyzer import HtmlCredentialSignalAnalyzer
from app.application.services.transport_security_signal_analyzer import (
    TransportSecuritySignalAnalyzer,
)
from app.application.services.url_signal_analyzer import DeterministicUrlSignalAnalyzer
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.verification import Verification
from app.domain.ports.id_generator import IdGeneratorPort
from app.domain.ports.verification_repository import VerificationRepository
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

        detected_signals = self.signal_analyzer.analyze(verification.normalized_input)
        detected_signals.extend(
            self.domain_recency_signal_analyzer.analyze(verification.normalized_input)
        )
        detected_signals.extend(
            self.transport_security_signal_analyzer.analyze(verification.normalized_input)
        )
        detected_signals.extend(self._analyze_html_content(verification))
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

        saved = self.repository.save(verification)
        return VerificationMapper.to_dto(saved)

    def _analyze_html_content(self, verification: Verification) -> list[AnalysisSignal]:
        try:
            fetched_document = self.html_fetcher.fetch(verification.normalized_input.normalized)
        except HtmlFetchError:
            return []

        if fetched_document is None:
            return []

        return self.html_credential_signal_analyzer.analyze(
            verification.normalized_input,
            fetched_document,
        )
