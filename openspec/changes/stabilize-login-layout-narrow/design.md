# Design

## Context

See proposal.md (Why) for the measured shifts. Relevant current state:

- Above 1120px, `.topbar-account__copy` has a fixed 26rem width, the restore placeholder
  (`PendingAccountPlaceholder`, gated by `readPendingSessionPlan()` while `!authReady`)
  mirrors the block, and `QuotaLinePlaceholders` reserves the quota lines. None of the
  width rules apply at ≤1120px.
- At ≤1120px, `.topbar-account__actions` switches to a wrapping row. The account block's
  width (and with it the actions' wrapping and the quota lines' wrapping) therefore
  depends on the text, and the placeholder's skeleton pills are narrower than the real
  labelled buttons.
- `.sidebar-account` is `display: none` except at ≤720px, where it becomes a compact card:
  avatar, eyebrow and name (label and email hidden), and two actions in a 2-column grid.
  It renders only when `currentUser` is set, so it appears late on restore.
- `Topbar` and `Sidebar` are never server-rendered.

## Goals / Non-Goals

**Goals:**

- Zero login-caused shift at 721–1120px and ≤720px on session restore.
- No change to the anonymous layout at any width.

**Non-Goals:**

- The single swap after the Google popup (unchanged non-goal from the previous change).
  The stale anonymous quota is now handled; see Decision 5.
- Other layout changes above 1120px. The exceptions apply at every width: the placeholder's
  real-label pills (Decision 3), the anonymous-quota rule (Decision 5) and the
  overlap fix (Decision 6).

## Decisions

1. **The tablet column width depends on the viewport, not on the text.** At 721–1120px,
   `.topbar-account__copy` gets `width: clamp(<min>, <vw>, <max>)`, calibrated during
   apply so the block plus the title fit at 721px and 1120px. Because it depends only on
   the viewport, the width is identical in every state. *Alternative considered:* reusing
   the desktop 26rem, rejected because it does not fit beside the title at 721px. The user
   also asked for a narrower reservation.
2. **Lines are bounded.** In the same range, the name and email lines get
   `white-space: nowrap; overflow: hidden; text-overflow: ellipsis`. The quota title and
   note get a fixed line count (`-webkit-line-clamp` plus a `min-height` of the same
   number of line-heights; 2 lines each, confirmed during apply against the longest EN/ES
   strings at the narrowest column width). `QuotaLinePlaceholders` is reused unchanged:
   its `<p>`s carry the same classes, so they reserve the same lines.
3. **Placeholder pills carry the real labels.** `PendingAccountPlaceholder` renders the
   actual action labels (`copy.topbar.reviewHistory`, upgrade label, `signOut`) with
   transparent text, so the pills are exactly as wide as the real buttons and the
   actions wrap identically. This also tightens the desktop placeholder.
4. **The mobile placeholder is a restore-aware `PendingSessionCard` in `Sidebar.tsx`.**
   While `!authReady && !currentUser` and a stored session exists, `Sidebar` renders a
   `.sidebar-account .sidebar-account--pending` section with the same markup:
   avatar skeleton, eyebrow and name skeleton lines, and hidden label/meta lines (they
   are `display: none` at ≤720px anyway). It has two pills with the real labels: a
   `<span>` for the link and a `<button>` for sign-out, matching the element types
   because native buttons do not inherit font size. It is `aria-hidden`. The name line
   gets `nowrap` + ellipsis at ≤720px, so the card height does not depend on the name.
5. **No anonymous quota inside the account block.** Found while verifying the truncation
   (task 3.2). At the narrowest column, 23 of 24 quota strings fit in 2 lines, but
   `es.anonymousDetail` (95 characters) needs 3. Anonymous strings reach the account block
   only through the stale quota left over from before an in-app login. `Topbar` therefore
   treats `quotaStatus.plan === "ANONYMOUS"` with a signed-in user as not loaded: skeleton
   until `refreshQuotaStatus` (triggered by `AppLayout` on the user change) brings the
   user's quota. This needs no `auth.tsx` change, and it also removes the stale-quota
   flash, previously a non-goal, at every width. *Alternatives considered:* reserving 3
   lines (adds ~17px for every signed-in user at 721–1120px), widening the column (does
   not fit beside the title at 721px), and shortening the ES copy (changes what anonymous
   users see elsewhere).
