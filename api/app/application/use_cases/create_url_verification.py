import hashlib
import html
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from dataclasses import replace
from itertools import combinations
from typing import Callable, TypeVar

from app.application.commands.create_verification_command import CreateVerificationCommand
from app.application.dto.verification_dto import VerificationDTO
from app.application.mappers.verification_mapper import VerificationMapper
from app.application.ports.html_fetcher import FetchedHtmlDocument, HtmlFetchError, HtmlFetcherPort
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
from app.application.services.message_resolver import (
    build_localized_signal,
    evidence_ref,
    resolve_message,
)
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.analysis_trace_stage import AnalysisTraceStage
from app.domain.entities.risk_assessment import RiskAssessment
from app.domain.entities.verification import Verification
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.exceptions.domain_exception import DomainException
from app.domain.ports.id_generator import IdGeneratorPort
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.services.risk_scoring_engine import risk_level_for_score, verdict_for_level
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS, SIGNAL_CATEGORY_MAP
from app.domain.services.scoring_service import ScoringService
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.infrastructure.external_services.outbound_target_guard import UnsafeOutboundTargetError

_StageResultT = TypeVar("_StageResultT")

_HTML_COVERAGE_WARNING_KEYS = (
    "warning.html_content_inspection_unavailable",
    "warning.resolved_destination_html_unavailable",
)
_NON_DEGRADING_ANALYSIS_WARNING_KEYS = (
    "warning.multi_user_agent_fetch_partially_unavailable",
)
_REDIRECT_COVERAGE_WARNING_KEYS = ("warning.redirect_resolution_unavailable",)
_CONTEXTUAL_COVERAGE_WARNING_KEYS = (
    "warning.domain_registration_unavailable",
    "warning.infrastructure_unavailable",
)
_REDIRECT_DEGRADED_SOURCE_SIGNAL_TYPES = {
    SignalType.PHISHING_KEYWORDS,
    SignalType.BRAND_IMPERSONATION,
    SignalType.TACTICAL_EMAIL_STAGING,
    SignalType.DECEPTIVE_BRAND_SUBDOMAIN,
}
_ANTI_CAMOUFLAGE_WARNING_KEY = "warning.multi_user_agent_fetch_partially_unavailable"
_ANTI_CAMOUFLAGE_MESSAGE_KEY = "signal.content_variation_detected"
_ANTI_CAMOUFLAGE_TAGS = ("anti-camouflage", "user-agent-variation", "html-content")
_LOGIN_SURFACE_SIGNAL_TYPES = {
    SignalType.CREDENTIAL_HARVEST_FORM,
    SignalType.SUSPICIOUS_LOGIN_INTERFACE,
}
_LOW_INFORMATION_SIGNAL_TYPES = {SignalType.LOW_INFORMATION_PAGE}
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_SCRIPT_STYLE_RE = re.compile(r"<(?:script|style|noscript)\b[^>]*>.*?</(?:script|style|noscript)>", re.IGNORECASE | re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9:/._-]*")
_UUID_TOKEN_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_HEX_TOKEN_RE = re.compile(r"^[0-9a-f]{16,}$", re.IGNORECASE)
_ISO_DATE_TOKEN_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:t\d{2}:\d{2}(?::\d{2})?(?:z|[+-]\d{2}:?\d{2})?)?$", re.IGNORECASE)
_EPOCH_TOKEN_RE = re.compile(r"^\d{10,13}$")


@dataclass(frozen=True, slots=True)
class _HtmlVariantProfile:
    name: str
    user_agent: str


@dataclass(frozen=True, slots=True)
class _HtmlVariantObservation:
    profile: _HtmlVariantProfile
    document: FetchedHtmlDocument
    signals: tuple[AnalysisSignal, ...]
    canonical_text: str
    token_set: frozenset[str]
    token_count: int
    content_hash: str


