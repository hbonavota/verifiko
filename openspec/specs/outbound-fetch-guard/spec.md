# outbound-fetch-guard Specification

## Purpose

Prevent server-side request forgery (SSRF) when the API makes outbound network calls to
user-controlled destinations: the verification target URL (redirect resolution, HTML
fetches, TLS validation, DNS/infrastructure lookup) and the scan webhook URL. The guard
validates the scheme and hostname, resolves the host, and rejects the destination unless
every resolved address is globally routable. Network adapters then connect only to the
addresses that were validated.

This is a baseline spec extracted from the code as of `main@d3f9dfb`. It describes
current behavior only. Gaps, ambiguities and suspected bypasses are in
`docs/openspec-baseline-findings.md`, not here.

Outbound calls to fixed, operator-configured hosts (reputation feeds, RDAP, Browserless,
email, Google token info, the internal scan dispatcher) do not use this guard and are out
of scope.

## Requirements

### Requirement: Only HTTP and HTTPS URLs are accepted

When the guard validates a URL, it SHALL reject any scheme other than `http` or `https`
and SHALL reject a URL that has no hostname.

Source: api/app/infrastructure/external_services/outbound_target_guard.py:resolve_safe_outbound_url

#### Scenario: Non-HTTP scheme is rejected

- **WHEN** `resolve_safe_outbound_url` is called with a URL whose scheme is not `http` or `https` (for example `ftp://` or `file://`)
- **THEN** it raises `UnsafeOutboundTargetError` with the message key `error.only_http_https_outbound_targets_allowed`
- **AND** no DNS resolution is attempted

Test: NONE

#### Scenario: URL without a hostname is rejected

- **WHEN** `resolve_safe_outbound_url` is called with an `http`/`https` URL whose parsed hostname is empty
- **THEN** it raises `UnsafeOutboundTargetError` with the message key `error.outbound_target_host_required`

Test: NONE

### Requirement: Hostnames are normalized before validation

The guard SHALL strip surrounding whitespace, lowercase the hostname and remove trailing
dots before applying any hostname rule. A hostname that is empty after normalization
MUST be rejected.

Source: api/app/infrastructure/external_services/outbound_target_guard.py:resolve_safe_outbound_host

#### Scenario: Trailing dot and uppercase do not evade the hostname rules

- **WHEN** the guard validates the host `LOCALHOST.`
- **THEN** it is treated as `localhost` and rejected as a local hostname

Test: NONE

#### Scenario: Empty hostname is rejected

- **WHEN** `resolve_safe_outbound_host` is called with a hostname that is empty after normalization (for example `" . "`)
- **THEN** it raises `UnsafeOutboundTargetError` with the message key `error.outbound_target_host_required`

Test: NONE

### Requirement: Local and special-use hostnames are blocked

The guard SHALL reject the hostname `localhost` and any hostname ending in `.internal`,
`.local`, `.localhost` or `.home.arpa`, before any DNS resolution.

Source: api/app/infrastructure/external_services/outbound_target_guard.py:resolve_safe_outbound_host

#### Scenario: localhost is rejected

- **WHEN** the guard validates the host `localhost`
- **THEN** it raises `UnsafeOutboundTargetError` with the message key `error.outbound_target_local_special_use_blocked`

Test: api/tests/unit/infrastructure/test_outbound_target_guard.py::test_outbound_target_guard_blocks_localhost

#### Scenario: Special-use suffixes are rejected

- **WHEN** the guard validates a host such as `metadata.internal`, `printer.local`, `app.localhost` or `router.home.arpa`
- **THEN** it raises `UnsafeOutboundTargetError` with the message key `error.outbound_target_local_special_use_blocked`

Test: NONE

### Requirement: Single-label hostnames are blocked

The guard SHALL reject a hostname that contains no dot unless it parses as an IP address
literal.

Source: api/app/infrastructure/external_services/outbound_target_guard.py:resolve_safe_outbound_host

#### Scenario: Single-label hostname is rejected

- **WHEN** a verification is requested for the URL `A` (normalized to `https://a/`)
- **THEN** the guard raises `UnsafeOutboundTargetError` with the message key `error.outbound_target_single_label_blocked`

