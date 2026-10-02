# Proposal

## Why

The login transition is stable above 1120px, but not on narrower screens. CLS on session
restore was measured on `main` with a production build, the API stubbed, `/api/me` delayed
600ms and quota delayed 1.8s:

- **721–1120px** (the sidebar collapses into a top bar and the topbar stays visible): CLS
  **0.074** at 1000px and **0.088** at 800px. The topbar account block widens when the
  placeholder is replaced (361→574px at 1000px). When the quota arrives it widens again,
  and it also gets **taller** (115→150px at 1000px, 115→184px at 800px), because the
  quota lines wrap in the narrow text column. The content below moves 35–69px.
- **≤720px** (mobile; the topbar is hidden): CLS **0.136** at 390px. The compact session
  card in the sidebar (`.sidebar-account`, 129px) appears only once the session is
  validated and pushes the page down 64px.

## What Changes

- 721–1120px: while a session is present or being restored, the topbar account block
  SHALL keep the same width and height across placeholder, loading quota and loaded quota.
  The text column gets a width that depends on the viewport, not on the text. Name and
  email stay on one line (ellipsis), and the quota title and note keep a fixed number of
  lines (longer text is truncated with an ellipsis). Placeholder action pills carry the
  real button labels (invisible), so their widths match exactly.
- ≤720px: while a saved session is being restored, the sidebar SHALL show a placeholder
  with the same size as the compact session card (name + two actions), analogous to the
  topbar's restore placeholder. The name stays on one line (ellipsis), so the card height
  does not depend on the name.
- Anonymous visitors (no saved session) see no change at any width.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `login-topbar-stability`: ADDED requirements for 721–1120px (topbar account block size)
  and ≤720px (mobile session card placeholder). Existing requirements are unchanged. The
  capability's Purpose ("topbar's account area") should be widened at archive time to
  cover the mobile session card. That is a direct edit of the main spec's Purpose, as the
  workflow requires.

## Impact

- Code: `web/src/layouts/Topbar.tsx`, `web/src/layouts/Sidebar.tsx`, `web/src/styles/layout.css`.
  A small shared helper may be extracted for the stored-session read used by both
  placeholders. No changes to `auth.tsx`, the API or the backend.
- Visible changes for signed-in users at ≤1120px: very long names/emails and quota texts
  that exceed the reserved lines are truncated with an ellipsis.
- Found during apply and included:
  - The 26rem desktop column could overlap the avatar between 1121px and ~1440px (a #90
    regression); fixed with content-sized grid tracks.
  - The stacked sidebar stretched on short pages (≤1120px). That was the cause of an
    intermittent anonymous EN shift at 390px; the anonymous EN sidebar now measures 70px,
    like ES.
  - The deep analysis hint uses the signed-in text during session restore.
  - The account block no longer shows a stale anonymous quota after an in-app login.
- `web/src/components/analysis/AnalyzeUrlForm.tsx` is also touched (hint text only).
- The acceptance measurement still excludes shifts that also occur in the anonymous run
  at the same viewport and language (page-content shifts unrelated to login).
