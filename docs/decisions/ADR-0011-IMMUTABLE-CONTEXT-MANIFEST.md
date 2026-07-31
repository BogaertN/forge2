# ADR-0011: Immutable bounded ContextManifest

Status:

**Accepted for Phase 1 Build 009A candidate
verification**

Build:

`FORGE2-PHASE1-BUILD-009A`

## Controlling roadmap

**AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent**

Document ID:

`1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0`

Controlling sections:

- 3.2 Source custody
- 8. Contract Architecture
- 10.3 Context manifest
- 10.4 Context versus memory

## Context

Build 006A established immutable InputEvent custody.

Build 007A established immutable classification
candidates.

Build 008A established immutable RequestContract
interpretation custody.

The next initial contract in the Production Build Bible
is ContextManifest: the exact evidence admitted into a
task.

## Decision

Add:

- RepositorySnapshot;
- ContextBudget;
- ContextItemKind;
- ContextItem;
- ExcludedContextItem;
- ContextManifest;
- deterministic identities;
- canonical content hashes;
- canonical byte accounting;
- explicit admission basis;
- explicit exclusion reasons;
- exact RequestContract binding;
- exact repository-commit binding;
- strict canonical decoding;
- hidden-field rejection;
- no-authority and no-effect laws.

## Boundedness decision

Every ContextManifest has hard item, per-item byte, and
total-byte limits.

Boundedness is validated by the contract rather than left
as an informal runtime promise.

## Admission decision

Build 009A records explicit admission decisions.

It does not retrieve, rank, or automatically select
context.

Future Context Builder services must produce these typed
records and remain separately governed and verified.

## Exclusion decision

Excluded material remains identifiable by source,
revision, locator, hash, size, and reason.

Excluded content is not silently inserted into the
admitted payload.

## Memory decision

Repository state, candidate memory, documentation, and
runtime proof remain separate evidence classes.

A memory candidate included in a manifest is not promoted
to canonical memory or truth.

## Authority decision

ContextManifest carries no authority and declares no side
effects.

Context presence cannot authorize a tool, command,
mutation, plan, memory promotion, or execution.

## Implementation-source decision

No Forge 1 source is copied or imported.

The implementation uses the accepted Forge 2 contract
kernel and Python standard library.

## Consequences

Later planners can receive a reproducible and bounded
evidence package without accepting hidden context,
unbounded context, hidden memory, or hidden authority.

CapabilityRequirement remains the next unimplemented
initial contract after ContextManifest integration.

Phase 1 remains in progress.
