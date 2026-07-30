# ADR-0009: ClassificationCandidateSet Contract

Status:

**Accepted for Phase 1 Build 007A candidate
verification**

Build:

`FORGE2-PHASE1-BUILD-007A`

## Context

Build 006A established immutable InputEvent custody.

The controlling roadmap requires the next initial contract
to preserve rule and permitted-model request candidates
without allowing those candidates to become commands,
permissions, selected meaning, or tool authority.

## Decision

Add:

- CandidateDimension;
- CandidateOrigin;
- FeatureEvidence;
- ClassificationCandidate;
- ClassificationCandidateSet;
- strict InputEvent evidence pointers;
- optional exact text spans;
- content-addressed evidence and candidate IDs;
- basis-point confidence values;
- uncertainty and clarification records;
- strict round-trip decoding;
- hidden-field rejection.

## Fixed-point confidence decision

The canonical profile forbids floating-point values.

Confidence therefore uses integer basis points between
zero and ten thousand.

This is a storage and identity representation. It does not
make confidence authoritative.

## Source-custody decision

Every candidate must point to at least one exact feature
observation inside the source InputEvent.

Unsupported or missing pointers are rejected.

## Authority decision

No candidate is selected.

No RequestContract is created.

No command, tool route, side effect, permission, runtime
authority, or memory authority is created.

## Implementation-source decision

No Forge 1 source is copied or imported.

The implementation uses only the Python standard library
and the already accepted Forge 2 contract kernel.

## Consequences

Later deterministic rules and qualified small models can
exchange typed request candidates without hidden fields.

A later build must separately define RequestContract and
its candidate-selection evidence.

Phase 1 remains in progress.
