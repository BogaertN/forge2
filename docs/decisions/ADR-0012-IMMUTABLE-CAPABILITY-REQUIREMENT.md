# ADR-0012: Immutable provider-neutral CapabilityRequirement

Status: **Accepted for Build 010A-R2 candidate verification**

## Controlling roadmap

**AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent**

Document ID: `1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0`

## Decision

Add immutable:

- CapabilityDataDirection;
- CapabilityDataRequirement;
- CapabilityAcceptanceCriterion;
- CapabilityRequirement.

Bind the requirement to exact RequestContract,
ContextManifest, RequestStatement, and side-effect
classification identities.

Require provider-neutral inputs, outputs, properties,
acceptance criteria, and uncertainty preservation.

## Provider separation

CapabilityRequirement defines what behavior is needed.

It does not name, discover, rank, select, qualify,
install, authorize, or execute a provider.

CapabilityContract remains a later and separate
contract.

## Evidence-span correction

The original Build 010A fixture used character span
`61–88` for `without choosing a provider`.

The exact span is `60–87`.

Build 010A-R2 corrects all three fixture copies.
Evidence checking remains mandatory and unchanged.

## Recovery-harness correction

Build 010A-R1 ran the accepted Build 009A verifier
against a candidate tree containing the preserved
untracked CapabilityRequirement source.

The accepted baseline verifier must instead run against
a temporary clean clone of accepted `main`.

This changes recovery verification only. It does not
change the contract, tests, accepted baseline, or
repository history.

## Authority

CapabilityRequirement has no authority and declares no
side effects.

Phase 1 remains in progress.
