# Forge 1 Donor Qualification Policy

Forge 1 is read-only reference material.

Every possible donor component receives exactly one classification:

- DIRECT_REUSE
- ADAPTER_REQUIRED
- REWRITE_REQUIRED
- REFERENCE_ONLY
- DEPRECATED
- QUARANTINED

A donor component is not migrated until its:

- source path and commit are recorded;
- destination is recorded;
- behavior is tested;
- hidden imports are removed;
- path assumptions are removed;
- writes are declared;
- network behavior is declared;
- dependencies and licenses are recorded;
- capability contract is registered;
- independent verifier passes;
- contribution lineage is preserved.

Forge 2.0 must never add `/home/nic/forge` to its Python import path.

Forge 2.0 must never import Forge 1's main module.
