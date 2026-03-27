from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlsplit

from app.application.ports.html_fetcher import FetchedHtmlDocument
from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS, SIGNAL_CATEGORY_MAP
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.normalized_url import NormalizedUrl

_LOGIN_TERMS = {
    "account",
    "confirm",
    "login",
    "log in",
    "password",
    "sign in",
    "signin",
    "verify",
}
_ACCOUNT_FIELD_HINTS = {"email", "identifier", "login", "mail", "user", "username"}
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
        password_field_count = sum(form.password_field_count for form in parsed_page.forms)
        account_hints = sorted(
            {hint for form in parsed_page.forms for hint in form.account_hints}
        )
        matched_login_terms = _match_login_terms(parsed_page.visible_text)
        visible_token_count = _visible_token_count(parsed_page.visible_text)
        low_information_markers = _match_low_information_markers(parsed_page.visible_text)
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
        strong_credential_cues = (
            bool(account_hints) or len(matched_login_terms) >= 2 or bool(suspicious_actions)
        )
        has_credential_harvest_form = (
            form_count > 0
            and password_field_count > 0
            and strong_credential_cues
        )

        if has_credential_harvest_form:
            signals.append(
                self._signal(
                    signal_type=SignalType.CREDENTIAL_HARVEST_FORM,
                    severity=SignalSeverity.HIGH,
                    confidence=92 if suspicious_actions else 86,
                    title="Credential capture form detected",
                    description=(
                        "The fetched HTML contains a form pattern consistent with credential "
                        "collection."
                    ),
                    evidence=self._build_evidence(
                        form_count=form_count,
                        password_field_count=password_field_count,
                        account_hints=account_hints,
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
            and (password_field_count > 0 or bool(suspicious_actions))
            and (bool(suspicious_actions) or suspicious_host_context)
        )

        if has_suspicious_login_interface and not has_credential_harvest_form:
            signals.append(
                self._signal(
                    signal_type=SignalType.SUSPICIOUS_LOGIN_INTERFACE,
                    severity=SignalSeverity.MEDIUM,
                    confidence=79,
                    title="Suspicious login-style interface",
                    description=(
                        "The fetched HTML exposes login-style wording and input hints that merit "
                        "credential-harvesting review."
                    ),
                    evidence=self._build_evidence(
                        form_count=form_count,
                        password_field_count=password_field_count,
                        account_hints=account_hints,
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
            title = "Parked or placeholder landing page"
            description = (
                "The fetched HTML looks like a parked domain, default hosting page, or placeholder landing page."
            )
            severity = SignalSeverity.HIGH
            confidence = 88
            evidence = (
                f"Visible text tokens found: {visible_token_count}.",
                f"Matched placeholder markers: {', '.join(low_information_markers[:3])}.",
            )
            tags = ("parked-page", "placeholder-page")
        else:
            title = "Low-information landing page"
            description = (
                "The fetched HTML contains almost no meaningful visible content, which limits confidence in a clean result."
            )
            severity = SignalSeverity.MEDIUM
            confidence = 72
            evidence = (
                f"Visible text tokens found: {visible_token_count}.",
                "The fetched landing page exposes no forms or meaningful visible copy.",
            )
            tags = ("low-information", "thin-content")

        return self._signal(
            signal_type=SignalType.LOW_INFORMATION_PAGE,
            severity=severity,
            confidence=confidence,
            title=title,
            description=description,
            evidence=evidence,
            tags=tags,
        )

    def _build_evidence(
        self,
        form_count: int,
        password_field_count: int,
        account_hints: list[str],
        matched_login_terms: list[str],
        observed_actions: list[str],
        suspicious_actions: list[str],
    ) -> tuple[str, ...]:
        evidence = [
            f"HTML forms found: {form_count}.",
            f"Password fields found: {password_field_count}.",
        ]

        if account_hints:
            evidence.append(f"Matched account input hints: {', '.join(account_hints[:4])}.")
        if matched_login_terms:
            evidence.append(f"Matched login wording: {', '.join(matched_login_terms[:4])}.")
        if observed_actions:
            evidence.append(f"Observed form action: {observed_actions[0]}.")
        if suspicious_actions:
            evidence.append(f"Suspicious form action: {suspicious_actions[0]}.")

        return tuple(evidence)

    def _signal(
        self,
        signal_type: SignalType,
        severity: SignalSeverity,
        confidence: float,
        title: str,
        description: str,
        evidence: tuple[str, ...],
        tags: tuple[str, ...],
    ) -> AnalysisSignal:
        return AnalysisSignal.create(
            signal_type=signal_type,
            category=SIGNAL_CATEGORY_MAP[signal_type],
            severity=severity,
            confidence=ConfidenceScore(confidence),
            title=title,
            description=description,
            source=self.source,
            base_weight=BASE_SIGNAL_WEIGHTS[signal_type],
            evidence=evidence,
            tags=tags,
        )


@dataclass(slots=True)
class _WorkingForm:
    action: str | None
    password_field_count: int = 0
    account_hints: set[str] = field(default_factory=set)
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
    return bool(_LOGIN_TERMS.intersection(host_tokens) or {"mail", "outlook", "paypal"}.intersection(host_tokens))


def _tokenize_host(value: str) -> set[str]:
    return {fragment for fragment in value.replace(".", "-").lower().split("-") if fragment}


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