@dataclass(frozen=True, slots=True)
class _ContentVariationCandidate:
    severity: SignalSeverity
    confidence: int
    message_params: dict[str, object]


_HTML_FETCH_VARIANT_PROFILES = (
    _HtmlVariantProfile(
        name="desktop",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        ),
    ),
    _HtmlVariantProfile(
        name="mobile",
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 "
            "Mobile/15E148 Safari/604.1"
        ),
    ),
    _HtmlVariantProfile(
        name="googlebot-like",
        user_agent=(
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        ),
    ),
)


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
    parallel_analysis_enabled: bool = True

    def execute(self, command: CreateVerificationCommand) -> VerificationDTO:
        verification = Verification.create_url(
            input_url=command.url,
            verification_id=self.id_generator.next_verification_id(),
            user_id=command.user_id,
            calculation_version=command.calculation_version,
        )
        self._assert_public_target(verification)
        verification.set_analyzing()

        analysis_warnings: list[str] = []
        analysis_trace: list[AnalysisTraceStage] = []
        normalized_input = verification.normalized_input
        detected_signals = self.signal_analyzer.analyze(normalized_input)
        analysis_trace.append(
            self._build_trace_stage(
                stage="url_analysis",
                source=self.signal_analyzer.source,
                signals=tuple(detected_signals),
                warnings=(),
            )
        )

        # Wave 1: analyzers that depend only on the input URL run concurrently.
        # Each analyzer performs blocking network I/O, so overlapping them turns
        # the total wait from a sum of latencies into a maximum.
        wave_one = self._run_stage_group(
            {
                "domain_recency": lambda: self.domain_recency_signal_analyzer.analyze_with_context(
                    normalized_input
                ),
                "redirect": lambda: self.redirect_signal_analyzer.analyze_with_context(
                    normalized_input
                ),
                "transport": lambda: self.transport_security_signal_analyzer.analyze_with_context(
                    normalized_input
                ),
                "html": lambda: self._analyze_html_content(verification),
            }
        )
        domain_recency_result = wave_one["domain_recency"]
        redirect_result = wave_one["redirect"]
        transport_result = wave_one["transport"]
        html_result = wave_one["html"]

        redirect_resolution = redirect_result.redirect_resolution

        # Wave 2: analyzers that additionally need the resolved redirect
        # destination. They only depend on wave 1's redirect result, so they run
        # concurrently with each other.
        wave_two = self._run_stage_group(
            {
                "reputation": lambda: self.reputation_signal_analyzer.analyze_with_context(
                    normalized_input, redirect_resolution=redirect_resolution
                ),
                "infrastructure": lambda: self.infrastructure_signal_analyzer.analyze_with_context(
                    normalized_input, redirect_resolution=redirect_resolution
                ),
                "resolved_destination": lambda: self.resolved_destination_signal_analyzer.analyze_with_context(
                    normalized_input, redirect_resolution=redirect_resolution
                ),
            }
        )
        reputation_result = wave_two["reputation"]
        infrastructure_result = wave_two["infrastructure"]
        resolved_destination_result = wave_two["resolved_destination"]

        # Assemble signals, warnings and trace stages in the original,
        # deterministic order so the scored result is byte-for-byte identical to
        # the sequential pipeline regardless of completion timing.
        for stage, source, result in (
            (
                "domain_recency",
                self.domain_recency_signal_analyzer.source,
                domain_recency_result,
            ),
            (
                "redirect_resolution",
                self.redirect_signal_analyzer.source,
                redirect_result,
            ),
            ("reputation", self.reputation_signal_analyzer.source, reputation_result),
            (
                "infrastructure",
                self.infrastructure_signal_analyzer.source,
                infrastructure_result,
            ),
            (
                "resolved_destination",
                "resolved-destination-analysis",
                resolved_destination_result,
            ),
            (
                "transport_security",
                self.transport_security_signal_analyzer.source,
                transport_result,
            ),
        ):
            detected_signals.extend(result.signals)
            analysis_warnings.extend(result.warnings)
            analysis_trace.append(
                self._build_trace_stage(
                    stage=stage,
                    source=source,
                    signals=result.signals,
                    warnings=result.warnings,
                )
            )

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
            verification.signals,
            analysis_warnings,
            analysis_trace,
        )

        trace = AnalysisTraceBuilder.build(
            verification.signals,
            layers_executed=self._layers_executed(command),
        )

        verification.redact_sensitive_input()
        saved = self.repository.save(verification)
        return VerificationMapper.to_dto(saved, trace=trace)

    def _run_stage_group(
        self,
        tasks: dict[str, Callable[[], "_StageResultT"]],
    ) -> dict[str, "_StageResultT"]:
        """Run independent analysis stages, concurrently when enabled.

        Falls back to sequential execution when parallelism is disabled or a
        single task is scheduled, so behaviour is identical either way — only
        timing differs. Task exceptions propagate unchanged.
        """
        if not self.parallel_analysis_enabled or len(tasks) <= 1:
            return {name: task() for name, task in tasks.items()}

        results: dict[str, _StageResultT] = {}
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {executor.submit(task): name for name, task in tasks.items()}
            for future in as_completed(futures):
                results[futures[future]] = future.result()
        return results

    def _analyze_html_content(self, verification: Verification) -> SignalAnalysisResult:
        observations: list[_HtmlVariantObservation] = []
        fetch_failures = 0

        for profile in _HTML_FETCH_VARIANT_PROFILES:
            try:
                fetched_document = self.html_fetcher.fetch(
                    verification.normalized_input.normalized,
                    user_agent=profile.user_agent,
                )
            except HtmlFetchError:
                fetch_failures += 1
                continue

            if fetched_document is None:
                continue

            signals = tuple(
                self.html_credential_signal_analyzer.analyze(
                    verification.normalized_input,
                    fetched_document,
                )
            )
            canonical_text = _canonicalize_html(fetched_document.content)
            observations.append(
                _HtmlVariantObservation(
                    profile=profile,
                    document=fetched_document,
                    signals=signals,
                    canonical_text=canonical_text,
                    token_set=frozenset(_canonical_tokens(canonical_text)),
                    token_count=len(canonical_text.split()),
                    content_hash=hashlib.sha256(canonical_text.encode("utf-8")).hexdigest(),
                )
            )

        if not observations:
            if fetch_failures > 0:
                return SignalAnalysisResult(
                    warnings=(
                        resolve_message("warning.html_content_inspection_unavailable"),
                    )
                )
            return SignalAnalysisResult()

        warnings: tuple[str, ...] = ()
        if fetch_failures > 0:
            warnings = (resolve_message(_ANTI_CAMOUFLAGE_WARNING_KEY),)

        signals = list(_deduplicate_analysis_signals(observations))
        variation_signal = _build_content_variation_signal(
            observations,
            source=self.html_credential_signal_analyzer.source,
        )
        if variation_signal is not None:
            signals.append(variation_signal)

        return SignalAnalysisResult(
            signals=tuple(signals),
            warnings=warnings,
        )

    def _apply_analysis_warnings(
        self,
        risk_assessment: RiskAssessment | None,
        signals: tuple[AnalysisSignal, ...],
        warnings: list[str],
        analysis_trace: list[AnalysisTraceStage],
    ) -> RiskAssessment | None:
        if risk_assessment is None:
            return None

        deduplicated_warnings = tuple(dict.fromkeys(warnings))
        degrading_warnings = _degrading_analysis_warnings(deduplicated_warnings)
        summary = risk_assessment.summary
        if degrading_warnings:
            summary = resolve_message(
                "summary.analysis_coverage_degraded",
                {
                    "warnings": " ".join(degrading_warnings),
                    "summary": risk_assessment.summary,
                },
            )

        adjusted_score = risk_assessment.score
        adjusted_risk_level = risk_assessment.risk_level
        adjusted_verdict = risk_assessment.verdict
        html_coverage_degraded = _has_html_coverage_warning(degrading_warnings)
        redirect_coverage_degraded = _has_redirect_coverage_warning(degrading_warnings)
        contextual_coverage_degraded = _has_contextual_coverage_warning(degrading_warnings)
        source_url_suspicion = _has_meaningful_source_url_suspicion(
            signals,
            source=self.signal_analyzer.source,
        )
        if (
            degrading_warnings
            and not risk_assessment.terminal_override
            and risk_assessment.score.value > 80
            and any(value > 0 for value in risk_assessment.category_breakdown.values())
        ):
            adjusted_score = ConfidenceScore(80)
            adjusted_risk_level = risk_level_for_score(adjusted_score.value)
            adjusted_verdict = verdict_for_level(adjusted_risk_level)
        if (
            html_coverage_degraded
            and not risk_assessment.terminal_override
            and risk_assessment.score.value < 80
            and adjusted_score.value > 60
            and any(value > 0 for value in risk_assessment.category_breakdown.values())
        ):
            adjusted_score = ConfidenceScore(60)
            adjusted_risk_level = risk_level_for_score(adjusted_score.value)
            adjusted_verdict = verdict_for_level(adjusted_risk_level)
        if (
            redirect_coverage_degraded
            and source_url_suspicion
            and not risk_assessment.terminal_override
            and adjusted_score.value > 60
        ):
            adjusted_score = ConfidenceScore(60)
            adjusted_risk_level = risk_level_for_score(adjusted_score.value)
            adjusted_verdict = verdict_for_level(adjusted_risk_level)
        if (
            contextual_coverage_degraded
            and source_url_suspicion
            and not risk_assessment.terminal_override
            and adjusted_score.value > 60
        ):
            adjusted_score = ConfidenceScore(60)
            adjusted_risk_level = risk_level_for_score(adjusted_score.value)
            adjusted_verdict = verdict_for_level(adjusted_risk_level)
        if adjusted_risk_level is not risk_assessment.risk_level:
            summary = _refresh_risk_detected_summary(
                summary=summary,
                original_assessment=risk_assessment,
                adjusted_risk_level=adjusted_risk_level,
            )

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


