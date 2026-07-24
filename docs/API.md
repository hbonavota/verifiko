# Verifiko API Reference

Verifiko is a URL reputation and phishing/malware detection API. Submit a URL,
get an explainable risk assessment: a score, a verdict, and the individual
signals behind it.

- **Base URL (production):** `https://api.verifiko.es`
- **Versioned prefix:** `/api/v1` (the stable, documented contract)
- **Interactive docs:** `https://api.verifiko.es/docs` (OpenAPI / Swagger UI)

> The unversioned `/api/*` paths still work for backwards compatibility but are
> undocumented. Build against `/api/v1`.

---

## Authentication

Most endpoints work anonymously (subject to a small daily quota). To raise your
quota, own your verification history, and use the async and management
endpoints, authenticate.

There are two credential types:

| Type | Header | Use for |
| --- | --- | --- |
| **API key** | `X-API-Key: vfk_live_…` **or** `Authorization: Bearer vfk_live_…` | Machine-to-machine / server integrations |
| **Session token** | `Authorization: Bearer <session_jwt>` | Browser / user sessions (obtained via `/auth/*`) |

### API keys

Create and manage keys from an authenticated session:

```
POST   /api/v1/keys          # create a key (returns the secret ONCE)
GET    /api/v1/keys          # list your keys (metadata only)
DELETE /api/v1/keys/{key_id} # revoke a key
```

Creating a key:

```bash
curl -X POST https://api.verifiko.es/api/v1/keys \
  -H "Authorization: Bearer <session_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "CI pipeline"}'
```

```json
{
  "id": "0c7b…",
  "name": "CI pipeline",
  "token_prefix": "vfk_live_a1b2c3",
  "created_at": "2026-07-23T12:00:00Z",
  "api_key": "vfk_live_a1b2c3d4e5f6…"
}
```

The `api_key` value is shown **only at creation** — store it securely. Verifiko
keeps only a hash. Listing keys never returns the secret.

Use the key on any endpoint:

```bash
curl https://api.verifiko.es/api/v1/verifications \
  -H "X-API-Key: vfk_live_a1b2c3d4e5f6…" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://site-to-check.example/login"}'
```

### Session auth (for user-facing apps)

```
POST /api/v1/auth/magic-link/request   # email -> emails a one-time sign-in link
POST /api/v1/auth/magic-link/consume   # token -> access_token
POST /api/v1/auth/google               # Google ID token -> access_token
POST /api/v1/auth/register             # email + password
POST /api/v1/auth/login                # email + password -> access_token
GET  /api/v1/me                        # current account
GET  /api/v1/me/verifications
```

**Magic link (passwordless).** The recommended email flow. Request a link, then
exchange the token embedded in it for a session.

```bash
curl -X POST https://api.verifiko.es/api/v1/auth/magic-link/request \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

Always returns `202 Accepted` with no body, regardless of whether the email is
registered — this prevents account enumeration. If the address is valid, an
email with a single-use link (`…/auth/magic?token=…`) is sent; the token expires
in 15 minutes and works once. Exchange it for a session:

```bash
curl -X POST https://api.verifiko.es/api/v1/auth/magic-link/consume \
  -H "Content-Type: application/json" \
  -d '{"token": "<token-from-the-link>"}'
```

Returns `200 OK` with an `access_token` (same shape as the other auth
endpoints), or `401` if the token is invalid, already used, or expired.

---

## Verify a URL (synchronous)

```
POST /api/v1/verifications
```

Request body:

```json
{ "url": "https://paypal.com.security-check.example/login" }
```

Response `201 Created` (abridged):

```json
{
  "id": "8f2c…",
  "status": "completed",
  "original_input": "https://paypal.com.security-check.example/login",
  "risk_assessment": {
    "score": 34,
    "risk_level": "HIGH",
    "verdict": "LIKELY_MALICIOUS",
    "summary": "…human-readable explanation…",
    "top_signals": ["Deceptive brand subdomain", "Credential-lure wording in URL"],
    "category_breakdown": { "domain_structure": 20, "content_behavior": 12 },
    "terminal_override_applied": false
  },
  "signals": [
    {
      "signal_type": "deceptive_brand_subdomain",
      "severity": "HIGH",
      "confidence": 94,
      "title": "…",
      "description": "…",
      "evidence": ["…"],
      "source": "url-rule-analyzer",
      "score_contribution": -20
    }
  ]
}
```

The verification is owned by the authenticated caller (if any) and can be
retrieved later:

```
GET /api/v1/verifications/{id}   # owner-only; 404 for non-owners
```

### Risk model

`score` runs from **0 (most malicious) to 100 (clean)**. It maps to a
`risk_level` and a `verdict`:

| Score | risk_level | verdict |
| --- | --- | --- |
| 81–100 | `SAFE` | `TRUSTED` |
| 61–80 | `LOW` | `CAUTION` |
| 41–60 | `MEDIUM` | `SUSPICIOUS` |
| 21–40 | `HIGH` | `LIKELY_MALICIOUS` |
| 0–20 | `CRITICAL` | `LIKELY_MALICIOUS` |

A confirmed reputation match (e.g. two independent feeds agreeing) triggers a
**terminal override**: `score = 0`, `verdict = CONFIRMED_MALICIOUS`,
`terminal_override_applied = true`.

Each `signal` in the response explains one contributing factor with its
`severity`, `confidence`, `evidence`, and `score_contribution`. Detection
combines deterministic URL/host/HTML/TLS heuristics with reputation feeds
(URLhaus, and OpenPhish when enabled) aggregated by consensus.

---

## Verify asynchronously (scans)

For bulk work or to avoid holding a request open, submit a **scan** and poll (or
receive a webhook) for the result. Scan endpoints require authentication.

```
POST /api/v1/scans          # submit one URL       -> 202
POST /api/v1/scans/batch    # submit up to 50 URLs -> 202
GET  /api/v1/scans/{scan_id}  # poll status / result
```

Submit:

```bash
curl -X POST https://api.verifiko.es/api/v1/scans \
  -H "X-API-Key: vfk_live_…" -H "Content-Type: application/json" \
  -d '{"url": "https://site.example", "webhook_url": "https://your-app.example/hooks/verifiko"}'