Test: api/tests/unit/application/test_create_url_verification_use_case.py::test_create_url_verification_use_case_rejects_single_label_targets

#### Scenario: Dotless decimal IPv4 form is rejected as single-label

- **WHEN** the guard validates the host `2130706433` (a dotless decimal IPv4 form that `ipaddress` does not parse as an IP)
- **THEN** it is rejected by the single-label rule before DNS resolution

Test: NONE

### Requirement: Every resolved address must be globally routable

The guard SHALL resolve the hostname with `socket.getaddrinfo` (TCP, at the effective
port), deduplicate the addresses, and reject the destination if **any** resolved address
is not globally routable according to Python's `ipaddress` `is_global`. This applies to
IP literals too, which resolve to themselves. On success it SHALL return the normalized
hostname, the effective port and the validated addresses in resolver order.

Source: api/app/infrastructure/external_services/outbound_target_guard.py:resolve_safe_outbound_host, _resolve_host_addresses

#### Scenario: Loopback literal is rejected

- **WHEN** the guard validates the host `127.0.0.1`
- **THEN** it raises `UnsafeOutboundTargetError` with the message key `error.outbound_target_private_special_use_address_blocked`

Test: api/tests/unit/infrastructure/test_outbound_target_guard.py::test_outbound_target_guard_blocks_private_ip_targets

#### Scenario: Public hostname resolving to a private address is rejected

- **WHEN** a hostname resolves to `127.0.0.1`
- **THEN** the guard raises `UnsafeOutboundTargetError`

Test: api/tests/unit/infrastructure/test_outbound_target_guard.py::test_outbound_target_guard_blocks_resolution_to_private_address

#### Scenario: Cloud metadata link-local address is rejected

- **WHEN** a host is, or resolves to, `169.254.169.254`
- **THEN** the guard raises `UnsafeOutboundTargetError` because the address is link-local (not global)

Test: NONE

#### Scenario: Mixed public and private answers are rejected

- **WHEN** a hostname resolves to one public address and one private address
- **THEN** the guard raises `UnsafeOutboundTargetError`, even though one answer is public

Test: NONE

#### Scenario: Non-global IPv6 resolutions are rejected

- **WHEN** a hostname resolves to `::1`, a unique-local (`fd00::/8`) address, or an IPv4-mapped address of a private IPv4 (for example `::ffff:127.0.0.1`)
- **THEN** the guard raises `UnsafeOutboundTargetError`

Test: NONE

#### Scenario: Non-canonical IPv4 forms are judged by their resolved address

- **WHEN** the host is a dotted non-canonical IPv4 form (for example hexadecimal `0x7f.1`) that the system resolver maps to a non-global address
- **THEN** the guard rejects it, because it validates the address returned by `getaddrinfo` rather than the textual host

Test: NONE

#### Scenario: Public hostname returns its validated addresses

- **WHEN** `example.org` resolves only to public addresses
- **THEN** the guard returns `SafeOutboundResolution(hostname="example.org", port=443, ip_addresses=(...))` with the addresses in resolver order

Test: api/tests/unit/infrastructure/test_outbound_target_guard.py::test_outbound_target_guard_resolves_public_host_to_validated_ips

### Requirement: DNS resolution failures fail closed

The guard SHALL treat a resolution failure as an unsafe target. A name-resolution error
(`socket.gaierror`) MUST be rejected immediately without retry. Any other `OSError` (for
example `EBUSY` from a contended resolver) SHALL be retried up to 3 attempts in total with
a short linear backoff, and rejected if every attempt fails.

Source: api/app/infrastructure/external_services/outbound_target_guard.py:_getaddrinfo_with_retry

#### Scenario: NXDOMAIN is rejected without retry

- **WHEN** `getaddrinfo` raises `socket.gaierror`
- **THEN** the guard raises `UnsafeOutboundTargetError` with the message key `error.outbound_target_host_unresolved_for_safety_validation`
- **AND** `getaddrinfo` was called exactly once

Test: api/tests/unit/infrastructure/test_outbound_target_guard.py::test_outbound_target_guard_does_not_retry_name_resolution_failure

#### Scenario: Transient resolver error is retried

