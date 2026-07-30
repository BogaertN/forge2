# ADR-0010: Immutable RequestContract

Status:

**Accepted for Phase 1 Build 008A candidate
verification**

Build:

`FORGE2-PHASE1-BUILD-008A`

## Context

Build 006A established immutable InputEvent custody.

Build 007A established immutable authority-neutral
classification candidates.

The next initial contract in the controlling roadmap is
RequestContract: selected request meaning, goals,
constraints, desired result, uncertainty, and
authority-neutral metadata.

The roadmap places the complete automatic Request
Compiler in a later phase. Contract definition must not
be mistaken for compiler completion.

## Decision

Add:

- CandidateSelection;
- RequestStatement;
- RequestContract;
- deterministic selection identities;
- deterministic statement identities;
- exact InputEvent reference binding;
- exact ClassificationCandidateSet reference binding;
- required request-kind, expected-result, and
  side-effect selections;
- evidence-bound goals and constraints;
- one evidence-bound desired result;
- exact uncertainty preservation;
- strict canonical round trips;
- hidden-field rejection;
- explicit no-authority and no-effect laws.

## Selection decision

Build 008A records explicit selection evidence.

It does not decide which candidate should be selected.

Automatic candidate ranking, conflict resolution,
selection, correction, and clarification remain future
Request Compiler work.

## Source-custody decision

Every goal, constraint, and desired result must reference
FeatureEvidence belonging to a selected candidate.

Unselected candidates remain preserved in the source
candidate set and cannot silently influence the
RequestContract.

## Clarification decision

A candidate set recommending clarification is rejected as
a RequestContract source.

The system must clarify first rather than fabricating a
resolved request.

## Authority decision

RequestContract carries no authority.

It declares no side effects.

A selected side-effect classification is not execution
permission.

## Implementation-source decision

No Forge 1 source is copied or imported.

The implementation uses the accepted Forge 2 contract
kernel and the Python standard library.

## Consequences

Later modules can consume a typed request interpretation
without accepting hidden meaning, hidden authority, or
untraceable evidence.

ContextManifest remains the next unimplemented initial
contract after RequestContract integration.

Phase 1 remains in progress.
