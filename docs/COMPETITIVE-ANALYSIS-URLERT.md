# Competitive Analysis — URLert (and the Verifiko roadmap to beat it)

_Last updated: 2026-07-24. Based on a full read of urlert.com and developer.urlert.com._

## 1. What URLert is

URLert ("Is this link safe?") is an AI-powered URL/link threat-detection service that
competes exactly where Verifiko does: real-time phishing / scam / "zero-day" detection.
It ships three things at once:

1. A **free consumer web tool** ("Start Investigation") — top of funnel.
2. A **developer API** (pay-as-you-go) — the monetization engine.
3. A **threat-intelligence content layer** (domain pages, threat feed, blog) — SEO moat.

Company: URLERT LLC (Texas), started 2025, incorporated early 2026. Small/new — beatable.

## 2. Their detection engine (the "model to replicate")

URLert describes a **5-stage multi-agent forensic pipeline** with a cost-aware orchestrator:

1. **Domain Intelligence** — typosquatting (`paypa1.com`), domain age, high-risk TLDs.
   Cheap checks that kill obvious junk "before it even loads".
2. **The Orchestrator ("Fail-Fast")** — if the domain is obviously malicious, stop; if
   suspicious, escalate to deeper (expensive) scans. **Smart routing to optimize
   speed and cost.** This is the crux of the whole design.
3. **Static & Cloaking Analysis** — fetch the page as **multiple user-agents
   simultaneously** (Mobile, Desktop, GoogleBot) to force cloaking attacks to reveal
   the payload they only show mobile victims.
4. **Visual & Behavioral** — for high-stakes URLs, launch a **headless browser** +
   **computer vision** to "see" the page: fake login forms, brand-logo impersonation,
   drive-by downloads.
5. **AI SOC Analyst** — an **LLM synthesizer** reviews all findings and writes a
   human-readable executive summary of *why* the site is dangerous.

**Key insight:** their "AI/ML" is mostly **LLM orchestration + a synthesizer**, not a
bespoke trained classifier. That is *easier* to replicate than training an ML model,
and it reframes our PR #6 (see §6).

## 3. Their API & business model

Async "Hybrid" pattern (identical in spirit to what Verifiko already built for scans):

- `POST /v2/...` → cache hit returns `200` immediately at a reduced price; cache miss
  returns `202 Accepted` + `job_id` + `status_url`.
- Poll `GET .../jobs/{id}` every 2–5s → `processing` / `complete` / `failed`.
- Charges on submission; **auto-refund if the job fails on their end**; every response
  carries an `X-Charge-Amount` header.

Three separately-priced products:

| Product | Price | Notes |
| --- | --- | --- |
| Domain Classification | $0.001 cache hit / $0.01 cache miss / $0 not-found | Identity/category of a domain |
| Domain Risk Analysis | $0.0025 / request | Typosquat, domain age, risk factors |
| URL Threat Detection | $0.02 / request | The deep headless+CV+LLM scan |

- **Free tier:** ~400 free scans after email verification, no credit card.
- **Pricing:** pay-as-you-go, balance/credits based, "as low as $0.0025/scan".
- **Rate limits:** per-org, per-minute (10/min POST, 60/min poll).
- **Growth loops:** programmatic SEO on `/domains/{domain}` pages + `/threat-report` +
  `/threat-feed` + `/blog`; a **Chrome extension** ("URLert Guard") for consumer reach;
  an **affiliate / reader-supported** model to fund the free tools.

> Note: Verifiko's own dashboard already surfaces `urlert.com/domains/…` links — proof
> their programmatic-SEO layer is capturing exactly the traffic we want.

## 4. Where Verifiko already matches or LEADS

We are much closer than it looks. Already shipped:

- **Clean Architecture (ports/adapters)** — far easier to extend than a monolith.
- **Async scan pipeline** (submit → poll) — the same "Hybrid" pattern URLert sells.
- **Webhooks** — URLert only documents polling; we already push. Advantage: us.
- **API keys + `/v1` versioning** + published API reference.
- **Evaluation harness** (precision/recall, regression gate) — a quality moat URLert
  doesn't advertise. This is our safety net for adding AI without regressing.
