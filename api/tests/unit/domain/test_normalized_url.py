from app.domain.value_objects.normalized_url import NormalizedUrl


def test_normalized_url_uses_multi_label_public_suffixes() -> None:
    normalized = NormalizedUrl.from_raw("https://login.example.co.uk/account")

    assert normalized.registered_domain == "example.co.uk"
    assert normalized.subdomain == "login"


def test_normalized_url_decodes_obfuscated_components_and_tracks_userinfo() -> None:
    normalized = NormalizedUrl.from_raw(
        "https://paypal.com@xn--pple-43d.com/%256Cogin?continue=https%253A%252F%252Fevil.test%252F"
    )

    assert normalized.contains_punycode is True
    assert normalized.has_userinfo is True
    assert normalized.userinfo == "paypal.com"
    assert normalized.decoded_path == "/login"
    assert normalized.decoded_query == "continue=https://evil.test/"
