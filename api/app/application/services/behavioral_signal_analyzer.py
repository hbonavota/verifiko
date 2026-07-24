from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.headless_detonation import DetonationResult
from app.application.services.message_resolver import build_localized_signal, evidence_ref
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS, SIGNAL_CATEGORY_MAP
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.normalized_url import NormalizedUrl


@dataclass(slots=True)
class BehavioralSignalAnalyzer:
    """Turns what a headless browser observed (a ``DetonationResult``) into
    behavioral risk signals. Pure application logic — it never talks to a
    browser, so it is fully testable with fabricated detonation results."""

    source: str = "behavioral-detonation-analyzer"

    def analyze(self, result: DetonationResult) -> list[AnalysisSignal]:
        signals: list[AnalysisSignal] = []

        page_domain = _registered_domain(result.final_url) or _registered_domain(
            result.requested_url
        )
        password_forms = [form for form in result.forms if form.has_password_field]

        if password_forms:
            signals.append(
                self._signal(
                    signal_type=SignalType.RENDERED_CREDENTIAL_FORM,
                    severity=SignalSeverity.HIGH,
                    confidence=88,
                    message_key="signal.rendered_credential_form",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.detonation_final_url", final_url=result.final_url
                            )
                        ]
                    },
                    tags=("behavioral", "credential-form", "rendered-dom"),
                )
            )

            offsite_hosts = sorted(
                {
                    form.action_host
                    for form in password_forms
                    if form.action_host
                    and _registered_domain_of_host(form.action_host) not in (None, page_domain)
                }
            )
            if offsite_hosts:
                signals.append(
                    self._signal(
                        signal_type=SignalType.OFFSITE_FORM_ACTION,
                        severity=SignalSeverity.CRITICAL,
                        confidence=95,
                        message_key="signal.offsite_credential_form_action",
                        message_params={
                            "evidence": [
                                evidence_ref(
                                    "evidence.detonation_offsite_form_hosts",
                                    hosts=", ".join(offsite_hosts[:3]),
                                )
                            ]
                        },
                        tags=("behavioral", "credential-exfiltration"),
                    )
                )

        requested_domain = _registered_domain(result.requested_url)
        final_domain = _registered_domain(result.final_url)
        if requested_domain and final_domain and requested_domain != final_domain:
            signals.append(
                self._signal(
                    signal_type=SignalType.JS_REDIRECT_TO_OFFSITE,
                    severity=SignalSeverity.MEDIUM,
                    confidence=80,
                    message_key="signal.js_redirect_to_offsite",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.detonation_redirect_domain", domain=final_domain
                            )
                        ]
                    },
                    tags=("behavioral", "js-redirect", final_domain),
                )
            )

        if result.downloads:
            signals.append(
                self._signal(
                    signal_type=SignalType.DRIVE_BY_DOWNLOAD,
                    severity=SignalSeverity.HIGH,
                    confidence=90,
                    message_key="signal.drive_by_download",
                    message_params={
                        "evidence": [
                            evidence_ref(
                                "evidence.detonation_downloads",
                                downloads=", ".join(result.downloads[:3]),
                            )
                        ]
                    },
                    tags=("behavioral", "drive-by-download"),
                )
            )

        return signals

    def _signal(
        self,
        *,
        signal_type: SignalType,
        severity: SignalSeverity,
        confidence: float,
        message_key: str,
        message_params: dict[str, object],
        tags: tuple[str, ...] = (),
    ) -> AnalysisSignal:
        return build_localized_signal(
            signal_type=signal_type,
            category=SIGNAL_CATEGORY_MAP[signal_type],
            severity=severity,
            confidence=ConfidenceScore(confidence),
            source=self.source,
            base_weight=BASE_SIGNAL_WEIGHTS[signal_type],
            message_key=message_key,
            message_params=message_params,
            tags=tags,
        )


def _registered_domain(url: str) -> str | None:
    try:
        registered = NormalizedUrl.from_raw(url).registered_domain
    except Exception:  # noqa: BLE001 - a malformed URL simply yields no domain
        return None
    return registered or None


def _registered_domain_of_host(host: str) -> str | None:
    return _registered_domain(f"https://{host}/")
