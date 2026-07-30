# ADR-0008: Immutable InputEvent Contract

Status:

**Accepted for Phase 1 Build 006A candidate
verification**

Build:

`FORGE2-PHASE1-BUILD-006A`

## Context

The controlling roadmap lists InputEvent as the first
initial cross-module contract.

The compatible RMC architecture defines the event as raw
input, conversation context, identity context, and
time/session metadata.

Existing canonical hashing alone is insufficient because
mutable lists and dictionaries could be altered after
hashing.

## Decision

Add:

- deeply immutable canonical value containers;
- strict contract metadata decoding;
- a frozen InputEvent dataclass;
- four exact formal fields;
- canonical round-trip encoding and decoding;
- body-hash verification;
- hidden-field rejection;
- explicit no-authority and no-side-effect laws.

## Authority decision

InputEvent cannot carry authority.

InputEvent cannot declare effects.

Its existence proves only that a structured input
condition was received.

## Source decision

No Forge 1 implementation source is copied.

The historical RMC definition is used as compatible
architecture reference only.

## Consequences

Forge 2 gains its first concrete typed domain contract.

Later builds may consume InputEvent only through typed,
validated interfaces.

Phase 1 remains in progress.