- **WHEN** `getaddrinfo` raises `OSError(EBUSY)` twice and then succeeds
- **THEN** the guard returns the validated resolution after the third attempt

Test: api/tests/unit/infrastructure/test_outbound_target_guard.py::test_outbound_target_guard_retries_transient_resolver_error

#### Scenario: Persistent resolver error is rejected

- **WHEN** `getaddrinfo` raises a non-`gaierror` `OSError` on every attempt
- **THEN** the guard raises `UnsafeOutboundTargetError` (never a raw `OSError`)

Test: api/tests/unit/infrastructure/test_outbound_target_guard.py::test_outbound_target_guard_surfaces_persistent_resolver_error_as_unsafe

### Requirement: Effective port defaults by scheme

When validating a URL, the guard SHALL use the explicit port when it is non-zero, and
otherwise 443 for `https` and 80 for `http`. When validating a bare host without a port,
it SHALL use 443. The effective port is used for resolution and returned in the
resolution.

Source: api/app/infrastructure/external_services/outbound_target_guard.py:resolve_safe_outbound_url, resolve_safe_outbound_host

#### Scenario: http URL without a port uses port 80

- **WHEN** the guard validates `http://example.org/`
- **THEN** the returned resolution has `port=80`

Test: NONE

#### Scenario: Bare host without a port uses port 443

- **WHEN** `resolve_safe_outbound_host("example.org")` is called without a port
- **THEN** resolution is performed at port 443 and the returned resolution has `port=443`

Test: NONE

### Requirement: Connections are pinned to validated addresses

Adapters that fetch the verification target SHALL connect only to the IP addresses
returned by the guard. They MUST NOT re-resolve the hostname between validation and
connection. The original hostname SHALL still be used for the HTTP `Host` header and for
TLS SNI and certificate verification. Validated addresses are tried in order, and the next
one is used after a network-level failure.

Source: api/app/infrastructure/external_services/pinned_http_client.py:send_pinned_get_request, _PinnedHTTPConnection.connect, _PinnedHTTPSConnection.connect; api/app/infrastructure/external_services/tls/tls_client.py:SocketTlsValidator.validate_hostname; api/app/infrastructure/external_services/dns/socket_infrastructure_lookup.py:SocketInfrastructureLookup.lookup

#### Scenario: HTTP fetch connects to the validated IP

- **WHEN** `send_pinned_get_request("https://example.org/login?next=/mail", ...)` runs and the guard validated `203.0.113.10`
- **THEN** the connection is built for host `example.org`, port 443, destination IP `203.0.113.10`
- **AND** the request is `GET /login?next=/mail`

Test: api/tests/unit/infrastructure/test_pinned_http_client.py::test_pinned_http_client_uses_validated_ip_for_actual_connection

#### Scenario: TLS validation connects to the validated IP with the hostname as SNI

- **WHEN** `SocketTlsValidator.validate_hostname("safe.example", 443)` runs and the guard validated `203.0.113.10`
- **THEN** the socket connects to `("203.0.113.10", 443)`
- **AND** the TLS handshake uses `server_hostname="safe.example"`

Test: api/tests/unit/infrastructure/test_network_adapter_pinning.py::test_tls_validator_connects_to_validated_ip_not_hostname

#### Scenario: Infrastructure lookup does not re-resolve

- **WHEN** `SocketInfrastructureLookup.lookup` runs
- **THEN** it uses the addresses returned by the guard and does not call `getaddrinfo` again (only reverse lookups on those IPs)

Test: api/tests/unit/infrastructure/test_network_adapter_pinning.py::test_infrastructure_lookup_reuses_validated_addresses_without_second_resolution

#### Scenario: Next validated address is tried after a network failure

- **WHEN** the connection to the first validated IP fails with a network or TLS error
- **THEN** the pinned client tries the next validated IP, and re-raises the last error if all fail

Test: NONE

### Requirement: Redirects are followed manually and every hop is re-validated

The pinned HTTP client SHALL NOT follow redirects on its own. The redirect resolver SHALL
follow only status codes 301, 302, 303, 307 and 308, for at most 5 requests. It SHALL
resolve each `Location` against the current URL and validate it with the guard before
recording the hop. A blocked hop MUST abort the entire resolution with
`RedirectResolutionError`.

