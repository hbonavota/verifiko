# QA process

The Verifiko web app is tested by hand in a real browser before and after each change, and the
findings are written up and handed to the implementation step with reproduction notes. This document
describes how that testing is run; it is not a bug tracker.

## Scope

- **Surfaces:** the public landing, the anonymous verification flow, and the authenticated app (deep
  analysis with screenshot, history, and the verification detail view).
- **Viewports:** desktop (1440px) and emulated mobile (360 / 375 / 390px).
- **Languages:** English and Spanish, exercised both by switching language at runtime and by loading
  with the language preselected.
- **Sessions:** anonymous (quota-limited) and authenticated via magic link.

## What each round checks

- **Functionality:** URL validation and error states, quota accounting, result rendering (trust score,
  verdict copy, evidence), and the paths for unreachable or failed analyses.
- **Console and network:** no React hydration errors on load, no unexpected console errors, and no
  redundant API calls (for example, switching language must not re-request `/health`).
- **Rendering stability:** no layout shift or flicker on the auth and quota transitions, and no overflow
  or clipping at mobile widths.
- **Accessibility:** the accessibility tree is inspected for landmarks, control labels, and keyboard
  reachability of the primary navigation.
- **Internationalization:** copy is complete and consistent in both languages, including the document
  title and meta tags.
- **PWA:** the manifest, service worker, cache strategy, update notice, install affordance, and offline
  behavior.

## Method

Testing is done in a real browser with the console, the Performance and Network APIs, and the
accessibility tree open, using JavaScript to set up state (language, consent), to inspect the service
worker, manifest and caches, and to simulate network failures and rate limiting. Each round starts from
a clean state — service worker, caches and storage cleared — and confirms the exact build under test.

## Regression

Findings from one round are re-verified in the next against the deployed build, so that fixes are
confirmed on the same surface where the issue appeared and nothing silently regresses.
