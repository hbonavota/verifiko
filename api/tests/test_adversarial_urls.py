from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "url, expected_signal, min_score, min_verdict_keyword",
    [
        # P0: Userinfo evasion (paypal.com@evil.com)
        (
            "http://paypal.com@evil.com",
            "userinfo_present",
            70,
            "ROJO",
        ),
        (
            "http://[::1]/",
            "ip_host",
            30,
            "AMARILLO",
        ),
        # P0: Punycode detection (xn-- prefix)
        (
            "http://xn--pple-43d.com",
            "punycode_present",
            45,
            "AMARILLO",
        ),
        # P0: Percent encoding en host
        (
            "http://%70%61%79%70%61%6c.com",
            "percent_encoded_host",
            25,
            "AMARILLO",
        ),
        # P0: Double encoding pattern
        (
            "http://%252e%252e/evil",
            "double_encoded",
            30,
            "AMARILLO",
        ),
        # P1: IPv4 standard
        (
            "http://127.0.0.1/",
            "ip_host",
            30,
            "AMARILLO",
        ),
        # P1: Decimal-like IP
        (
            "http://2130706433/",
            "ip_like_host",
            20,
            "AMARILLO",
        ),
        # P1: Hex-like IP
        (
            "http://0x7f000001/",
            "ip_like_host",
            20,
            "AMARILLO",
        ),
        # P0: Shortener (bit.ly)
        (
            "http://bit.ly/abcdef",
            "shortener_detected",
            35,
            "AMARILLO",
        ),
        # P1: Many subdomains
        (
            "http://very.long.subdomain.example.paypal.co/login",
            "many_subdomains",
            15,
            "AMARILLO",
        ),
        # P1: Long hostname
        (
            "http://thisisaveryveryveryveryveryverylonghostnametotest.example",
            "long_hostname",
            20,
            "AMARILLO",
        ),
        # P1: Brand keyword in path
        (
            "http://login.paypal.com.evil.tld",
            "brand_keyword_in_host_or_path",
            20,
            "AMARILLO",
        ),
        # P1: Brand keyword in host
        (
            "https://paypal-login-secure-update.xyz/account/verify",
            "brand_keyword_in_host_or_path",
            20,
            "AMARILLO",
        ),
        # P0: Another shortener (tinyurl)
        (
            "http://tinyurl.com/abcdef",
            "shortener_detected",
            35,
            "AMARILLO",
        ),
        # P1: IPv4 private range
        (
            "http://192.168.1.1/",
            "ip_host",
            30,
            "AMARILLO",
        ),
        # P1: Percent encoding + brand
        (
            "http://%62%61%6e%6b.example.com",
            "percent_encoded_host",
            25,
            "AMARILLO",
        ),
    ],
)
def test_adversarial_urls(client, url, expected_signal, min_score, min_verdict_keyword):
    """
    Tests adversariales: verificar que cada URL evasiva dispara
    la señal esperada y alcanza el score/veredicto mínimo.

    Flujo:
    1. POST /scan/url con URL adversaria
    2. Verificar que signal esperada está presente
    3. Verificar que score >= min_score
    4. Verificar que verdict contiene keyword mínimo
    """
    # POST /scan/url
    r = client.post("/scan/url", json={"url": url})
    assert r.status_code == 200, f"POST /scan/url failed for {url}: {r.text}"
    data = r.json()
    scan_id = data["id"]

    # GET /scan/{id}/signals
    r_signals = client.get(f"/scan/{scan_id}/signals")
    assert r_signals.status_code == 200
    signals_data = r_signals.json()
    signal_names = {s["name"] for s in signals_data.get("signals", [])}
    assert expected_signal in signal_names, (
        f"Expected signal '{expected_signal}' not in {signal_names} for {url}"
    )

    # GET /scan/{id} para score y verdict
    r_scan = client.get(f"/scan/{scan_id}")
    assert r_scan.status_code == 200
    scan = r_scan.json()
    score = int(scan.get("score", 0))
    verdict = scan.get("verdict", "")

    assert score >= min_score, f"Score {score} < min_score {min_score} for {url}"
    assert min_verdict_keyword in verdict, (
        f"Verdict '{verdict}' does not contain '{min_verdict_keyword}' for {url}"
    )
