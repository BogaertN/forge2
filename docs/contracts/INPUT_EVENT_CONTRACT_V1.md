# InputEvent Contract Version 1

Build:

`FORGE2-PHASE1-BUILD-006A`

Controlling roadmap:

AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent

Compatible architecture reference:

The Recursive Manifest Compiler - Section 03.1 Input Event

## Formal structure

The architecture defines:

`I_t = {x_t, c_t, u_t, τ_t}`

Build 006A maps those components to:

- `raw_input`;
- `conversation_context`;
- `identity_context`;
- `session_metadata`.

## Deep immutability

Every field is canonicalized and recursively frozen.

Lists become immutable tuple-backed canonical lists.

Mappings become immutable, sorted canonical mappings.

Mutation of an input object after contract creation cannot
alter the stored event.

## Metadata

InputEvent uses:

- contract type `InputEvent`;
- schema version `1.0.0`;
- deterministic canonical body hash;
- deterministic contract ID;
- timezone-aware UTC creation time;
- immutable contract metadata.

## Authority boundary

InputEvent must use authority status `none`.

InputEvent cannot declare side effects.

User input is evidence of a request. It is not permission
to execute, write, install, apply, commit, release, mutate
memory, or select a tool.

## Exact field boundary

Serialization accepts exactly:

- top level: `metadata`, `body`;
- body: the four formal InputEvent fields.

Missing and hidden fields are rejected.

## Round trip

Canonical serialization followed by strict decoding must
recreate the identical immutable InputEvent.

## Exclusions

Build 006A does not implement:

- interpretation;
- classification candidates;
- RequestContract;
- request-state transitions;
- terminal access;
- planning;
- execution;
- memory writes;
- product capability.
