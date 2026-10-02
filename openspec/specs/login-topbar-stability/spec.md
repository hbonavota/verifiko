# login-topbar-stability Specification

## Purpose

Keeps the app's account areas visually stable while authentication and quota state load:
the topbar account block on desktop and tablet, and the sidebar session card on phones.
Signing in or restoring a session then does not push the page content around
(cumulative layout shift) at any viewport width.

## Requirements

### Requirement: Quota lines keep their space while the quota loads

While a user is signed in and their quota has not loaded yet, the topbar account block
SHALL reserve the space of the two quota lines with a neutral skeleton. When the quota
arrives, the real lines SHALL replace the skeleton without changing the block's height.

#### Scenario: Quota arrives after the account block is shown

- **WHEN** a signed-in user's account block is rendered and the quota request is still pending
- **THEN** two skeleton lines are shown where the quota title and note go
- **AND** when the quota response arrives, the quota text replaces them and the topbar height does not change
- **AND** at viewports wider than 1120px, the account block's width and the avatar's position do not change either

#### Scenario: Skeleton is hidden from assistive technology

- **WHEN** the quota skeleton is shown
- **THEN** it is not announced by screen readers and contains no visible text

### Requirement: Failed quota keeps the space without a stuck skeleton

If the quota request completes without data (for example, it fails), the topbar SHALL keep
the space of the two quota lines reserved and empty. It MUST NOT keep showing the loading
skeleton.

#### Scenario: Quota request fails

- **WHEN** a signed-in user's quota request fails
- **THEN** the skeleton disappears, the reserved space stays empty, and the topbar height does not change

### Requirement: Session restore shows an account-sized placeholder

While the app validates a saved session on load, the topbar SHALL render a placeholder
that is the same size as the signed-in account block, instead of the sign-in actions. When
validation succeeds, the account block SHALL replace the placeholder without moving the
content below.

#### Scenario: Saved session is restored

- **WHEN** the app loads at a viewport wider than 1120px with a valid saved session, and both the session check and the quota request are delayed
- **THEN** the sign-in actions are never shown
- **AND** the cumulative layout shift attributable to the topbar from load until the quota is shown is below 0.01

#### Scenario: Saved session is invalid

- **WHEN** the app loads with a saved session that the server rejects
- **THEN** the placeholder is replaced by the sign-in actions

### Requirement: Account text width does not move the language switcher

While a user is signed in or a saved session is being restored, the topbar SHALL place the
language switcher on its own row below the account area. A change in the width of the
account text (for example, the quota note arriving, or a different language or plan) then
cannot change the topbar height.

#### Scenario: Long quota note arrives

- **WHEN** a signed-in user's quota note arrives (in English or Spanish), which would otherwise widen the account block
- **THEN** the language switcher stays in the same position and the topbar height does not change

### Requirement: Anonymous topbar is unchanged

When there is no saved session, the topbar SHALL show the sign-in actions on first render,
at the same height as before this change, with no placeholder.

#### Scenario: Anonymous visitor opens the app

- **WHEN** the app loads at a viewport wider than 1120px with no saved session
- **THEN** the sign-in actions are shown immediately and the topbar actions area keeps its previous height (120px in the reference build)

### Requirement: State swaps animate opacity only

Swaps between the sign-in actions, the placeholder and the account block SHALL use at most
a short opacity fade. They MUST NOT animate size or position, and they MUST NOT animate at
all when the user prefers reduced motion.

#### Scenario: Reduced motion

- **WHEN** the user has `prefers-reduced-motion: reduce` and the topbar swaps state
- **THEN** the new state appears without animation

### Requirement: Topbar account block keeps its size between 721px and 1120px

At viewports from 721px to 1120px, while a user is signed in or a saved session is being
restored, the topbar account block SHALL keep the same width and height across the
restore placeholder, the loading-quota state and the loaded-quota state, whatever the
user's name, email, plan or language.

#### Scenario: Session restore at tablet width

