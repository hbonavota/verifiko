from dataclasses import dataclass

from app.application.ports.html_fetcher import HtmlFetchError, HtmlFetcherPort
from app.application.ports.redirect_resolver import RedirectResolution
from app.application.services.analysis_result import SignalAnalysisResult
from app.application.services.html_credential_signal_analyzer import HtmlCredentialSignalAnalyzer
from app.application.services.url_signal_analyzer import DeterministicUrlSignalAnalyzer
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.value_objects.normalized_url import NormalizedUrl


@dataclass(slots=True)
class ResolvedDestinationSignalAnalyzer:
    url_signal_analyzer: DeterministicUrlSignalAnalyzer
    html_fetcher: HtmlFetcherPort
    html_credential_signal_analyzer: HtmlCredentialSignalAnalyzer
    url_source: str = "resolved-destination-url-analyzer"
    html_source: str = "resolved-destination-html-analyzer"

    def analyze_with_context(
        self,
        original_url: NormalizedUrl,
        redirect_resolution: RedirectResolution | None,
    ) -> SignalAnalysisResult:
        if redirect_resolution is None or not redirect_resolution.hops:
            return SignalAnalysisResult()

        final_url = NormalizedUrl.from_raw(redirect_resolution.final_url)
        if not self._should_analyze_destination(original_url, final_url):
            return SignalAnalysisResult()

        warnings: list[str] = []
        signals = list(self._clone_url_signals(final_url))
        try:
            fetched_document = self.html_fetcher.fetch(final_url.normalized)
        except HtmlFetchError as exc:
            warnings.append(str(exc) or "Resolved destination HTML inspection could not be completed.")
        else:
            if fetched_document is not None:
                signals.extend(self._clone_html_signals(final_url, fetched_document))

        return SignalAnalysisResult(
            signals=tuple(signals),
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def _should_analyze_destination(
        self,
        original_url: NormalizedUrl,
        final_url: NormalizedUrl,
    ) -> bool:
        return final_url.registered_domain != original_url.registered_domain

    def _clone_url_signals(self, final_url: NormalizedUrl) -> tuple[AnalysisSignal, ...]:
        return tuple(
            self._copy_signal(
                signal,
                source=self.url_source,
                evidence_prefix=f"Resolved final URL: {final_url.normalized}.",
                tag_prefix="resolved-destination",
            )
            for signal in self.url_signal_analyzer.analyze(final_url)
        )

    def _clone_html_signals(
        self,
        final_url: NormalizedUrl,
        fetched_document,
    ) -> tuple[AnalysisSignal, ...]:
        return tuple(
            self._copy_signal(
                signal,
                source=self.html_source,
                evidence_prefix=f"Resolved final URL: {final_url.normalized}.",
                tag_prefix="resolved-destination",
            )
            for signal in self.html_credential_signal_analyzer.analyze(final_url, fetched_document)
        )

    def _copy_signal(
        self,
        signal: AnalysisSignal,
        source: str,
        evidence_prefix: str,
        tag_prefix: str,
    ) -> AnalysisSignal:
        evidence = (evidence_prefix, *signal.evidence)
        tags = (tag_prefix, *signal.tags)
        return AnalysisSignal.create(
            signal_type=signal.signal_type,
            category=signal.category,
            severity=signal.severity,
            confidence=signal.confidence,
            title=signal.title,
            description=signal.description,
            source=source,
            base_weight=signal.base_weight,
            evidence=evidence,
            tags=tags,
        )
