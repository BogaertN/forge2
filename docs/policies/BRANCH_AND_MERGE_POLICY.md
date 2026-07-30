# Forge 2.0 Branch and Merge Policy

## Required development sequence

1. Confirm local main and remote main match.
2. Confirm the repository is clean.
3. Create a build branch.
4. Make only approved changes.
5. Run local tests and the current verifier.
6. Commit one coherent change.
7. Push the build branch.
8. Require successful build-branch CI.
9. Advance local main by fast-forward only.
10. Push main through the tracked pre-push gate.
11. Confirm remote main matches the verified commit.
12. Require successful main CI.
13. Preserve the evidence.

## Prohibited operations

- force-pushing main;
- deleting main;
- rewriting accepted history;
- integrating an unverified build branch;
- bypassing the current verifier;
- changing the payload after verification;
- making the repository public only to obtain branch
  protection.

## Local pre-push control

The tracked `.githooks/pre-push` program rejects branch
deletion and non-fast-forward pushes.

Main pushes additionally run the local test suite and
`scripts/verify_current.py`.

Local Git must set:

`core.hooksPath = .githooks`
