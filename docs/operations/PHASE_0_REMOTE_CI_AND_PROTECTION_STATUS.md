# Phase 0 Remote, CI, and Protection Status

Repository: `BogaertN/forge2`

Visibility: **PRIVATE**

## Main state

Main commit:

`d805691e169e52bc00ea9ec674eba706abd3ddda`

Main remains unchanged during the closure-candidate
correction.

## Branch-protection disposition

Classic GitHub branch protection and repository rulesets
are unavailable for this private repository on the current
account plan.

The repository remains private. A paid-plan upgrade is not
required for the Forge 2.0 build.

## Preserved failed closure attempt

Build branch:

`build/phase0-000c-c-b1`

Commit:

`e683ffedf26506d8a2490707a89b4dfce5f73611`

Failed run:

`30571121938`

Failed job:

`90967820591`

Exact verifier result:

`Commit parent mismatch`

The failed GitHub Actions log proves that checkout used:

`fetch-depth: 1`

## Root cause

The verifier requires the current commit and `HEAD^` so it
can prove the exact parent.

The source, compilation, and unit tests passed. The parent
object was absent from the one-commit checkout.

## Accepted correction candidate

Build:

`FORGE2-PHASE0-BUILD-000C-C-B1-R2`

The workflow now declares:

`fetch-depth: 2`

Two commits are the minimum history needed to verify the
current commit and its direct parent.

The original failure remains preserved as evidence.

Phase 0 final acceptance remains pending until the corrected
build branch and then main pass GitHub Actions.
