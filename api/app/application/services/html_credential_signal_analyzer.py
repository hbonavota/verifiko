from collections.abc import Iterable
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from app.application.ports.html_fetcher import FetchedHtmlDocument
from app.application.services.message_resolver import (
    build_localized_signal,
    evidence_ref,
)
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import (
    BASE_SIGNAL_WEIGHTS,
    SIGNAL_CATEGORY_MAP,
)
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.normalized_url import NormalizedUrl

_LOGIN_TERMS = {
    "account",
    "approve",
    "challenge",
    "confirm",
    "login",
    "log in",
    "password",
    "reauth",
    "security",
    "session",
    "sign in",
    "signin",
    "verify",
    "verification",
}
_ACCOUNT_FIELD_HINTS = {"email", "identifier", "login", "mail", "user", "username"}
_AUTH_FIELD_HINTS = {"mfa", "otp", "passcode", "totp"}
_LOW_INFORMATION_MARKERS = {
    "apache2 ubuntu default page",
    "buy this domain",
    "coming soon",
    "domain for sale",
    "future home of something quite cool",
    "parked free courtesy of",
    "sedo",
    "this domain is for sale",
    "under construction",
    "welcome to nginx",
}


@dataclass(frozen=True, slots=True)
class ParsedForm:
    action: str | None
    password_field_count: int
    account_hints: tuple[str, ...]
    auth_hints: tuple[str, ...]
    button_labels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ParsedHtmlPage:
    forms: tuple[ParsedForm, ...]
    visible_text: tuple[str, ...]


