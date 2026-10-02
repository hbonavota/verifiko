# Tasks

## 1. Quota line skeleton (Topbar + CSS)

- [x] 1.1 In `Topbar.tsx`, when `currentUser && !quotaReady` render two `aria-hidden` placeholder `<p>`s (`topbar-account__quota topbar-account__quota--skeleton`, `topbar-account__quota-note topbar-account__quota--skeleton`, each holding `&nbsp;`); when `quotaReady && !quotaStatus` render the same with `--reserved` instead of `--skeleton`; verify with `npm run build` (tsc passes)
- [x] 1.2 In `layout.css`, style `--skeleton` (transparent text, low-contrast background bar ~9rem / ~7rem, rounded, justify-self end) and `--reserved` (transparent, no background); verify in the harness that the account block height is identical before and after the delayed quota arrives (restore scenario, 1366px)

## 2. Session-restore placeholder

- [x] 2.1 In `Topbar.tsx`, while `!authReady` and a stored session exists (guarded read), render an account-shaped placeholder (avatar circle, skeleton text lines incl. quota skeletons, 3 skeleton pills for FREE / 2 otherwise, all `aria-hidden`) instead of the sign-in actions; verify with `npm run build`
- [x] 2.2 In `layout.css`, add the avatar and pill skeleton styles reusing the `button` box so pills match real button height; verify in the harness that on restore the sign-in actions never render and topbar CLS < 0.01 at 1366px
- [x] 2.4 Stack the language switcher under the account area whenever the placeholder or the account block is shown (`.topbar__actions` modifier, column, end-aligned); verify in the harness that the switcher's position and the topbar height do not change when the quota arrives, in EN and ES at 1366px
- [x] 2.5 Give `.topbar-account__copy` a fixed 26rem width above 1120px; verify in the harness that the account block width and avatar position do not change when the quota arrives (EN and ES, FREE and PRO, 1366px), and that the topbar still fits at 1180px
- [x] 2.3 Verify the anonymous scenario in the harness: no placeholder, sign-in actions on first render, `.topbar__actions` height unchanged vs `main` (120px at 1366px)

## 3. Opacity-only swap

- [x] 3.1 Add a short opacity `@keyframes` fade on `.topbar-account` / `.topbar-auth` mount, disabled under `prefers-reduced-motion: reduce`; verify the harness CLS numbers are unchanged and that no `layout-shift` entry comes from the fade

## 4. Integration checks

- [x] 4.1 `cd web && npm run build` green
- [x] 4.2 Run the Playwright CLS harness on the production build for `main` and this branch (anon + restore, 1366px; 1000px informational) and record the before/after table in the PR description