def _has_html_coverage_warning(warnings: tuple[str, ...]) -> bool:
    html_warnings = {resolve_message(key) for key in _HTML_COVERAGE_WARNING_KEYS}
    return any(warning in html_warnings for warning in warnings)


def _degrading_analysis_warnings(warnings: tuple[str, ...]) -> tuple[str, ...]:
    non_degrading = {resolve_message(key) for key in _NON_DEGRADING_ANALYSIS_WARNING_KEYS}
    return tuple(warning for warning in warnings if warning not in non_degrading)


def _has_redirect_coverage_warning(warnings: tuple[str, ...]) -> bool:
    redirect_warnings = {resolve_message(key) for key in _REDIRECT_COVERAGE_WARNING_KEYS}
    return any(warning in redirect_warnings for warning in warnings)


def _has_contextual_coverage_warning(warnings: tuple[str, ...]) -> bool:
    contextual_warnings = {resolve_message(key) for key in _CONTEXTUAL_COVERAGE_WARNING_KEYS}
    return any(warning in contextual_warnings for warning in warnings)


def _has_meaningful_source_url_suspicion(
    signals: tuple[AnalysisSignal, ...],
    source: str,
) -> bool:
    return any(
        signal.source == source and signal.signal_type in _REDIRECT_DEGRADED_SOURCE_SIGNAL_TYPES
        for signal in signals
    )


