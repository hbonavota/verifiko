from app.application.ports.headless_detonation import DetonationForm, DetonationResult
from app.application.services.behavioral_signal_analyzer import BehavioralSignalAnalyzer
from app.domain.enums.signal_type import SignalType


def _types(result: DetonationResult) -> set[SignalType]:
    return {s.signal_type for s in BehavioralSignalAnalyzer().analyze(result)}


def test_rendered_password_form_flags_credential_form() -> None:
    result = DetonationResult(
        requested_url="https://shop.example/login",
        final_url="https://shop.example/login",
        forms=(DetonationForm(has_password_field=True, action_host="shop.example"),),
    )
    assert SignalType.RENDERED_CREDENTIAL_FORM in _types(result)
    # Same-domain submission is not credential exfiltration.
    assert SignalType.OFFSITE_FORM_ACTION not in _types(result)


def test_offsite_form_action_flags_exfiltration() -> None:
    result = DetonationResult(
        requested_url="https://secure-login.example/",
        final_url="https://secure-login.example/",
        forms=(DetonationForm(has_password_field=True, action_host="collector.evil.net"),),
    )
    types = _types(result)
    assert SignalType.RENDERED_CREDENTIAL_FORM in types
    assert SignalType.OFFSITE_FORM_ACTION in types


def test_offsite_form_to_trusted_idp_is_not_flagged() -> None:
    # Posting credentials to a legitimate IdP/PSP (federated auth) is expected,
    # not exfiltration — even though the page is on a different registered domain.
    result = DetonationResult(
        requested_url="https://app.mycompany.example/login",
        final_url="https://app.mycompany.example/login",
        forms=(DetonationForm(has_password_field=True, action_host="auth0.com"),),
    )
    types = _types(result)
    assert SignalType.RENDERED_CREDENTIAL_FORM in types
    assert SignalType.OFFSITE_FORM_ACTION not in types


def test_offsite_form_to_trusted_idp_subdomain_is_not_flagged() -> None:
    # The allowlist matches on eTLD+1, so IdP subdomains are trusted too.
    result = DetonationResult(
        requested_url="https://app.mycompany.example/login",
        final_url="https://app.mycompany.example/login",
        forms=(DetonationForm(has_password_field=True, action_host="login.okta.com"),),
    )
    types = _types(result)
    assert SignalType.RENDERED_CREDENTIAL_FORM in types
    assert SignalType.OFFSITE_FORM_ACTION not in types


def test_offsite_form_to_untrusted_domain_is_still_flagged() -> None:
    # A form posting to an attacker domain that is NOT in the allowlist still fires.
    result = DetonationResult(
        requested_url="https://app.mycompany.example/login",
        final_url="https://app.mycompany.example/login",
        forms=(DetonationForm(has_password_field=True, action_host="collector.evil.net"),),
    )
    assert SignalType.OFFSITE_FORM_ACTION in _types(result)


def test_js_redirect_to_different_registered_domain_is_flagged() -> None:
    result = DetonationResult(
        requested_url="https://link.example/promo",
        final_url="https://totally-different.net/landing",
    )
    assert SignalType.JS_REDIRECT_TO_OFFSITE in _types(result)


def test_same_registered_domain_redirect_is_not_flagged() -> None:
    result = DetonationResult(
        requested_url="https://example.com/a",
        final_url="https://www.example.com/b",  # same registered domain
    )
    assert SignalType.JS_REDIRECT_TO_OFFSITE not in _types(result)


def test_unsolicited_download_is_flagged() -> None:
    result = DetonationResult(
        requested_url="https://example.com/",
        final_url="https://example.com/",
        downloads=("invoice.exe",),
    )
    assert SignalType.DRIVE_BY_DOWNLOAD in _types(result)


def test_clean_page_produces_no_behavioral_signals() -> None:
    result = DetonationResult(
        requested_url="https://example.com/",
        final_url="https://example.com/",
        forms=(DetonationForm(has_password_field=False, action_host="example.com"),),
    )
    assert _types(result) == set()
