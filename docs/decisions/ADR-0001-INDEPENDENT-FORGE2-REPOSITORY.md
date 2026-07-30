# ADR-0001: Build Forge 2.0 as an Independent Repository

Status: Accepted

Decision Owner: Nicholas Jacob Bogaert / AI.Web Inc.

## Context

Forge 1 contains valuable working code, tests, policies, receipts,
experiments, and architectural lessons. It also contains extensive
historical coupling and a monolithic runtime structure.

Continuing to layer the new product inside Forge 1 would risk carrying
forward hidden dependencies and competing routing systems.

## Decision

Forge 2.0 shall be built as a separate repository and independent
runtime.

Forge 1 shall remain preserved as:

- reference implementation;
- requirements archive;
- behavioral test source;
- donor source for individually qualified components;
- historical evidence.

Forge 2.0 production code shall not import Forge 1's main module or
require the Forge 1 repository to run.

## Consequences

Positive consequences:

- clean source history;
- clean dependency graph;
- enforceable module boundaries;
- independent packaging;
- independent UI;
- explicit donor migration;
- easier verification and release.

Required costs:

- components must be inventoried and qualified;
- adapters must be written;
- behavior must be re-proven;
- no component is accepted merely because it existed in Forge 1.

## Reversal

Reversal requires an explicit superseding architecture decision from
the Decision Owner.
