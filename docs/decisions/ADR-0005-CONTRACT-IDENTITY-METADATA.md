# ADR-0005: Immutable Contract Identity Metadata

Status:

**Accepted for Phase 1 Build 003A candidate
verification**

Build:

`FORGE2-PHASE1-BUILD-003A`

## Context

Build 002A established canonical serialization, hashing,
and stable identifiers.

Phase 1 next requires common identity, schema, ancestry,
lifecycle, authority-disposition, effect-declaration, and
validation structures before concrete domain contracts
are created.

## Decision

Add standard-library-only immutable primitives:

- `SchemaVersion`;
- `LifecycleState`;
- `AuthorityStatus`;
- `EffectKind`;
- `DeclaredEffect`;
- `ContractReference`;
- `ContractMetadata`;
- structured validation and integrity errors;
- deterministic metadata construction and body
  verification.

## Identity rule

The body hash binds canonical content.

The contract ID binds the body hash and all material
metadata fields except the contract ID itself.

## Immutability rule

Stored metadata and references use frozen, slotted
dataclasses.

Declared effects are stored as canonically ordered tuples.

## Authority boundary

`AuthorityStatus.AUTHORIZED` is descriptive metadata. It
is not an executable permission token and is not accepted
by any runtime authority in Build 003A.

## Consequences

Later contracts can carry uniform identity and direct
ancestry.

Later builds must still define:

- append-only successor transition laws;
- request and action state machines;
- concrete Section 8 contract families;
- schema evolution compatibility;
- authority enforcement;
- acceptance gates.

Phase 1 remains in progress.
