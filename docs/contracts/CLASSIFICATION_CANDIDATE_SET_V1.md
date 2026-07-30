# ClassificationCandidateSet Version 1

Build:

`FORGE2-PHASE1-BUILD-007A`

Controlling roadmap:

AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent

## Purpose

ClassificationCandidateSet records structured
authority-neutral suggestions produced by deterministic
language rules or permitted small classifiers.

It does not select request meaning.

## Candidate dimensions

Version 1 supports:

- request kind;
- domain;
- expected result;
- side-effect class;
- freshness requirement;
- capability;
- code-versus-explanation distinction;
- tool-discovery requirement;
- simulation requirement;
- clarification requirement;
- risk candidate.

## Candidate origin

Every candidate declares one origin:

- `rule`;
- `model`.

Every candidate also names its exact producer ID.

## Feature evidence

Every candidate must contain at least one immutable
FeatureEvidence record.

Evidence uses an exact JSON pointer into the source
InputEvent body.

Text evidence may additionally record exact start and end
offsets.

Evidence identity is content-addressed using:

`aiweb.feature-evidence:sha256:<64 lowercase hex>`

## Confidence

Floating-point values are forbidden by the Forge 2
canonical serialization profile.

Confidence is therefore stored as an integer from zero to
ten thousand basis points.

This makes confidence identity deterministic across
programming languages and platforms.

A confidence value is evidence from a producer. It is not
final authority.

## Candidate identity

Candidate identity binds:

- dimension;
- label;
- origin;
- producer;
- confidence;
- feature evidence.

Candidate IDs use:

`aiweb.classification-candidate:sha256:<64 lowercase hex>`

## Candidate-set body

The set contains:

- the exact InputEvent reference;
- zero or more candidates;
- uncertainty codes;
- a clarification recommendation;
- clarification reason codes.

A set may contain zero candidates only when clarification
is explicitly recommended with at least one reason.

## Authority boundary

ClassificationCandidateSet always carries authority status
`none`.

It cannot declare side effects.

It cannot select a candidate, create a RequestContract,
select a tool, create a command, or authorize execution.

## Distinction from conclusion candidates

This contract represents request-classification
candidates before RequestContract selection.

It is not the later RMC candidate-conclusion object and
does not select final meaning or output.

## Phase status

Phase 1 remains in progress.
