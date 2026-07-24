# Phase B — Headless Detonation (design & plan)

_Draft for review. Follows Phase A (typosquatting + fail-fast orchestrator)._

## 1. Goal

Move Verifiko from **static** analysis (URL + raw HTML + reputation) to **dynamic**
analysis: actually load a suspicious URL in a real, isolated browser ("detonate" it)
and observe what it *does*. This catches modern phishing that static analysis misses:
JavaScript-built login forms, multi-step JS redirects, cloaking, and off-domain
credential exfiltration. It's the stage URLert leans on ("Visual & Behavioral").

## 2. Where it fits in the architecture

Detonation is **slow and expensive**, so it does **not** run on the synchronous
`/verifications` path. It runs on the **async scan pipeline we already built**
(`submit → job → poll/webhook`, `VerificationScanProcessor`), off the request thread.

The **orchestrator** decides *whether* to detonate — this is the escalation half of the
work Phase A started:

- URL-only verdict **decisive malicious** (HIGH/CRITICAL) → already handled by fast-path,
  no detonation needed.
- URL-only verdict **clearly safe** → no detonation.
- URL-only verdict **suspicious / borderline** (the MEDIUM middle) **or** caller
  explicitly requests a deep scan → **detonate**.

This keeps cost bounded: we only pay for a browser on the URLs where it changes the answer.

## 3. Clean-architecture placement (ports & adapters)

- **Port** (`app/application/ports/headless_detonation.py`): `HeadlessDetonationPort`
  with `detonate(url) -> DetonationResult`.
- **DTO** `DetonationResult`: `final_url`, `js_redirect_chain`, `rendered_forms`
  (fields + action host), `third_party_hosts`, `downloads`, `page_title`,
  `detected_brand`, `screenshot_ref` (optional), `console_errors`, timing.
- **Adapter(s)** in `app/infrastructure/detonation/`: one real client for the chosen
  browser service, plus a `NullHeadlessDetonation` (no-op) for tests / when disabled.
- **Signal analyzer** (`app/application/services/behavioral_signal_analyzer.py`):
  turns a `DetonationResult` into `AnalysisSignal`s. New signal types (with weights,
  categories, EN/ES messages), e.g.:
  - `RENDERED_CREDENTIAL_FORM` — a password field appears only after JS renders.
  - `OFFSITE_FORM_ACTION` — the login form posts to a different domain (exfiltration).
  - `JS_REDIRECT_TO_OFFSITE` — the page navigates elsewhere via script.
  - `DRIVE_BY_DOWNLOAD` — an unsolicited download is triggered.
  - `CLOAKING_BEHAVIOR` — rendered content differs from the static HTML.
- **Orchestrator**: an escalation decision (`should_detonate(url_only_assessment)`),
  wired into the scan processor behind a feature flag.

Everything is flag-gated (`DETONATION_ENABLED`, default off) and validated against the
evaluation harness so precision cannot regress.

## 4. Security (non-negotiable — we load malicious pages on purpose)

- The browser must be **fully isolated** from our infrastructure: egress-only network,
  no route to internal services/metadata endpoints, non-root, locked-down container or a
  managed service that guarantees this.
- **Hard timeouts** and resource caps per detonation.
- **Downloads are captured as metadata only — never executed.**
- Redirects can steer the browser toward internal IPs → the isolation boundary (not just
  our existing SSRF guard) must prevent that.
- Nothing the page returns is ever `eval`'d or trusted; it's parsed as data only.

## 5. Open decisions (need your call)

1. **Where does Chromium run?**
   - *Managed browser API* (e.g. Browserless, Cloudflare Browser Rendering): no infra to
     run, sandboxing handled, pay-per-use, fastest to ship. Recommended for v1.
   - *Self-hosted container* (Cloud Run / Fly.io running Playwright): more control, scales
     to zero, but we own the hardening and ops.
2. **Screenshots now or later?** Capturing + storing a screenshot enables evidence and
   future computer-vision (brand-logo match, Phase C). Needs a blob store (Cloudflare R2 /
   Vercel Blob / S3). We can ship behavioral signals **without** screenshots first and add
   storage later.
3. **Escalation trigger:** async scan path only (recommended) vs. also offer a
   synchronous "deep scan" endpoint.

## 6. Phasing (small, independently shippable PRs)

- **B.1 — Behavioral core (no infra).** Port + `DetonationResult` DTO +
  `BehavioralSignalAnalyzer` + new signal types/scoring/i18n + orchestrator
  `should_detonate` decision. Fully unit-tested with fake detonation results. No browser
  yet. This is safe and lands the whole model.
- **B.2 — Browser adapter.** Real client for the chosen service + config + wiring into the
  scan processor, behind `DETONATION_ENABLED`. Integration-tested with a stub server.
- **B.3 — Evidence & screenshots** (optional). Blob storage + surface screenshot ref in
  the scan result / dashboard.
- **B.4 — Tune + harness.** Add detonation-dependent samples to the corpus, calibrate
  weights, confirm no precision regression.
- **(Phase C, later) — Computer vision** over the screenshot: brand-logo match, visual
  fake-login detection.

## 7. Recommended path

Start with **B.1** regardless of the infra decision — it's pure application/domain code,
fully testable, and lands the behavioral signal model + escalation gate without touching
infra. In parallel, pick the browser host (decision #1) so B.2 can follow immediately.