def _refresh_risk_detected_summary(
    summary: str,
    original_assessment: RiskAssessment,
    adjusted_risk_level,
) -> str:
    score_breakdown = original_assessment.score_breakdown
    if score_breakdown is None:
        return summary

    risk_signal_count = sum(
        1 for contribution in score_breakdown.signal_contributions if contribution.impact > 0
    )
    category_total_penalty = sum(original_assessment.category_breakdown.values())
    compound_penalty = sum(
        rule.delta for rule in score_breakdown.compound_rules_applied
    )
    original_base_summary = resolve_message(
        "summary.risk_detected",
        {
            "risk_signal_count": risk_signal_count,
            "risk_level": original_assessment.risk_level.value.lower(),
            "category_total_penalty": category_total_penalty,
            "compound_penalty": compound_penalty,
        },
    )
    adjusted_base_summary = resolve_message(
        "summary.risk_detected",
        {
            "risk_signal_count": risk_signal_count,
            "risk_level": adjusted_risk_level.value.lower(),
            "category_total_penalty": category_total_penalty,
            "compound_penalty": compound_penalty,
        },
    )
    return summary.replace(original_base_summary, adjusted_base_summary, 1)


def _deduplicate_analysis_signals(
    observations: list[_HtmlVariantObservation],
) -> tuple[AnalysisSignal, ...]:
    deduplicated: list[AnalysisSignal] = []
    seen: set[tuple[object, ...]] = set()

    for observation in observations:
        for signal in observation.signals:
            key = (
                signal.signal_type,
                signal.category,
                signal.severity,
                signal.confidence.value,
                signal.title,
                signal.description,
                signal.source,
                signal.base_weight,
                signal.evidence,
                signal.detected,
                signal.tags,
                signal.message_key,
                _freeze_message_params(signal.message_params),
            )
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(signal)

    return tuple(deduplicated)


