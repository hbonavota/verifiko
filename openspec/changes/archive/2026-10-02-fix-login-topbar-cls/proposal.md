# Proposal

## Why

When a signed-in user opens the app, the desktop topbar moves the page content down twice
(cumulative layout shift). First, the topbar renders the sign-in actions (120px tall) while
the saved session is being validated, then swaps them for the taller account block
(171px). Second, the two quota lines appear once the quota request returns, and the
block grows to 224px. In a production build with the API stubbed, CLS on session
restore measured 0.169 at 1366px with two shifts. Goal: CLS ≈ 0 for this transition
without making the header taller for anonymous visitors.

## What Changes

- While the quota for a signed-in user is still loading, the topbar SHALL keep the space of
  the two quota lines with a neutral skeleton, so the account block does not grow when the
  quota arrives. If the quota request fails, the space stays reserved and empty, with no
  skeleton left showing.
- While a saved session is being validated on load, the topbar SHALL show an account-sized
  placeholder instead of the sign-in actions. The page then does not move when the account
  block replaces it. Anonymous visitors (no saved session) see the sign-in actions
  immediately, at the same height as today.
- Swaps between topbar states fade in using opacity only (no layout animation) and honor
  `prefers-reduced-motion`.
- The reserved Google button size (`min-height: 40px`, `min-width: 200px`) is kept as is.

## Capabilities

### New Capabilities

- `login-topbar-stability`: layout stability of the app topbar's account area across the
  signed-out ↔ signed-in transition, including session restore and late quota data.

### Modified Capabilities

(none)

## Impact

- Code: `web/src/layouts/Topbar.tsx`, `web/src/styles/layout.css`. No changes to
  `web/src/lib/auth.tsx`, the API or the backend.
- Behavior: no change for anonymous visitors (same header height). Signed-in users with a
  saved session see a short placeholder instead of a flash of the sign-in buttons.
- Out of scope (non-goals, possible follow-ups):
  - The sidebar account block at ≤1120px, where the sidebar becomes a top bar. It produces
    its own shift; at 1000px, CLS measured 0.298 on `main`, partly from the sidebar.
  - The stale anonymous quota shown briefly during an in-app login. That needs a quota
    reset in `auth.tsx`.
  - The single, user-initiated swap during an in-app login, after the Google popup or the
    email modal.