@dataclass(slots=True)
class HtmlCredentialSignalAnalyzer:
    source: str = "html-credential-analyzer"

    def analyze(
        self,
        normalized_url: NormalizedUrl,
        fetched_document: FetchedHtmlDocument,
    ) -> list[AnalysisSignal]:
        parsed_page = _LoginHtmlParser.parse(fetched_document.content)
        form_count = len(parsed_page.forms)
        password_field_count = sum(
            form.password_field_count for form in parsed_page.forms
        )
        account_hints = sorted(
            {hint for form in parsed_page.forms for hint in form.account_hints}
        )
        auth_hints = sorted(
            {hint for form in parsed_page.forms for hint in form.auth_hints}
        )
        matched_login_terms = _match_login_terms(parsed_page.visible_text)
        visible_token_count = _visible_token_count(parsed_page.visible_text)
        low_information_markers = _match_low_information_markers(
            parsed_page.visible_text
        )
        suspicious_host_context = _has_suspicious_host_context(normalized_url)
        suspicious_actions = [
            action
            for form in parsed_page.forms
            if form.action
            for action in [_normalize_action(form.action, fetched_document.source_url)]
            if _is_suspicious_action(action, normalized_url.registered_domain)
        ]
        observed_actions = [
            action
            for form in parsed_page.forms
            if form.action
            for action in [_normalize_action(form.action, fetched_document.source_url)]
        ]

        signals: list[AnalysisSignal] = []
        official_same_site_auth_surface = _is_official_same_site_auth_surface(
            normalized_url,
            suspicious_actions,
        )
        auth_challenge_surface = bool(auth_hints) and len(matched_login_terms) >= 3
        strong_credential_cues = (
            bool(account_hints)
            or bool(auth_hints)
            or len(matched_login_terms) >= 2
            or bool(suspicious_actions)
        )
        has_credential_harvest_form = (
            form_count > 0
            and password_field_count > 0
            and strong_credential_cues
            and not official_same_site_auth_surface
        )

        if has_credential_harvest_form:
            signals.append(
                self._signal(
                    signal_type=SignalType.CREDENTIAL_HARVEST_FORM,
                    severity=SignalSeverity.HIGH,
                    confidence=92 if suspicious_actions else 86,
                    message_key="signal.credential_capture_form_detected",
                    message_params=self._build_message_params(
                        form_count=form_count,
                        password_field_count=password_field_count,
                        account_hints=account_hints,
                        auth_hints=auth_hints,
                        matched_login_terms=matched_login_terms,
                        observed_actions=observed_actions,
                        suspicious_actions=suspicious_actions,
                    ),
                    tags=("html-form", "credential-collection"),
                )
            )

        has_suspicious_login_interface = (
            form_count > 0
            and len(matched_login_terms) >= 2
            and (
                password_field_count > 0 or bool(auth_hints) or bool(suspicious_actions)
            )
            and (
                bool(suspicious_actions)
                or suspicious_host_context
                or auth_challenge_surface
            )
            and not official_same_site_auth_surface
        )

        if has_suspicious_login_interface and not has_credential_harvest_form:
            signals.append(
                self._signal(
                    signal_type=SignalType.SUSPICIOUS_LOGIN_INTERFACE,
                    severity=SignalSeverity.MEDIUM,
                    confidence=79,
                    message_key="signal.suspicious_login_style_interface",
                    message_params=self._build_message_params(
                        form_count=form_count,
                        password_field_count=password_field_count,
                        account_hints=account_hints,
                        auth_hints=auth_hints,
                        matched_login_terms=matched_login_terms,
                        observed_actions=observed_actions,
                        suspicious_actions=suspicious_actions,
                    ),
                    tags=("login-ui", "html-content"),
                )
            )

        low_information_signal = self._low_information_signal(
            normalized_url=normalized_url,
            form_count=form_count,
            password_field_count=password_field_count,
            matched_login_terms=matched_login_terms,
            visible_token_count=visible_token_count,
            low_information_markers=low_information_markers,
        )
        if low_information_signal is not None:
            signals.append(low_information_signal)

        return signals

    def _low_information_signal(
        self,
        normalized_url: NormalizedUrl,
        form_count: int,
        password_field_count: int,
        matched_login_terms: list[str],
        visible_token_count: int,
        low_information_markers: list[str],
    ) -> AnalysisSignal | None:
        if form_count > 0 or password_field_count > 0 or matched_login_terms:
            return None

        path_is_root = normalized_url.decoded_path in {"", "/"}
        explicit_placeholder = bool(low_information_markers)
        extremely_low_information = path_is_root and visible_token_count <= 3

        if not explicit_placeholder and not extremely_low_information:
            return None

        if explicit_placeholder:
            message_key = "signal.parked_or_placeholder_landing_page"
            severity = SignalSeverity.HIGH
            confidence = 88
            message_params = {
                "evidence": [
                    evidence_ref(
                        "evidence.visible_text_tokens_found",
                        visible_token_count=visible_token_count,
                    ),
                    evidence_ref(
                        "evidence.matched_placeholder_markers",
                        markers=", ".join(low_information_markers[:3]),
                    ),
                ],
            }
            tags = ("parked-page", "placeholder-page")
        else:
            message_key = "signal.low_information_landing_page"
            severity = SignalSeverity.MEDIUM
            confidence = 72
            message_params = {
                "evidence": [
                    evidence_ref(
                        "evidence.visible_text_tokens_found",
                        visible_token_count=visible_token_count,
                    ),
                    evidence_ref("evidence.no_forms_or_meaningful_visible_copy"),
                ],
            }
            tags = ("low-information", "thin-content")

        return self._signal(
            signal_type=SignalType.LOW_INFORMATION_PAGE,
            severity=severity,
            confidence=confidence,
            message_key=message_key,
            message_params=message_params,
            tags=tags,
        )

    def _build_message_params(
        self,
        form_count: int,
        password_field_count: int,
        account_hints: list[str],
        auth_hints: list[str],
        matched_login_terms: list[str],
        observed_actions: list[str],
        suspicious_actions: list[str],
    ) -> dict[str, object]:
        evidence = [
            evidence_ref("evidence.html_forms_found", form_count=form_count),
            evidence_ref(
                "evidence.password_fields_found",
                password_field_count=password_field_count,
            ),
        ]

        if account_hints:
            evidence.append(
                evidence_ref(
                    "evidence.matched_account_input_hints",
                    hints=", ".join(account_hints[:4]),
                )
            )
        if auth_hints:
            evidence.append(
                evidence_ref(
                    "evidence.matched_auth_input_hints",
                    hints=", ".join(auth_hints[:4]),
                )
            )
        if matched_login_terms:
            evidence.append(
                evidence_ref(
                    "evidence.matched_login_wording",
                    terms=", ".join(matched_login_terms[:4]),
                )
            )
        if observed_actions:
            evidence.append(
                evidence_ref(
                    "evidence.observed_form_action",
                    action=observed_actions[0],
                )
            )
        if suspicious_actions:
            evidence.append(
                evidence_ref(
                    "evidence.suspicious_form_action",
                    action=suspicious_actions[0],
                )
            )

        return {"evidence": evidence}

    def _signal(
        self,
        signal_type: SignalType,
        severity: SignalSeverity,
        confidence: float,
        message_key: str,
        message_params: dict[str, object],
        tags: tuple[str, ...],
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


@dataclass(slots=True)
class _WorkingForm:
    action: str | None
    password_field_count: int = 0
    account_hints: set[str] = field(default_factory=set)
    auth_hints: set[str] = field(default_factory=set)
    button_labels: list[str] = field(default_factory=list)


class _LoginHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: list[ParsedForm] = []
        self.visible_text: list[str] = []
        self._current_form: _WorkingForm | None = None
        self._inside_button = False
        self._button_text: list[str] = []

    @classmethod
    def parse(cls, html: str) -> ParsedHtmlPage:
        parser = cls()
        parser.feed(html)
        parser.close()
        return ParsedHtmlPage(
            forms=tuple(parser.forms),
            visible_text=tuple(text for text in parser.visible_text if text),
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}

        if tag == "form":
            self._current_form = _WorkingForm(action=attr_map.get("action") or None)
            return

        if tag == "input":
            self._handle_input(attr_map)
            return

        if tag == "button":
            self._inside_button = True
            self._button_text = []
            value = _clean_text(attr_map.get("value", ""))
            if value and self._current_form is not None:
                self._current_form.button_labels.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "button":
            button_text = _clean_text(" ".join(self._button_text))
            if button_text:
                self.visible_text.append(button_text)
                if self._current_form is not None:
                    self._current_form.button_labels.append(button_text)
            self._inside_button = False
            self._button_text = []
            return

        if tag == "form" and self._current_form is not None:
            self.forms.append(
                ParsedForm(
                    action=self._current_form.action,
                    password_field_count=self._current_form.password_field_count,
                    account_hints=tuple(sorted(self._current_form.account_hints)),
                    auth_hints=tuple(sorted(self._current_form.auth_hints)),
                    button_labels=tuple(self._current_form.button_labels),
                )
            )
            self._current_form = None

    def handle_data(self, data: str) -> None:
        text = _clean_text(data)
        if not text:
            return

        self.visible_text.append(text)
        if self._inside_button:
            self._button_text.append(text)

    def _handle_input(self, attr_map: dict[str, str]) -> None:
        if self._current_form is None:
            return

        input_type = attr_map.get("type", "text").strip().lower()
        if input_type == "password":
            self._current_form.password_field_count += 1

        for candidate in _iter_input_hints(attr_map):
            matched_hint = _match_account_hint(candidate)
            if matched_hint is not None:
                self._current_form.account_hints.add(matched_hint)
            matched_auth_hint = _match_auth_hint(candidate)
            if matched_auth_hint is not None:
                self._current_form.auth_hints.add(matched_auth_hint)


def _iter_input_hints(attr_map: dict[str, str]) -> Iterable[str]:
    for key in ("name", "id", "placeholder", "autocomplete", "aria-label"):
        value = attr_map.get(key, "").strip().lower()
        if value:
            yield value


def _match_account_hint(candidate: str) -> str | None:
    for hint in sorted(_ACCOUNT_FIELD_HINTS):
        if hint in candidate:
            return hint
    return None


def _match_auth_hint(candidate: str) -> str | None:
    for hint in sorted(_AUTH_FIELD_HINTS):
        if hint in candidate:
            return hint
    return None


def _match_login_terms(text_fragments: Iterable[str]) -> list[str]:
    lowered = " ".join(fragment.lower() for fragment in text_fragments)
    return sorted(term for term in _LOGIN_TERMS if term in lowered)


def _match_low_information_markers(text_fragments: Iterable[str]) -> list[str]:
    lowered = " ".join(fragment.lower() for fragment in text_fragments)
    return sorted(marker for marker in _LOW_INFORMATION_MARKERS if marker in lowered)


def _visible_token_count(text_fragments: Iterable[str]) -> int:
    return len(
        {
            fragment
            for text in text_fragments
            for fragment in text.lower().replace("/", " ").split()
            if fragment
        }
    )


def _has_suspicious_host_context(normalized_url: NormalizedUrl) -> bool:
    host_tokens = _tokenize_host(normalized_url.host)
    return bool(
        _LOGIN_TERMS.intersection(host_tokens)
        or {"mail", "outlook", "paypal"}.intersection(host_tokens)
    )


def _is_official_same_site_auth_surface(
    normalized_url: NormalizedUrl,
    suspicious_actions: list[str],
) -> bool:
    official_auth_domains = {
        "apple.com",
        "dropbox.com",
        "github.com",
        "google.com",
        "live.com",
        "microsoftonline.com",
        "paypal.com",
    }
    return (
        normalized_url.registered_domain in official_auth_domains
        and not suspicious_actions
    )


def _tokenize_host(value: str) -> set[str]:
    return {
        fragment for fragment in value.replace(".", "-").lower().split("-") if fragment
    }


def _normalize_action(action: str, source_url: str) -> str:
    return urljoin(source_url, action)


def _is_suspicious_action(action: str, registered_domain: str) -> bool:
    parsed = urlsplit(action)
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return True
    if not parsed.hostname:
        return False
    return not parsed.hostname.lower().endswith(registered_domain.lower())


def _clean_text(value: str) -> str:
    return " ".join(value.split())
