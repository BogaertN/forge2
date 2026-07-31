# CapabilityRequirement Version 1

Build: `FORGE2-PHASE1-BUILD-010A`

Correction: `FORGE2-PHASE1-BUILD-010A-R2`

## Controlling roadmap

**AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent**

Document ID: `1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0`

Referenced sections:

- 3.1 Authority separation
- 8. Contract Architecture
- 11. Open-Source Capability Fabric
- 11.3 Discovery query

## Production Build Bible definition

CapabilityRequirement is a provider-neutral
description of required behavior.

A discovery request describes required behavior rather
than guessing a package, provider, or tool name.

## Version 1 records

- exact RequestContract binding;
- exact ContextManifest binding;
- required behavior;
- exact RequestStatement ancestry;
- provider-neutral input requirements;
- provider-neutral output requirements;
- selected request side-effect classification;
- required property codes;
- observable acceptance criteria;
- preserved uncertainty;
- canonical identities and serialization.

## Provider-neutral boundary

The contract does not contain provider identity,
package name, tool name, executable, command, endpoint,
adapter, provider version, ranking, qualification,
installation, or execution authority.

## Authority boundary

CapabilityRequirement carries authority status `none`
and declares no material side effects.

Recording a required side-effect class does not
authorize that side effect.

## Correction record

The original fixture incorrectly recorded
`without choosing a provider` at span `61–88`.

Its exact zero-based half-open span is `60–87`.

Build 010A-R2 corrects the three fixture occurrences
without weakening evidence validation or changing the
contract boundary.

Build 010A-R1 stopped before this correction because
its baseline verifier inspected the candidate working
tree rather than a clean accepted-main snapshot.

## Not implemented

- CapabilityContract;
- ToolCandidate;
- capability registry runtime;
- provider discovery;
- provider ranking or selection;
- package installation;
- qualification;
- planning;
- execution authority.

Phase 1 remains in progress.