- **Deterministic, explainable signals + i18n (EN/ES)** — URLert is `en_US` only.
  Bilingual + the Spanish-speaking market is a real wedge.
- **Multi-user-agent anti-cloaking already in progress** (`feat/anti-camouflage-*`).
- **Reputation aggregation with 2-of-N consensus + circuit breaker**, parallel lookups,
  caching, fail-open limiters, Postgres-backed durable state. Solid, cheap foundation.

## 5. Gaps to close (what they have that we don't yet)

1. **Cost-aware orchestrator / tiered "fail-fast" routing** — run cheap checks first,
   only escalate to expensive stages when warranted. Prerequisite for affording
   headless + LLM without blowing latency/cost.
2. **Typosquatting detection** — cheap, high signal, easy win.
3. **Headless detonation** — render the live page, capture JS redirects, final DOM,
   third-party requests, and a screenshot. (PR #6, part 1.)
4. **Computer-vision-style signals** — fake-login-form detection, brand-logo match.
   Can start as heuristics (password field + off-domain form action + brand keywords)
   before any real CV.
5. **LLM synthesizer** — turn findings into a verdict + human-readable executive
   summary (URLert's headline feature).
6. **Domain classification product** — a second revenue line and the SEO engine.
7. **Usage-based billing** — credits/balance, per-request pricing, charge transparency,
   auto-refund on failure.
8. **Growth loops** — programmatic SEO (`/domains/*`, threat feed) + Chrome extension.

## 6. Reframed PR #6 — phased plan

URLert proves the winning design is **headless detonation feeding an LLM synthesizer**,
gated by a **cost-aware orchestrator** — not a hand-trained ML model. Proposed phases,
each a small, independently shippable PR behind a feature flag, validated against the
evaluation harness so we never regress precision:

- **Phase A — Orchestrator + typosquatting.** Introduce tiered routing (cheap domain
  stage can short-circuit; suspicious → escalate). Add a typosquat analyzer. Pure
  in-process, no new infra, immediate detection lift + the cost control everything else
  depends on.
- **Phase B — Headless detonation service.** A separate worker (NOT Vercel — Chromium
  needs a container: Fly.io / Cloud Run / Render, or a managed browser like
  Browserless). Sandboxed, timeouts, no secrets, egress-controlled. Produces new
  signals: JS-driven redirects, final URL, rendered DOM, third-party calls, screenshot.
  Wired in as optional signals behind a flag; only invoked for "suspicious" URLs by the
  orchestrator.
- **Phase C — Visual/behavioral signals.** Fake-login detection + brand impersonation,
  starting heuristic, upgradeable to real CV later.
- **Phase D — LLM synthesizer.** Optional stage that composes findings into a verdict +
  executive summary. Deterministic signals stay the guardrail; the harness gates any
  false-positive regression.
- **Phase E — Business layer.** Usage-based billing (credits, per-request price,
  auto-refund), domain-classification product, programmatic SEO pages + threat feed,
  Chrome extension funnel.

## 7. Positioning to WIN (not just match)

- **Explainability + evals as a promise**, not marketing: publish precision/recall,
  offer reproducible verdicts. URLert asks for trust; we can *show* it.
- **Bilingual / LATAM-first.** URLert is English-only. Own Spanish-speaking SMB + the
  region's regulatory/notification needs.
- **Webhooks + developer ergonomics** beyond polling.
- **Transparent, undercut pricing** on the cheap tiers where our costs are low.
- **Privacy stance** as a differentiator (URLert is affiliate/reader-supported).

Bottom line: we don't need to invent anything URLert hasn't; we need the orchestrator,
the headless stage, and an LLM synthesizer — and we already own the harder-to-copy parts
(clean architecture, async pipeline, webhooks, evaluation harness, bilingual UX).

---

### Sources
- URLert — home: https://www.urlert.com/
- URLert — How it works: https://www.urlert.com/how
- URLert — Threat report: https://www.urlert.com/threat-report
- URLert — API overview: https://developer.urlert.com/documentation
- URLert — V2 API guide: https://developer.urlert.com/documentation/v2-api
- URLert — URL Threat Detection (V2): https://developer.urlert.com/documentation/threat-detection-v2
- URLert — Domain Classification: https://developer.urlert.com/documentation/domain-classification
