# Open-Source-First Capability Policy

## Required order

A Forge plan must evaluate capability sources in this order:

1. Registered and verified Forge 2.0 capability
2. Suitable locally installed tool
3. Qualified Forge 1 donor component
4. Suitable open-source package, command, library, service, model, or
   repository
5. Configuration of an existing tool
6. Composition of existing tools
7. Bounded adapter, wrapper, validator, or workflow
8. Permitted modification of open-source code
9. Original implementation

Original implementation requires evidence explaining why the prior
options were unsuitable.

## Search is not admission

Popularity, download count, repository stars, package rank, or search
position may inform comparison. None of them authorize installation or
execution.

## Qualification

A tool must be evaluated for:

- functional fit;
- source identity;
- exact version;
- license;
- dependencies;
- privileges;
- network and filesystem behavior;
- install scripts;
- resource use;
- vulnerabilities;
- testability;
- sandbox compatibility;
- rollback;
- contribution provenance.

## Host installation

New packages do not enter the host or primary runtime by default.
Qualification occurs in quarantine.