Source: api/app/infrastructure/external_services/redirects/http_redirect_resolver.py:HttpRedirectResolver.resolve; api/app/infrastructure/external_services/pinned_http_client.py:send_pinned_get_request

#### Scenario: Redirect to a blocked destination aborts resolution

- **WHEN** `https://safe.example/start` responds `302` with a `Location` that the guard rejects
- **THEN** the resolver raises `RedirectResolutionError`
- **AND** no request is sent to the blocked location

Test: api/tests/unit/infrastructure/test_network_adapter_pinning.py::test_redirect_resolver_revalidates_each_redirect_hop

#### Scenario: Redirect chain longer than the hop limit fails

- **WHEN** every response in the chain is a redirect and 5 requests have been made
- **THEN** the resolver raises `RedirectResolutionError` ("Redirect chain exceeded the configured hop limit.")

Test: NONE

#### Scenario: Redirect without Location fails

- **WHEN** a redirect status is returned without a `Location` header
- **THEN** the resolver raises `RedirectResolutionError`

Test: NONE

### Requirement: Outbound fetches are bounded by timeouts and body size

The pinned HTTP client SHALL apply the caller's timeout to socket connect and read
operations. When a byte limit is given, it SHALL read at most that many body bytes. With
code defaults, the HTML fetcher uses a 3-second timeout and a 200,000-byte limit; the
redirect resolver uses a 3-second timeout and does not read response bodies; the TLS
validator uses a 3-second connect timeout.

Source: api/app/infrastructure/external_services/pinned_http_client.py:send_pinned_get_request; api/app/infrastructure/external_services/html/simple_html_fetcher.py:SimpleHtmlFetcher; api/app/infrastructure/external_services/redirects/http_redirect_resolver.py:HttpRedirectResolver; api/app/infrastructure/external_services/tls/tls_client.py:SocketTlsValidator

#### Scenario: HTML body is truncated to the byte limit

- **WHEN** a page larger than 200,000 bytes is fetched by `SimpleHtmlFetcher` with defaults
- **THEN** only the first 200,000 bytes are read and decoded

Test: NONE

#### Scenario: Redirect resolution does not download bodies

- **WHEN** the redirect resolver issues a request
- **THEN** it calls the pinned client with `read_body=False`

Test: api/tests/unit/infrastructure/test_network_adapter_pinning.py::test_redirect_resolver_revalidates_each_redirect_hop

### Requirement: Verification targets are validated before any analysis

The verification use case SHALL validate the normalized target URL with the guard before
running any analysis, including the URL-only fast path and headless detonation. A rejected
target MUST abort the verification with a `DomainException`, which the API returns as HTTP
422 with a localized (EN/ES) message. No verification or analysis trace is persisted. On
the async scan path, the job SHALL be marked failed with the rejection message.

Source: api/app/application/use_cases/create_url_verification.py:CreateURLVerificationUseCase.execute, _assert_public_target; api/app/entrypoints/api/main.py:handle_domain_exception; api/app/application/services/verification_scan_processor.py:VerificationScanProcessor.process; api/app/entrypoints/api/dependencies/container.py:get_create_url_verification_use_case

#### Scenario: Local target is rejected at the use case

- **WHEN** a verification is requested for `https://localhost/login` with the real guard wired in
- **THEN** the use case raises `DomainException("Outbound target is a local or special-use hostname and was blocked.")`

Test: api/tests/unit/application/test_create_url_verification_use_case.py::test_create_url_verification_use_case_rejects_unsafe_local_targets

#### Scenario: API returns a localized 422

- **WHEN** `POST /api/verifications` is called with `https://localhost/login` and `Accept-Language: es`
- **THEN** the response is 422 with the Spanish message for `error.outbound_target_local_special_use_blocked`

Test: api/tests/integration/test_verifications_api.py::test_verification_api_rejects_unsafe_local_targets (uses a stub validator, not the real guard)

#### Scenario: Async scan with a rejected target is marked failed

- **WHEN** the scan processor runs a job whose target the guard rejects
- **THEN** the job is marked failed with the guard's message as its error

