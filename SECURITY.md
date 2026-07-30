# Security Policy

## Current status

Forge 2.0 is in pre-capability establishment.

No release is currently supported for production deployment.

## Security principles

1. Read-only inspection is the default.
2. No model or classifier receives direct execution authority.
3. No arbitrary shell command is accepted as an internal API.
4. No package is admitted because it ranks highly in search.
5. New tools enter quarantine before qualification.
6. Secrets must not enter Git, task logs, model datasets, candidate
   memory, or contribution records.
7. Forge 1 is a protected read-only reference.
8. The live project worktree is never the experimentation workspace.
9. Builder and verifier responsibilities remain separate.
10. Every material mutation requires scope, authority, evidence,
    verification, and rollback.

## Reporting

Do not publish credentials, exploit details, or private system data in
a public issue. Report security concerns through the Decision Owner's
established private communication channel.

## Supported versions

No production version is currently supported. Support begins only after
the release acceptance gate in the controlling roadmap passes.
