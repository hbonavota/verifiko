# Spec Delta

## ADDED Requirements

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
