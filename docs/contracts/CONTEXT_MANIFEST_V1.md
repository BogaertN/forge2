# ContextManifest Version 1

Build:

`FORGE2-PHASE1-BUILD-009A`

## Controlling roadmap

**AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent**

Document ID:

`1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0`

Referenced sections:

- 3.2 Source custody
- 8. Contract Architecture
- 10.3 Context manifest
- 10.4 Context versus memory

## Build Bible requirement

ContextManifest is the exact evidence admitted into a
task.

Every task step receives bounded context containing only
the material needed for that step.

The Production Build Bible identifies:

- exact file slices;
- symbol references;
- repository commit;
- relevant test outputs;
- applicable policies;
- admitted documentation;
- capability descriptions;
- memory candidates;
- prior task results;
- excluded material and its exclusion reason.

## Purpose

Version 1 records:

- the exact RequestContract;
- the exact task-step identity;
- the exact repository and Git commit;
- hard item and canonical-byte budgets;
- exact admitted context;
- why each item was admitted;
- exact excluded material identity;
- why each excluded item was excluded;
- authority-neutral contract metadata.

## Context item categories

The exact version 1 vocabulary is:

- `file_slice`;
- `symbol_reference`;
- `test_output`;
- `policy`;
- `documentation`;
- `capability_description`;
- `memory_candidate`;
- `prior_task_result`.

## Exact admitted content

Admitted ContextItem records:

- deterministic item identity;
- category;
- source URI;
- source revision;
- exact locator;
- canonical content hash;
- canonical byte count;
- deeply frozen canonical content;
- explicit admission-basis codes.

## Exact excluded material

ExcludedContextItem records:

- deterministic exclusion identity;
- source identity and locator;
- canonical content hash and byte count;
- exclusion reason code;
- human-readable exclusion reason.

Excluded content itself is not placed into the admitted
manifest payload.

## Boundedness

ContextBudget defines:

- maximum admitted item count;
- maximum total canonical bytes;
- maximum canonical bytes per item.

A manifest that exceeds any budget is invalid.

## Repository custody

RepositorySnapshot identifies:

- stable repository URI;
- exact full Git commit SHA;
- deterministic snapshot identity.

## Context versus memory

In accordance with the Production Build Bible:

- repository state is not memory;
- candidate memory is not repository truth;
- design documentation is not runtime proof.

Memory candidates may be recorded as context candidates,
but their presence does not promote or canonicalize them.

## Authority boundary

ContextManifest always carries authority status `none`.

It declares no material side effects.

Inclusion in context does not authorize:

- tool selection;
- planning;
- file access;
- network access;
- package installation;
- execution;
- memory promotion;
- Git mutation;
- delivery.

## Runtime boundary

Build 009A defines the contract only.

It does not implement:

- context retrieval;
- relevance ranking;
- automatic context selection;
- Context Builder runtime;
- stale-context detection;
- memory promotion;
- task planning;
- tool selection;
- execution authority.

## Phase status

Phase 1 remains in progress.
