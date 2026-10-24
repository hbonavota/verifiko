# outbound-fetch-guard: baseline review

The SSRF guard that protects outbound requests to user-controlled destinations was first
captured as a baseline OpenSpec spec, extracted from the code as it stood. The spec is
[`openspec/specs/outbound-fetch-guard/spec.md`](../openspec/specs/outbound-fetch-guard/spec.md),
added in [#87](https://github.com/hbonavota/verifiko/pull/87). The guard was then reviewed
against that spec for undocumented rules, test gaps, and possible bypasses.

## Outcome

The review found two gaps on the scan-webhook delivery path and one in how IPv6 transition
addresses were classified. All three are fixed, and each fix has regression tests:

- **Webhook delivery ([#88](https://github.com/hbonavota/verifiko/pull/88)).** Webhooks are
  delivered over the same IP-pinned client as the verification path. Delivery validates and
  connects to a single resolved address, does not re-resolve DNS, and does not follow
  redirects. The guard and the client use the same URL parser.
- **IPv6 transition addresses ([#89](https://github.com/hbonavota/verifiko/pull/89)).** The
  guard extracts the IPv4 address embedded in IPv4-mapped, 6to4, Teredo, NAT64
  (`64:ff9b::/96`) and IPv4-compatible forms and validates it too. An IPv6 address can no
  longer pass as global while pointing at a private IPv4 host.

The review also confirmed what the guard already covered: DNS-rebinding protection through
connection pinning, per-hop validation of redirects on the verification path, and validation
of the resolved address rather than its textual form, so alternative IPv4 notations don't
help. Rejections are all-or-nothing: one non-global DNS answer blocks the destination.

Lower-risk hardening follow-ups and test-coverage gaps from the review are tracked
separately. Behavior changes to the guard go through OpenSpec against the spec above.
