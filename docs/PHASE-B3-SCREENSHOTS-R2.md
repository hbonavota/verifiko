# Phase B.3 — Screenshot capture + Cloudflare R2 storage (design & plan)

_Draft for review. Follows B.2 (detonation integrated + CredentialExfiltrationRule)._

## Goal

Persist the screenshot the headless browser already captures during detonation, and
surface it as `screenshot_ref` in the scan result + dashboard. This gives human-readable
evidence ("here's the fake login page we saw") and is the input for Phase C (computer
vision: brand-logo match, visual fake-login).

## What already exists

The `BrowserlessDetonationClient` JS already captures a base64 PNG (`screenshot_base64`),
but `_parse_detonation_response` drops it (`screenshot_ref=None`). B.3 wires the bytes to a
blob store and threads the resulting reference to the API/UI.

## Architecture (ports & adapters)

- **Port** `ScreenshotStorePort` (`app/application/ports/screenshot_store.py`):
  `store(image_bytes: bytes, *, key_hint: str) -> str` → returns an opaque `screenshot_ref`
  (the R2 object key).
- **Adapters** (`app/infrastructure/storage/`):
  - `R2ScreenshotStore` — S3-compatible PUT to Cloudflare R2 (via `boto3` with
    `endpoint_url=https://<accountid>.r2.cloudflarestorage.com`, R2 access key/secret).
  - `NullScreenshotStore` — no-op returning `None`; used when disabled / in tests.
- **Where the upload happens:** inject `ScreenshotStorePort` into
  `BrowserlessDetonationClient`. When a screenshot is captured and a real store is
  configured, upload it and set `DetonationResult.screenshot_ref` to the object key. Keeps
  the raw base64 out of `DetonationResult` (only the ref travels through the pipeline).
- **Serving it back:** the bucket is **private**; the API mints a **time-limited presigned
  GET URL** when returning a scan result. `screenshot_ref` stays the durable key; the
  presigned URL is generated on read (never stored).

## Threading `screenshot_ref` to the result

Detonation happens inside `CreateURLVerificationUseCase` (B.2b), so the ref flows out via
the DTO, and the scan job carries it (screenshot is a **scan-scoped** artifact — the sync
`/verifications` path never detonates, so it never has one):

1. `VerificationDTO` gains an optional `screenshot_ref`.
2. `CreateURLVerificationUseCase` sets it from the `DetonationResult` when detonation ran.
3. `VerificationScanProcessor` copies it onto the `VerificationJob`
   (**migration 0009**: add `screenshot_ref` column to `verification_jobs`).
4. The scan result route returns a presigned `screenshot_url` (generated from the key).
5. Frontend: show the screenshot in the scan/verification detail view.

## Phasing (small PRs)

- **B.3a — storage core.** `ScreenshotStorePort` + `R2ScreenshotStore` + `NullScreenshotStore`
  + settings (`R2_*`, `SCREENSHOT_STORAGE_ENABLED`) + inject into the detonation client so
  `screenshot_ref` gets populated. Unit-tested with a fake store / fake S3 client. Adds a
  `boto3` dependency. No pipeline/schema changes yet.
- **B.3b — surface it.** Thread `screenshot_ref` through DTO → job (migration 0009) → scan
  result schema (presigned URL) → dashboard display. Tests + migration.

## Decisions (recommended)

1. **R2 client:** `boto3` (S3-compatible, reliable). Adds one dependency. ✔ recommended.
2. **Bucket privacy:** **private + presigned GET URLs** (screenshots are of malicious pages;
   don't expose a public bucket). ✔ recommended.
3. **Screenshot lives on the scan job** (`verification_jobs`), not the core `verifications`
   table — keeps the sync path and the core schema untouched. ✔ recommended.
4. **Naming:** key `screenshots/{job_or_verification_id}/{uuid}.png`.
5. **Retention:** an R2 lifecycle rule (config in the R2 dashboard, not code) — e.g. expire
   after 60 days. Noted as an ops follow-up.

## Flags & safety

- `SCREENSHOT_STORAGE_ENABLED` (default off) → `NullScreenshotStore` when off, so nothing
  changes until R2 is configured. Screenshots only happen during detonation, which is itself
  behind `DETONATION_ENABLED`. Double-gated.
- Never store the raw image in Postgres; only the R2 key. Presigned URLs are short-lived.

## Out of scope (later)

- Computer vision over the screenshot (Phase C).
- Live Browserless smoke test (Phase B follow-up) — still pending before enabling in prod.