```

Response `202 Accepted`:

```json
{ "scan_id": "3d6f…", "status": "queued", "url": "https://site.example" }
```

Poll:

```bash
curl https://api.verifiko.es/api/v1/scans/3d6f… -H "X-API-Key: vfk_live_…"
```

```json
{
  "scan_id": "3d6f…",
  "status": "completed",
  "url": "https://site.example",
  "result_verification_id": "8f2c…",
  "result": { "…full verification response…" },
  "error": null
}
```

`status` is one of `queued`, `running`, `completed`, `failed`. When `completed`,
`result` embeds the full verification response. When `failed`, `error` explains
why (e.g. an unsupported URL). Scans are owner-scoped (404 for non-owners).

Batch:

```bash
curl -X POST https://api.verifiko.es/api/v1/scans/batch \
  -H "X-API-Key: vfk_live_…" -H "Content-Type: application/json" \
  -d '{"urls": ["https://a.example", "https://b.example"], "webhook_url": "https://your-app.example/hooks/verifiko"}'
```

```json
{ "scans": [ {"scan_id": "…", "status": "queued", "url": "https://a.example"}, … ] }
```

---

## Webhooks

Pass a `webhook_url` when submitting a scan and Verifiko will `POST` a signed
JSON notification to it once the scan reaches a terminal state — no polling
needed. `webhook_url` must be an `http(s)` URL; delivery is blocked to private or
special-use addresses.

Delivery payload:

```json
{
  "event": "scan.completed",
  "scan_id": "3d6f…",
  "status": "completed",
  "url": "https://site.example",
  "result_verification_id": "8f2c…",
  "error": null,
  "occurred_at": "2026-07-23T12:00:05Z"
}
```

`event` is `scan.completed` or `scan.failed`. Fetch the full result with
`GET /api/v1/scans/{scan_id}` or `GET /api/v1/verifications/{result_verification_id}`.

Delivery headers:

| Header | Meaning |
| --- | --- |
| `X-Verifiko-Event` | `scan.completed` \| `scan.failed` |
| `X-Verifiko-Delivery` | Unique delivery id |
| `X-Verifiko-Timestamp` | Unix seconds when signed |
| `X-Verifiko-Signature` | `sha256=<hmac>` (see below) |

### Verifying the signature

The signature is `HMAC-SHA256` over the string `"{timestamp}." + raw_body`, keyed
with your webhook signing secret, hex-encoded. Recompute it and compare in
constant time; reject if it doesn't match or the timestamp is too old.

```python
import hashlib, hmac

def is_valid(secret: str, timestamp: str, raw_body: bytes, header: str) -> bool:
    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", header)
```

Delivery is best-effort with automatic retries on failure. Because delivery is
not guaranteed, treat webhooks as an optimization and keep polling available as
the source of truth.

---

## Rate limits & quotas

Two independent controls protect the service:

- **Daily verification quota** (per identity, resets at 00:00 UTC):

  | Caller | Limit / day |
  | --- | --- |
  | Anonymous | 3 |
  | Authenticated · FREE | 10 |
  | Authenticated · PRO | 200 |

- **Burst limit**: short-window abuse protection on the verification endpoint.
  If burst blocks a request, your daily quota is **not** consumed.

Check your standing without spending quota:

```
GET /api/v1/verifications/quota-status
```

```json
{
  "subject_type": "USER", "plan": "FREE",
  "daily_limit": 10, "used_today": 2, "remaining_today": 8,
  "reset_at_utc": "2026-07-24T00:00:00Z", "reset_in_seconds": 43200, "blocked": false
}
```

When a limit is hit you get `429 Too Many Requests` with a `Retry-After` header.
Daily-quota responses also expose:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset` (Unix seconds)

---

## Errors

| Status | Meaning |
| --- | --- |
| `400` / `422` | Invalid request (bad URL, unsupported scheme, unresolvable/unsafe target, malformed body) |
| `401` | Missing or invalid credentials |
| `403` | Endpoint not available to this caller |
| `404` | Not found, or not owned by you (owner-scoped resources are non-enumerating) |
| `429` | Rate limit or daily quota exceeded (see `Retry-After`) |
| `5xx` | Unexpected server error |

Error bodies are localized (English/Spanish via `Accept-Language`) and shaped as
`{ "detail": "…" }`.

---

## Notes & limits

- Verification targets must be public `http`/`https` URLs; private, loopback, and
  special-use addresses are rejected (SSRF protection).
- Batch scans accept up to **50** URLs per request.
- Timestamps are ISO-8601 UTC (`…Z`).
- The full machine-readable schema is always at `/openapi.json`.