Test: api/tests/unit/application/test_verification_scan_use_cases.py::test_processor_marks_failed_on_domain_exception (generic DomainException, not guard-specific)

### Requirement: Guard rejections inside analysis stages degrade to coverage warnings

When the guard rejects a destination inside a network analysis stage (for example a
redirect hop or the resolved destination), the adapter SHALL convert the rejection into its
port-level error. The stage SHALL then record a coverage warning in its analysis-trace
entry instead of failing the verification. The warnings are:
`warning.redirect_resolution_unavailable` (redirects),
`warning.tls_validation_unavailable` (TLS), `warning.infrastructure_unavailable`
(DNS/infrastructure), `warning.html_fetch_blocked_private_target` (resolved-destination
HTML) and `warning.html_content_inspection_unavailable` (primary HTML, when every
user-agent variant fails). Only the resolved-destination HTML warning identifies the
guard as the cause.

Source: api/app/infrastructure/external_services/html/simple_html_fetcher.py:SimpleHtmlFetcher.fetch; api/app/infrastructure/external_services/tls/tls_client.py:SocketTlsValidator.validate_hostname; api/app/infrastructure/external_services/dns/socket_infrastructure_lookup.py:SocketInfrastructureLookup.lookup; api/app/infrastructure/external_services/redirects/http_redirect_resolver.py:HttpRedirectResolver.resolve; api/app/application/services/redirect_signal_analyzer.py; api/app/application/services/transport_security_signal_analyzer.py; api/app/application/services/infrastructure_signal_analyzer.py; api/app/application/services/resolved_destination_signal_analyzer.py; api/app/application/use_cases/create_url_verification.py:_analyze_html_content, _run_network_analysis

#### Scenario: Blocked redirect hop becomes a redirect coverage warning

- **WHEN** redirect resolution fails because a hop was rejected by the guard
- **THEN** the `redirect_resolution` trace stage carries `warning.redirect_resolution_unavailable` and no redirect hops are reported

Test: api/tests/unit/application/test_redirect_signal_analyzer.py::test_redirect_signal_analyzer_records_warning_when_resolution_fails (generic resolution error, not guard-specific)

#### Scenario: Blocked resolved-destination fetch is identified as a private-target block

- **WHEN** the HTML fetch of the resolved destination is rejected by the guard
- **THEN** `SimpleHtmlFetcher` raises `HtmlFetchError("HTML content fetch was blocked for a private or special-use target.")`
- **AND** the `resolved_destination` trace stage carries `warning.html_fetch_blocked_private_target`

Test: NONE

#### Scenario: Blocked TLS or infrastructure lookup becomes a generic coverage warning

- **WHEN** the guard rejects the host during TLS validation or infrastructure lookup
- **THEN** the corresponding trace stage carries `warning.tls_validation_unavailable` or `warning.infrastructure_unavailable`

Test: NONE

### Requirement: Webhook destinations are validated before delivery

The scan webhook notifier SHALL validate the job's webhook URL with the guard once per
notification, before the first delivery attempt. A rejected destination MUST NOT be
contacted. The notifier SHALL log a warning
that names the scan id (not the URL) and SHALL NOT retry. At submission time, the API
SHALL accept a webhook URL only if its scheme is `http` or `https`.

Source: api/app/infrastructure/webhooks/http_scan_webhook_notifier.py:HttpScanWebhookNotifier.notify; api/app/entrypoints/api/dependencies/container.py:get_scan_webhook_notifier; api/app/entrypoints/api/schemas/scan_schema.py:_validate_webhook_url

#### Scenario: Unsafe webhook destination is skipped

- **WHEN** a scan reaches a terminal state and the guard rejects its webhook URL
- **THEN** the HTTP poster is never called

Test: api/tests/unit/infrastructure/test_http_scan_webhook_notifier.py::test_unsafe_destination_is_not_delivered

#### Scenario: Non-HTTP webhook URL is rejected at submission

- **WHEN** `POST /api/v1/scans` is called with `webhook_url` set to `ftp://not-http.example`
- **THEN** the response is 422

Test: api/tests/integration/test_scans_api.py::test_submit_rejects_invalid_webhook_url
