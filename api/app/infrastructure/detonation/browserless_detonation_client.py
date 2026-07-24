from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.application.ports.headless_detonation import (
    DetonationForm,
    DetonationResult,
    HeadlessDetonationError,
    HeadlessDetonationPort,
)

# (url, headers, body) -> (HTTP status code, response body text).
DetonationHttpPoster = Callable[[str, dict[str, str], bytes], tuple[int, str]]

# Browser-side script executed inside Browserless's isolated Chromium via the
# /function endpoint. It loads the URL, lets scripts run, and returns ONLY the
# observations our behavioral analyzer needs — never a verdict. The page content
# is treated as data; nothing it returns is executed on our side.
_DETONATION_SCRIPT = """
export default async function ({ page, context }) {
  const { url, captureScreenshot } = context;
  const downloads = [];
  try {
    const client = await page.target().createCDPSession();
    await client.send('Page.setDownloadBehavior', { behavior: 'deny' });
    client.on('Page.downloadWillBegin', (e) => downloads.push(e.suggestedFilename || e.url));
  } catch (e) { /* download hooks are best-effort */ }

  const thirdParty = new Set();
  const pageHost = (() => { try { return new URL(url).hostname; } catch (e) { return ''; } })();
  page.on('request', (req) => {
    try {
      const h = new URL(req.url()).hostname;
      if (h && h !== pageHost) thirdParty.add(h);
    } catch (e) {}
  });

  let timedOut = false;
  try {
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 20000 });
  } catch (e) { timedOut = true; }

  const finalUrl = page.url();
  const pageTitle = await page.title().catch(() => null);

  const forms = await page.evaluate(() => {
    const out = [];
    for (const f of Array.from(document.querySelectorAll('form'))) {
      const hasPassword = !!f.querySelector('input[type="password"]');
      let actionHost = null;
      try { actionHost = f.action ? new URL(f.action, document.baseURI).hostname : null; } catch (e) {}
      out.push({ has_password_field: hasPassword, action_host: actionHost });
    }
    // Password fields outside a <form> still indicate a credential surface.
    if (out.length === 0 && document.querySelector('input[type="password"]')) {
      out.push({ has_password_field: true, action_host: null });
    }
    return out;
  }).catch(() => []);

  let screenshot = null;
  if (captureScreenshot) {
    try {
      screenshot = await page.screenshot({ encoding: 'base64', type: 'png' });
    } catch (e) {}
  }

  return {
    data: {
      requested_url: url,
      final_url: finalUrl,
      page_title: pageTitle,
      forms,
      third_party_hosts: Array.from(thirdParty),
      downloads,
      screenshot_base64: screenshot,
      timed_out: timedOut,
    },
    type: 'application/json',
  };
}
"""


@dataclass(slots=True)
class BrowserlessDetonationClient(HeadlessDetonationPort):
    """Detonates a URL in Browserless's managed, isolated Chromium.

    Transport is a single HTTP POST to the Browserless ``/function`` endpoint, so
    no browser runs in our process. The endpoint URL (which carries the token)
    and the HTTP poster are injected, keeping this adapter fully unit-testable and
    independent of whether Browserless is managed or self-hosted.
    """

    endpoint: str
    http_poster: DetonationHttpPoster
    capture_screenshot: bool = True

    def detonate(self, url: str) -> DetonationResult:
        payload = json.dumps(
            {
                "code": _DETONATION_SCRIPT,
                "context": {"url": url, "captureScreenshot": self.capture_screenshot},
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        status, body = self.http_poster(self.endpoint, headers, payload)
        if not 200 <= status < 300:
            raise HeadlessDetonationError(
                f"Browserless returned HTTP {status}: {body[:200]}"
            )
        return _parse_detonation_response(url, body)


class NullHeadlessDetonation(HeadlessDetonationPort):
    """No-op detonation used when the feature is disabled or in tests. Reports a
    benign result so an accidental call can never fabricate risk."""

    def detonate(self, url: str) -> DetonationResult:
        return DetonationResult(requested_url=url, final_url=url)


def _parse_detonation_response(requested_url: str, body: str) -> DetonationResult:
    try:
        payload: Any = json.loads(body)
    except (json.JSONDecodeError, TypeError) as exc:
        raise HeadlessDetonationError("Browserless returned a non-JSON body") from exc

    # Browserless may wrap the function's return under a "data" key; accept both.
    data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
    if not isinstance(data, dict):
        raise HeadlessDetonationError("Browserless response had no result object")

    forms = tuple(
        DetonationForm(
            has_password_field=bool(form.get("has_password_field")),
            action_host=form.get("action_host") or None,
        )
        for form in data.get("forms", [])
        if isinstance(form, dict)
    )
    return DetonationResult(
        requested_url=requested_url,
        final_url=data.get("final_url") or requested_url,
        forms=forms,
        third_party_hosts=tuple(h for h in data.get("third_party_hosts", []) if h),
        downloads=tuple(d for d in data.get("downloads", []) if d),
        page_title=data.get("page_title") or None,
        detected_brand=data.get("detected_brand") or None,
        screenshot_ref=None,  # populated by the screenshot storage step (B.3)
        timed_out=bool(data.get("timed_out", False)),
    )


def build_urllib_detonation_poster(timeout_seconds: float = 30.0) -> DetonationHttpPoster:
    def _post(url: str, headers: dict[str, str], body: bytes) -> tuple[int, str]:
        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return response.status, response.read().decode("utf-8", "replace")
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", "replace")
            except Exception:  # noqa: BLE001
                detail = ""
            return exc.code, detail
        except (URLError, TimeoutError, OSError) as exc:
            raise HeadlessDetonationError(str(exc)) from exc

    return _post