- **WHEN** the app loads at 1000px or 800px wide with a valid saved session, and both the session check and the quota request are delayed
- **THEN** the sign-in actions are never shown
- **AND** the account block's width and height do not change from the placeholder until the quota is shown
- **AND** the cumulative layout shift, excluding shifts that also occur for an anonymous visitor at the same viewport and language, is below 0.01

#### Scenario: Parity between English and Spanish

- **WHEN** the same restore happens with the interface in Spanish
- **THEN** the account block's width and height also stay constant

### Requirement: Account text is bounded at narrow widths

At viewports of 1120px or less, the signed-in name and email SHALL each occupy a single
line, and the quota title and note SHALL each occupy a fixed number of lines. Text that
does not fit SHALL be truncated with an ellipsis instead of adding lines.

#### Scenario: Long email

- **WHEN** a signed-in user's email is longer than the account text column at 800px
- **THEN** it is shown on one line, truncated with an ellipsis, and the block height is unchanged

### Requirement: Account text never overlaps the avatar or the actions

At viewports wider than 720px, the topbar account block's text column SHALL NOT overlap the
avatar or the action buttons. When space is short, the topbar title SHALL narrow (wrap)
instead.

#### Scenario: Narrow desktop and tablet widths

- **WHEN** a signed-in user views the app at any width from 721px to 1920px, in English or Spanish
- **THEN** the avatar, the account text and the action buttons do not overlap each other or the topbar title
- **AND** the page has no horizontal overflow

### Requirement: Account block never shows an anonymous quota

While a user is signed in, if the quota on hand belongs to an anonymous visitor (for
example, the stale quota from before an in-app login), the topbar account block SHALL treat
it as not loaded yet. It SHALL show the quota skeleton until the signed-in user's quota
arrives, instead of the anonymous quota text.

#### Scenario: In-app login with a stale anonymous quota

- **WHEN** an anonymous visitor signs in from the app and the account block appears before the user's quota has been refreshed
- **THEN** the quota lines show the skeleton, not the anonymous quota text
- **AND** when the user's quota arrives, it replaces the skeleton without changing the block's size

### Requirement: Mobile session card reserves its space during restore

At viewports of 720px or less, while the app validates a saved session on load, the
sidebar SHALL render a placeholder of the same size as the compact session card. When
validation succeeds, the session card SHALL replace the placeholder without moving the
content below.

#### Scenario: Session restore on a phone

- **WHEN** the app loads at 390px wide with a valid saved session and the session check is delayed
- **THEN** the session card's space is reserved from the first render
- **AND** the cumulative layout shift, excluding shifts that also occur for an anonymous visitor at the same viewport and language, is below 0.01

#### Scenario: Invalid saved session on a phone

- **WHEN** the app loads at 390px with a saved session that the server rejects
- **THEN** the placeholder is removed and the anonymous sidebar is shown

#### Scenario: Anonymous visitor on a phone

- **WHEN** the app loads at 390px with no saved session
- **THEN** no placeholder is rendered and the sidebar layout is the same as before this change, except that the stacked sidebar no longer stretches when the page content is shorter than the viewport (it keeps its content height, as it already did in Spanish)

### Requirement: Stacked sidebar keeps its content height

At viewports of 1120px or less, where the sidebar is stacked above the page, the sidebar
SHALL keep its content height regardless of how tall the page content is. Short page
content MUST NOT stretch it.

#### Scenario: Page content renders after the sidebar

- **WHEN** the app loads at 390px and the page content is still shorter than the viewport
- **THEN** the sidebar has the same height as after the page content has rendered, and does not shift when the content appears

### Requirement: Deep analysis hint follows a restoring session

While the app validates a saved session on load, the deep analysis toggle's hint SHALL use
the signed-in text, so the hint does not change length when validation succeeds. The
toggle's behavior SHALL still depend on the validated session.

#### Scenario: Session restore on a phone with the analysis form

- **WHEN** the app loads at 390px with a valid saved session and the session check is delayed
- **THEN** the deep analysis hint shows the signed-in text from the first render and the toggle does not move when the session is validated

#### Scenario: Anonymous visitor sees the sign-in hint

- **WHEN** the app loads with no saved session
- **THEN** the deep analysis hint shows the sign-in text, as before
