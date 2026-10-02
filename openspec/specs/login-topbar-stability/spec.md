# login-topbar-stability Specification

## Purpose

Keeps the app topbar's account area visually stable while authentication and quota state
load, so signing in or restoring a session does not push the page content around
(cumulative layout shift).

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
