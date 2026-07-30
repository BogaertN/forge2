# Forge 2.0 Coding Standards

## General requirements

- Python production code targets Python 3.12 or later.
- Public interfaces require type annotations.
- Contracts are versioned and serializable.
- Domain objects are immutable or append-only where practical.
- Hidden global mutable state is prohibited.
- Entry points remain thin.
- Errors use explicit typed states or exceptions.
- Filesystem paths use pathlib.
- Subprocess execution uses argument arrays.
- Timeouts are mandatory for external processes.
- Network access is explicit.
- Tests accompany behavior.
- Failure evidence is preserved.

## Dependency requirements

- Use an isolated environment.
- Never use bare `pip3`.
- Invoke package installation through the environment's exact
  `python -m pip`.
- Pin and hash admitted dependencies.
- Record license and provenance.
- Do not add a dependency before capability qualification.

## Module requirements

- No monolithic main file.
- Contracts must not depend on runtime adapters.
- Adapters may depend on contracts.
- Verification consumes stable artifacts rather than mutable builder
  internals when possible.
- The UI communicates through API contracts.

## Terminal requirements

- No unrestricted shell strings as an internal execution API.
- Prefer executable identity plus argument list.
- Declare working directory, environment, filesystem policy, network
  policy, timeout, and expected outputs.

## Review requirements

Every material change must identify:

- roadmap phase;
- build ID;
- objective;
- source scope;
- protected boundaries;
- tests;
- verifier;
- rollback;
- contribution lineage.
