# ADR-0007: Exact Request-State Identities

Status:

**Accepted for Phase 1 Build 005A candidate
verification**

Build:

`FORGE2-PHASE1-BUILD-005A`

## Context

Build 004A established generic append-only successor
laws.

The controlling roadmap provides 25 exact request-state
names and requires transition receipts, but it does not
define the complete lawful transition edge table.

Treating the written sequence as a universal linear edge
table would create false transitions such as treating
failure, hold, cancellation, result delivery, application,
commit, release, and archive as one unconditional chain.

## Decision

Implement only:

- the exact `RequestState` vocabulary;
- stable ordinals;
- stable state codes;
- deterministic state IDs;
- an immutable deterministic registry;
- strict registry validation;
- an explicit transition-policy hold.

## Non-decision

Build 005A does not decide:

- which states may transition to which other states;
- which states may resume after hold;
- how clarification returns to the main path;
- how failure, retry, cancellation, or recovery works;
- when delivery may proceed to apply;
- who may authorize apply, commit, or release.

## Consequences

Later work can reference exact state identities without
guessing their transition behavior.

A later Decision Owner-backed build must establish the
complete transition matrix before request-state
transitions or transition receipts are activated.

Phase 1 remains in progress.
