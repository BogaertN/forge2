# ADR-0003: Branch Protection Disposition

Status: Accepted

Decision Owner: Nicholas Jacob Bogaert / AI.Web Inc.

Build: FORGE2-PHASE0-BUILD-000C-C-B1

## Verified evidence

Parent commit:

`d805691e169e52bc00ea9ec674eba706abd3ddda`

GitHub Actions run:

`30569975781`

Successful check:

`phase-zero`

Both classic branch protection and repository ruleset
APIs reported that GitHub Pro or public repository
visibility is required.

## Decision

Keep `BogaertN/forge2` private.

Do not require a paid-plan upgrade as a condition of the
Forge 2.0 build.

Do not make Forge 2.0 public merely to obtain branch
protection.

Record server-side protection as unavailable under the
current account plan.

Use branch-first, CI-before-main, fast-forward-only, and
local pre-push controls until server-side protection
becomes available.

## Limitation

Local and procedural controls do not equal server-side
branch enforcement. The limitation remains visible and
must not be described as GitHub branch protection.
