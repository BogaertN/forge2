# Canonical Serialization Profile Version 1

Build:

`FORGE2-PHASE1-BUILD-002A`

Controlling roadmap:

AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent

## Purpose

This profile establishes deterministic serialization,
hashing, and stable identity primitives for later Forge 2
immutable contracts.

It does not define any Section 8 domain contract yet.

## Approved input

- `None`;
- booleans;
- JSON-safe integers;
- Unicode strings normalized to NFC;
- timezone-aware datetimes normalized to UTC;
- dates;
- enum values whose values are themselves approved;
- frozen dataclass instances;
- mappings with string keys;
- lists and tuples.

## Explicit rejection

The profile rejects:

- floating-point values;
- integers outside the interoperable JSON safe range;
- naive datetimes;
- bytes;
- sets and frozen sets;
- mapping keys that are not strings;
- mapping keys that collide after Unicode normalization;
- mutable dataclasses;
- recursive container ancestry;
- arbitrary custom-object conversion;
- invalid stable-ID namespaces.

Rejection is intentional. Forge must not invent an
encoding for ambiguous values.

## Canonical JSON

Canonical JSON uses:

- normalized values;
- sorted mapping keys;
- compact separators;
- UTF-8;
- no ASCII escaping requirement;
- no NaN or infinity;
- SHA-256 for content digests.

This is an AI.Web Forge 2 profile. It does not claim full
RFC 8785 compatibility.

## Stable identifier

A stable identifier has the form:

`namespace:sha256:<64 lowercase hexadecimal characters>`

The namespace must be explicit and validated.

## Authority boundary

Serialization and hashing do not grant truth, permission,
execution, verification, memory, planning, or acceptance
authority.
