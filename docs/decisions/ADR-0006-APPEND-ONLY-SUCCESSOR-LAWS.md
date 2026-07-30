# ADR-0006: Append-Only Contract Successor Laws

Status:

**Accepted for Phase 1 Build 004A candidate
verification**

Build:

`FORGE2-PHASE1-BUILD-004A`

## Context

Build 003A established immutable contract metadata and a
direct parent reference.

A parent pointer alone does not prove that a successor is
valid. Explicit transition laws and receipts are needed.

## Decision

Add standard-library-only successor primitives:

- `SuccessorKind`;
- `SuccessorReceipt`;
- `SuccessorTransition`;
- `create_successor`;
- `verify_successor`;
- lifecycle transition tables;
- authority-disposition transition tables;
- schema step validation;
- body and effect revision constraints;
- no-op and mixed-transition rejection.

## Atomicity rule

Independent transition dimensions must normally be
represented by separate immutable successors.

Schema revision may include a body change.

## Authority boundary

Authority status remains descriptive evidence.

Successor validation does not grant permission and does
not execute any declared effect.

## Consequences

Later concrete contracts can form auditable append-only
chains.

Later Phase 1 builds must still define:

- request-state identities;
- action-state identities;
- concrete Section 8 domain contracts;
- domain-specific compatibility laws;
- phase acceptance.

Phase 1 remains in progress.
