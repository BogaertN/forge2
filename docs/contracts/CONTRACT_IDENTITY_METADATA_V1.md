# Contract Identity Metadata Version 1

Build:

`FORGE2-PHASE1-BUILD-003A`

Controlling roadmap:

AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent

## Purpose

This specification defines immutable identity metadata
shared by later Forge 2 contracts.

It does not define `InputEvent`, `RequestContract`, or
any other Section 8 domain contract.

## Schema version

Schema versions use strict canonical:

`major.minor.patch`

Components are non-negative integers without leading
zeros.

## Contract content hash

`content_hash` is the SHA-256 digest of the canonical
contract body.

The body does not include its own metadata object.

## Contract identifier

`contract_id` is derived from:

- schema version;
- contract type;
- canonical body hash;
- UTC creation time;
- lifecycle state;
- authority disposition;
- direct parent reference;
- canonically ordered declared effects.

Form:

`aiweb.contract:sha256:<64 lowercase hex characters>`

## Parent reference

A parent reference carries:

- parent contract ID;
- parent content hash;
- parent contract type;
- parent schema version.

Build 003A records direct ancestry only. Successor
transition laws are a later Phase 1 build.

## Lifecycle states

- draft;
- candidate;
- accepted;
- superseded;
- rejected;
- archived.

These are identity-bearing snapshot states. State changes
must later produce append-only successors rather than
mutate an existing record.

## Authority disposition

- none;
- advisory;
- requested;
- authorized;
- denied;
- revoked.

An authority value is recorded evidence only. It does not
itself grant execution, write, network, installation,
memory, planning, or verification permission.

## Declared effects

Supported declaration categories are:

- read;
- write;
- delete;
- execute;
- network;
- install;
- apply;
- commit;
- release.

Declaring an effect does not authorize it.

## Validation

Failures carry a stable code, field, and message.

Invalid identity values are rejected rather than repaired
or silently converted.

## Boundaries

Build 003A adds no terminal broker, executor, planner,
language authority, memory authority, product capability,
or user-facing workflow.
