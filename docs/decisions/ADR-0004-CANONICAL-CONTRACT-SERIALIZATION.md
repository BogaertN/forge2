# ADR-0004: Canonical Contract Serialization

Status:

**Accepted for Phase 1 Build 002A candidate verification**

Build:

`FORGE2-PHASE1-BUILD-002A`

## Context

Phase 1 requires deterministic serialization, stable
hashes, and immutable contract foundations.

The donor review established that Forge 1 contains an
`InputEvent` schema label but no implemented `InputEvent`
class suitable for admission.

Installed third-party libraries were not admitted.

## Decision

Use Python 3.12 standard-library primitives:

- `dataclasses`;
- `datetime`;
- `enum`;
- `hashlib`;
- `json`;
- `typing`;
- `unicodedata`.

Use a strict rejection-first profile rather than implicit
conversion.

## Consequences

Later contracts can rely on deterministic bytes, hashes,
and namespaced content identities.

Later builds must still define:

- contract metadata;
- ancestry;
- lifecycle states;
- authority states;
- successor rules;
- concrete Section 8 domain contracts.

Build 002A does not accept Phase 1 as complete and does
not add a user-facing product capability.
