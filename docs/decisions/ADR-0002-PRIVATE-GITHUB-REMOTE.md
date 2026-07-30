# ADR-0002: Establish a Private GitHub Remote

Status: Accepted

Decision Owner: Nicholas Jacob Bogaert / AI.Web Inc.

Build: FORGE2-PHASE0-BUILD-000C-B

## Context

Forge 2.0 requires an independent source-history and CI boundary.

The product license is not yet finalized. Public release and
redistribution policy are not yet approved.

## Decision

Create the repository `BogaertN/forge2` as a private GitHub
repository.

Use `main` as the initial default branch.

Preserve Forge 1 in its separate repository.

Do not copy Forge 1 source into Forge 2.0 during remote
establishment.

## Consequences

- Source history is independent.
- GitHub Actions can verify builds.
- Branch protection can be evaluated.
- The repository remains private while license and release policy
  are unresolved.
- Public release requires a separate Decision Owner record.