6. **Content-sized grid tracks from 721px up (fixes a #90 regression).** Found during
   apply with a new overlap check in the harness. The fixed-width text column (26rem above
   1120px from #90; the clamp width here) sits in a `minmax(0, 1fr)` track that can shrink
   below it. On `main`, the text overlaps the avatar for signed-in users from 1121px to
   ~1365px (EN) and up to ~1440px (ES). From 721px up, `.topbar-account` uses
   `auto auto auto` tracks, and at 721–1120px the actions keep `min-width: auto`. That
   overrides the existing `max-width: 1120px` `min-width: 0`, which needs extra specificity
   because it comes later in the file. `.topbar__actions--account` is also set to
   `flex-wrap: nowrap`. The block's minimum width is then honored, and the topbar title
   absorbs the squeeze: ~140px wide and 2–3 lines at 1121px, still shorter than the
   account column. Verified with no overlaps from 721px to 1920px in EN/ES.
7. **Content-sized sidebar row at ≤1120px.** Found during apply (task 4.2). `.app-layout`
   has `min-height: 100vh`, and at ≤1120px it stacks the sidebar and the content in two
   `auto` rows. When the content is shorter than the viewport (before the lazy page
   renders, or permanently on short pages), the free space was spread over both rows, so
   the sidebar stretched and later snapped back. That caused the intermittent anonymous
   EN shift at 390px and a 5px sidebar shift on restore. `grid-template-rows: auto 1fr`
   keeps the sidebar row content-sized. Visible effect: the anonymous EN sidebar at 390px
   is 70px (it was a stretched 96px), as it already was in ES.
8. **Deep analysis hint during restore.** Also found in task 4.2. With the sidebar stable,
   the remaining 390px restore shift (EN 0.0105) came from `AnalyzeUrlForm`'s deep
   analysis hint switching from the sign-in text (2 lines) to the signed-in text
   (5 lines). The hint text now uses `isAuthenticated || hasPendingSession`, via the
   shared helper. The toggle's `onChange` still uses `isAuthenticated`, so behavior is
   unchanged.
9. **Shared stored-session read.** `readPendingSessionPlan()` moves to a small shared
   helper (for example, in `lib/authSessionStorage.ts`) so `Topbar` and `Sidebar` use the
   same guarded read.
10. **Verification harness.** This reuses the Playwright CLS harness from the previous
   change (production build, Google script and API stubbed, `/api/me` +600ms, quota
   +1.8s, `layout-shift` observer with per-source rects). Cases: restore and anonymous,
   at 1000/800/390px, in EN and ES, with an extra 721px and 1120px fit check. The
   acceptance CLS excludes shifts that also occur in the anonymous run at the same
   viewport and language. It runs against `main` and the branch for a before/after table.

## Risks / Trade-offs

- [Truncation hides part of a very long name, email or quota text at ≤1120px] → Current
  strings fit in the reserved lines (verified during apply). Truncation is a safety net
  for user data, and the full email remains visible on the dashboard.
- [The tablet column width leaves empty space for short text] → The text is right-aligned,
  as on desktop, so the effect matches the desktop look.
- [Plan differs between the stored session and `/api/me`] → The pill count can differ by
  one. At ≤720px both plans show 2 actions in the sidebar, so it is unaffected. In the
  tablet topbar the actions wrap row may differ; accepted as rare.
- [The stacked sidebar row no longer stretches on short pages] → Matches the existing
  Spanish layout. The only visible difference is the anonymous EN sidebar at 390px
  (96px → 70px), which removes an intermittent shift.

## Migration Plan

Frontend-only (JSX/CSS). No flags or migrations. Rollback is a revert of the commit.

## Open Questions

- Exact clamp bounds and line counts are calibrated during apply. This does not change
  the approach or the tasks.
