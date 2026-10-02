# Design

## Context

See proposal.md (Why). Relevant current state:

- `Topbar.tsx` renders `.topbar-account` when `currentUser` is set and `.topbar-auth`
  otherwise. Quota lines render only when `quotaReady && quotaStatus`.
- `AuthProvider` sets `currentUser` only after `GET /api/me` validates the saved session.
  Until then, `authReady` is false and the topbar shows the sign-in actions.
- `quotaReady` is a one-shot flag: it is set true after the first quota fetch and never
  resets. The skeleton condition is therefore `currentUser && !quotaReady`, not
  `!quotaSummary`, which would leave a skeleton stuck after a failed fetch.
- Measured on `main` (production build, API stubbed, Google script stubbed), desktop >1120px:
  sign-in actions 120px, account block without quota 171px, with quota 224px. On session
  restore, CLS was 0.169, made of two shifts.
- `Topbar` is never server-rendered (the SSR prerender covers only the landing page), but
  storage reads are still guarded.

## Goals / Non-Goals

**Goals:**

- Zero topbar-caused shift on session restore and on late quota at desktop widths.
- No change to the anonymous header height.

**Non-Goals:**

- Sidebar account block at ≤1120px.
- Resetting the quota on login/logout (`auth.tsx`).
- The user-initiated swap during an in-app login.
- Any change to the Google button's reserved size.

## Decisions

1. **The skeleton reuses the real line classes.** Each placeholder `<p>` keeps
   `topbar-account__quota` / `topbar-account__quota-note`, adds
   `topbar-account__quota--skeleton`, and contains a non-breaking space. It therefore
   inherits the exact font size and line height (0.8rem / 0.78rem), so the reserved height
   matches the real lines by construction rather than through hard-coded pixel heights.
   The skeleton bar is a `background` of fixed width (~9rem / ~7rem) clipped to the text
   line, with `color: transparent` and `aria-hidden="true"`. *Alternative considered:*
   a fixed `min-height` on the copy column. Rejected because it would have to be
   recalibrated per breakpoint.
2. **A failed quota renders the same placeholders without the skeleton class modifier**
   (`topbar-account__quota--reserved`): space is kept and nothing is shown. This covers
   the "Failed quota" requirement.
3. **Restore-aware placeholder instead of a uniform `min-height`.** While `!authReady` and a
   stored session exists (read through `readStoredAuthSession()`, guarded with try/catch),
   `Topbar` renders the account block structure in skeleton form. It includes the avatar
   circle, the text lines with skeletons, and the action buttons as inert skeleton pills
   with the same `button` box. The number of pills follows the stored user's plan: 3 for
   FREE (history, upgrade, sign out), otherwise 2. That way the placeholder is the same
   size as the block that replaces it. *Alternatives considered:* a uniform
   `min-height: ~224px` on `.topbar__actions`, rejected because it adds ~104px of empty
   header for every anonymous visitor; and rendering the account block optimistically
   from stored user data before validation, rejected because it would show identity data
   that may be invalid and flash on a rejected session.
4. **Opacity-only fade.** A ~160ms `@keyframes` from `opacity: 0` on `.topbar-account` and
   `.topbar-auth` mount, disabled under `prefers-reduced-motion: reduce`. Opacity does not
   trigger layout, so it cannot add CLS.
5. **Language switcher on its own row when there is a session.** Found during apply: the
   second shift is horizontal, not vertical. The real quota note widens the account block
   (349px → 567px in EN, 612px in ES, at 1366px), and `.topbar__actions` (`flex-wrap: wrap`)
   then wraps the EN/ES switcher onto a new row (+53px). A height-only skeleton cannot
   reserve a text-dependent width. When the placeholder or the account block is shown,
   `.topbar__actions` gets a modifier that stacks the switcher under the account area
   (column, end-aligned). The height is then constant (account 171px + gap + switcher)
   whatever the text. At 1366px this matches the final layout `main` already shows.
   *Alternatives considered:* a non-wrapping single row, rejected because it overflows or
   crushes the title between ~1121–1280px; capping the quota width with a 2-line skeleton,
   rejected because the line count depends on language, plan and blocked state.
6. **Fixed-width account text column above 1120px.** Also found during apply. Once the
   switcher was stacked, a residual horizontal shift remained (CLS 0.018 at 1366px). The
   text column grew from ~145px to 362–410px when the quota arrived, and since the block is
   right-aligned, the avatar moved ~218px left. Above 1120px, `.topbar-account__copy` gets
   a fixed width of 26rem, enough for the longest quota note (73 characters); text wraps
   if it ever exceeds it. The block width is then constant across placeholder, skeleton
   and loaded states. *Alternatives considered:* accepting 0.018, rejected per the < 0.01
   target; moving the avatar next to the buttons, rejected as a larger visual change.
7. **Verification harness.** Playwright runs against a production build. It stubs the Google
   script and the API, with configurable delays for `/api/me` and `/quota-status`, and
   records `layout-shift` entries with a `PerformanceObserver`. Scenarios: anonymous, and
   restore with delayed `/api/me` and quota, at 1366px. The 1000px numbers are reported
   for information only (non-goal). The harness lives outside the repo, in the session
   scratchpad, like the flicker verification.

## Risks / Trade-offs

- [Placeholder height drifts from the real block if the account markup changes later] →
  The placeholder reuses the same container and line classes. The restore scenario in the
  harness catches a regression as CLS > 0.
- [Invalid saved session] → One swap from placeholder to sign-in actions. This is rare
  (expired token) and accepted per spec.
- [Plan changes between the stored session and `/api/me`, for example FREE→PRO] → Pill
  count differs by one. On desktop the copy column (224px) dominates the actions column, so
  the height is unaffected there. Accepted.
- [On very wide screens, where the switcher used to fit beside the account block, it now
  sits below it] → A minor, consistent visual change for signed-in users only; the
  anonymous header is unchanged.
- [Short names or emails leave empty space inside the fixed 26rem column] → With the quota
  loaded, the column is already 362–410px today, so the final look barely changes (the
  avatar sits ~50px further left in EN).
- [Skeleton visible for a long time on a slow quota request] → Neutral, low-contrast bar
  with no shimmer animation, so it does not distract.

## Migration Plan

Frontend-only and CSS/JSX-only. No flags or migrations. Rollback is a revert of the commit.
