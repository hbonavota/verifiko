# Tasks

## 1. Baseline

- [x] 1.1 Run the CLS harness on a `main` production build (restore + anonymous; 1000/800/390px; EN and ES) and save the numbers for the before/after table; verify the results are reproducible across two runs

## 2. Shared helper and placeholder pills

- [x] 2.1 Move `readPendingSessionPlan()` to a shared guarded helper used by `Topbar.tsx`; verify `npm run build` passes and the desktop restore CLS at 1366px is still 0
- [x] 2.2 Render the real action labels (transparent) in `PendingAccountPlaceholder` pills; verify in the harness that at 1000px the placeholder and account block have identical width

## 3. Tablet topbar (721–1120px)

- [x] 3.1 Add the viewport-based `clamp()` width for `.topbar-account__copy` at 721–1120px, single-line ellipsis for name/email, and fixed line counts for the quota title/note; verify in the harness that the block width/height is constant across placeholder → account → quota at 1000px and 800px in EN and ES, and that block + title fit at 721px and 1120px
- [x] 3.2 Verify every quota title/note string (EN/ES, all plans and blocked states) fits within the reserved lines at the narrowest column width, by measuring rendered line counts in the harness

- [x] 3.3 In `Topbar.tsx`, treat a signed-in user's `ANONYMOUS` quota as not loaded (skeleton) instead of rendering it; verify in the harness with an in-app-login simulation (stale anonymous quota, delayed user quota) that the anonymous text never appears in the account block and the block size does not change, and re-run the 3.2 line-count check over the strings the account block can now show

- [x] 3.4 Use content-sized (`auto`) grid tracks for `.topbar-account` from 721px up, keep the actions' `min-width: auto` at 721–1120px, and set `flex-wrap: nowrap` on `.topbar__actions--account`; verify with the harness overlap check that avatar, text, actions and title never overlap from 721px to 1920px in EN/ES, with no horizontal overflow and restore CLS unchanged

## 4. Mobile session card (≤720px)

- [x] 4.1 Add a restore-aware `PendingSessionCard` placeholder in `Sidebar.tsx` (same markup, real-label pills with matching element types, `aria-hidden`) plus the `nowrap`/ellipsis name rule at ≤720px; verify `npm run build` passes
- [x] 4.3 Set `grid-template-rows: auto 1fr` on `.app-layout` at ≤1120px; verify at 390px that the sidebar height is identical before and after the page content renders (EN/ES, anonymous and restore), and that the anonymous EN sidebar equals the ES height
- [x] 4.4 In `AnalyzeUrlForm.tsx`, use the signed-in deep analysis hint while a saved session is being validated (text only; `onChange` unchanged); verify at 390px EN/ES restore that the deep toggle does not move, and that the anonymous hint is unchanged
- [x] 4.2 Verify in the harness at 390px: restore CLS (excluding shifts also present in the anonymous run) < 0.01 in EN and ES; invalid session removes the placeholder; anonymous sidebar height unchanged vs `main`

## 5. Integration checks

- [x] 5.1 `cd web && npm run build` green
- [x] 5.2 `cd api && python -m pytest -q` and `python -m evaluation.run_evaluation` green (repo convention; no backend change), with no precision regression
- [x] 5.3 Run the full harness on `main` vs the branch and record the before/after table in the PR description
