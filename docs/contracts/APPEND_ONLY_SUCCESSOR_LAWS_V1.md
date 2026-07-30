# Append-Only Contract Successor Laws Version 1

Build:

`FORGE2-PHASE1-BUILD-004A`

Controlling roadmap:

AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent

## Purpose

This specification defines how one immutable Forge 2
contract metadata snapshot may legally succeed another.

Existing records are never mutated.

## Structural laws

Every successor must:

- have a different contract ID;
- preserve the contract type;
- directly reference the predecessor;
- use a creation time later than the predecessor;
- pass canonical body verification;
- satisfy exactly one primary successor law;
- produce a deterministic successor receipt.

## Supported successor laws

### Body revision

Body revisions are permitted only while the predecessor
is `draft` or `candidate`.

A body revision cannot be combined with lifecycle,
authority, or declared-effect changes.

### Schema revision

A schema revision may optionally include a body change.

It cannot also change lifecycle, authority, or declared
effects.

Allowed version steps are exactly:

- next patch;
- next minor with patch reset to zero;
- next major with minor and patch reset to zero.

### Lifecycle transition

Lifecycle transitions are isolated snapshots governed by
an explicit transition table.

Terminal or historical states cannot silently return to
editable states.

### Authority-disposition transition

Authority values are recorded dispositions only.

They do not grant execution permission.

Direct `none` to `authorized` transition is forbidden.
Authority must first become `requested`.

### Declared-effect revision

Declared-effect revision is permitted only while the
predecessor is `draft` or `candidate`.

Declaring an effect does not authorize it.

## No-op rule

A later timestamp alone does not make a valid successor.

At least one material dimension must change.

## Mixed-transition rule

Independent state changes must be recorded as separate
append-only successors.

Schema revision is the sole Version 1 exception and may
include a body change because schema and body migration
may be inseparable.

## Successor receipt

The receipt binds:

- predecessor reference;
- successor reference;
- successor kind;
- rule identity;
- changed fields;
- observed UTC time;
- predecessor state hash;
- successor state hash.

Receipt identity uses:

`aiweb.successor:sha256:<64 lowercase hex characters>`

## Boundaries

Build 004A adds no executor, terminal broker, planner,
language authority, memory authority, permission grant,
domain contract, or product capability.
