# RequestContract Version 1

Build:

`FORGE2-PHASE1-BUILD-008A`

Controlling roadmap:

AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent

## Purpose

RequestContract records one selected structured
interpretation of an exact InputEvent.

It preserves:

- selected classification candidates;
- goals;
- constraints;
- the desired result;
- uncertainty;
- exact source-contract references;
- producer identity;
- authority-neutral contract metadata.

## Source chain

Every RequestContract identifies:

- its exact InputEvent;
- its exact ClassificationCandidateSet;
- each selected candidate;
- the feature evidence supporting each goal,
  constraint, and desired result.

Statement evidence must originate from selected
candidates. Evidence from an unselected candidate cannot
silently enter the RequestContract.

## Required selected dimensions

Version 1 requires exactly one selected candidate for
each of these dimensions:

- request kind;
- expected result;
- side-effect class.

Additional dimensions may be selected, but no dimension
may be selected more than once.

## CandidateSelection

CandidateSelection records:

- selection identity;
- candidate identity;
- candidate dimension;
- candidate label;
- explicit basis codes.

CandidateSelection does not perform selection.

It records a selection supplied by a future lawful
compiler, reviewed operator, test fixture, or other
identified producer.

## Request statements

RequestStatement has one exact kind:

- `goal`;
- `constraint`;
- `desired_result`.

Every statement has:

- a deterministic statement ID;
- a stable code;
- human-readable text;
- one or more exact FeatureEvidence IDs.

## Uncertainty preservation

Version 1 requires the RequestContract to preserve the
candidate set's exact uncertainty codes.

Uncertainty cannot be silently deleted during contract
creation.

## Clarification boundary

A ClassificationCandidateSet that recommends
clarification cannot produce a RequestContract.

Clarification resolution belongs to a separate future
implementation and evidence chain.

## Authority boundary

RequestContract always uses authority status `none`.

It declares no material side effects.

Selected side-effect classification is descriptive
evidence. It is not permission to perform that effect.

RequestContract cannot authorize:

- terminal access;
- file writes;
- network access;
- package installation;
- Git mutation;
- memory promotion;
- tool selection;
- plan execution.

## Compiler boundary

Build 008A defines the typed contract and strict
validation laws only.

It does not implement the roadmap's later Request
Compiler phase, automatic conflict rules, expected-result
inference, side-effect inference, capability inference,
correction hooks, or broad-corpus evaluation.

## Phase status

Phase 1 remains in progress.