def _freeze_message_params(value):
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze_message_params(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_message_params(item) for item in value)
    return value


def _build_content_variation_signal(
    observations: list[_HtmlVariantObservation],
    *,
    source: str,
) -> AnalysisSignal | None:
    if len(observations) < 2:
        return None

    best_candidate: _ContentVariationCandidate | None = None
    for left, right in combinations(observations, 2):
        candidate = _evaluate_content_variation_pair(left, right)
        if candidate is None:
            continue
        if (
            best_candidate is None
            or _variation_candidate_sort_key(candidate) > _variation_candidate_sort_key(best_candidate)
        ):
            best_candidate = candidate

    if best_candidate is None:
        return None

    return build_localized_signal(
        signal_type=SignalType.CONTENT_VARIATION_DETECTED,
        category=SIGNAL_CATEGORY_MAP[SignalType.CONTENT_VARIATION_DETECTED],
        severity=best_candidate.severity,
        confidence=ConfidenceScore(best_candidate.confidence),
        source=source,
        base_weight=BASE_SIGNAL_WEIGHTS[SignalType.CONTENT_VARIATION_DETECTED],
        message_key=_ANTI_CAMOUFLAGE_MESSAGE_KEY,
        message_params=best_candidate.message_params,
        tags=_ANTI_CAMOUFLAGE_TAGS,
    )


