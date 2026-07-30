# Request Lifecycle State Identities Version 1

Build:

`FORGE2-PHASE1-BUILD-005A`

Controlling roadmap:

AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent

## Purpose

This specification establishes the exact request-state
vocabulary named by the controlling roadmap.

It defines state identity only.

It does not define transition permission.

## Exact state sequence

1. `RECEIVED`
2. `CUSTODIED`
3. `INTERPRETATION_CANDIDATES_READY`
4. `CLARIFICATION_REQUIRED`
5. `REQUEST_CONTRACT_READY`
6. `CONTEXT_READY`
7. `CAPABILITY_REQUIREMENTS_READY`
8. `CAPABILITY_RESOLVED`
9. `PLAN_READY`
10. `AWAITING_AUTHORITY`
11. `AUTHORIZED`
12. `EXECUTING`
13. `EXECUTION_COMPLETE`
14. `VERIFYING`
15. `VERIFIED`
16. `FAILED`
17. `HELD`
18. `CANCELLED`
19. `RESULT_READY`
20. `DELIVERED`
21. `APPLY_PENDING`
22. `APPLIED`
23. `COMMITTED`
24. `RELEASED`
25. `ARCHIVED`

The sequence is preserved as source authority and stable
ordinal identity. Sequence position alone does not grant
a transition.

## State identity

Each state carries:

- exact uppercase roadmap value;
- zero-based ordinal;
- stable state code;
- schema version `1.0.0`;
- deterministic SHA-256 state identity.

State IDs use:

`aiweb.request-state:sha256:<64 lowercase hex>`

## Registry identity

The complete exact registry receives a deterministic ID:

`aiweb.request-state-registry:sha256:<64 lowercase hex>`

## Transition-policy hold

The controlling roadmap requires:

- no silent state skipping;
- a receipt for every real state transition.

It does not provide a complete edge table covering every
clarification, failure, hold, cancellation, result,
delivery, apply, commit, release, and archive branch.

Build 005A therefore records:

`transition_policy_defined = false`

No transition API, edge table, permission, or transition
receipt is introduced.

## Boundaries

Build 005A adds no:

- transition authority;
- execution authority;
- permission authority;
- request contract;
- input event;
- task plan;
- terminal broker;
- memory write;
- language interpretation;
- product capability.