def _evaluate_content_variation_pair(
    left: _HtmlVariantObservation,
    right: _HtmlVariantObservation,
) -> _ContentVariationCandidate | None:
    if left.content_hash == right.content_hash:
        return None

    similarity = _token_similarity(left.token_set, right.token_set)
    left_has_login = _has_signal_type(left.signals, _LOGIN_SURFACE_SIGNAL_TYPES)
    right_has_login = _has_signal_type(right.signals, _LOGIN_SURFACE_SIGNAL_TYPES)
    left_is_low_information = _is_low_information_variant(left)
    right_is_low_information = _is_low_information_variant(right)

    base_evidence = [
        evidence_ref(
            "evidence.user_agent_profiles_compared",
            left_profile=left.profile.name,
            right_profile=right.profile.name,
        ),
        evidence_ref(
            "evidence.user_agent_variant_token_counts",
            left_profile=left.profile.name,
            left_tokens=left.token_count,
            right_profile=right.profile.name,
            right_tokens=right.token_count,
        ),
        evidence_ref(
            "evidence.user_agent_variant_similarity",
            left_profile=left.profile.name,
            right_profile=right.profile.name,
            similarity=f"{similarity:.2f}",
        ),
    ]

    if left_has_login != right_has_login:
        login_profiles = ", ".join(
            observation.profile.name
            for observation in (left, right)
            if _has_signal_type(observation.signals, _LOGIN_SURFACE_SIGNAL_TYPES)
        )
        return _ContentVariationCandidate(
            severity=SignalSeverity.HIGH,
            confidence=92,
            message_params={
                "evidence": [
                    *base_evidence,
                    evidence_ref(
                        "evidence.login_cues_observed_for_profiles",
                        profiles=login_profiles,
                    ),
                ],
            },
        )

    if (
        left_is_low_information != right_is_low_information
        and max(left.token_count, right.token_count) >= 25
        and similarity <= 0.60
    ):
        low_information_profiles = ", ".join(
            observation.profile.name
            for observation in (left, right)
            if _is_low_information_variant(observation)
        )
        return _ContentVariationCandidate(
            severity=SignalSeverity.HIGH,
            confidence=88,
            message_params={
                "evidence": [
                    *base_evidence,
                    evidence_ref(
                        "evidence.low_information_profiles_observed",
                        profiles=low_information_profiles,
                    ),
                ],
            },
        )

    shorter_length = max(1, min(left.token_count, right.token_count))
    length_ratio = max(left.token_count, right.token_count) / shorter_length
    if max(left.token_count, right.token_count) >= 25 and length_ratio >= 2.5 and similarity <= 0.35:
        return _ContentVariationCandidate(
            severity=SignalSeverity.MEDIUM,
            confidence=79,
            message_params={"evidence": base_evidence},
        )

    return None


def _variation_candidate_sort_key(candidate: _ContentVariationCandidate) -> tuple[int, int]:
    severity_rank = {
        SignalSeverity.MEDIUM: 1,
        SignalSeverity.HIGH: 2,
        SignalSeverity.CRITICAL: 3,
    }
    return (severity_rank.get(candidate.severity, 0), candidate.confidence)


def _is_low_information_variant(observation: _HtmlVariantObservation) -> bool:
    return _has_signal_type(observation.signals, _LOW_INFORMATION_SIGNAL_TYPES) or (
        observation.token_count <= 6
    )


def _has_signal_type(
    signals: tuple[AnalysisSignal, ...],
    signal_types: set[SignalType],
) -> bool:
    return any(signal.signal_type in signal_types for signal in signals)


def _token_similarity(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 1.0
    return len(left & right) / len(union)


def _canonicalize_html(value: str) -> str:
    scrubbed = html.unescape(value).lower()
    scrubbed = _HTML_COMMENT_RE.sub(" ", scrubbed)
    scrubbed = _HTML_SCRIPT_STYLE_RE.sub(" ", scrubbed)
    scrubbed = _HTML_TAG_RE.sub(" ", scrubbed)
    return " ".join(_canonical_tokens(scrubbed))


def _canonical_tokens(value: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for raw_token in _HTML_TOKEN_RE.findall(value):
        normalized = _normalize_canonical_token(raw_token.strip("._-:/"))
        if normalized:
            tokens.append(normalized)
    return tuple(tokens)


def _normalize_canonical_token(token: str) -> str | None:
    if not token:
        return None
    if _UUID_TOKEN_RE.match(token) or _HEX_TOKEN_RE.match(token):
        return "<token>"
    if _ISO_DATE_TOKEN_RE.match(token) or _EPOCH_TOKEN_RE.match(token):
        return "<timestamp>"
    if len(token) >= 24 and any(character.isdigit() for character in token):
        return "<token>"
    if len(token) == 1 and not token.isdigit():
        return None
    return token
