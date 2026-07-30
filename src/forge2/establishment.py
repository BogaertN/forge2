"""Final Phase 0 establishment identity.

This module reports accepted establishment state only.
It does not provide a product capability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Final


BUILD_ID: Final[str] = "FORGE2-PHASE0-BUILD-000C-C-B3"
FORGE2_VERSION: Final[str] = "0.0.0"

STATUS_SCHEMA_VERSION: Final[str] = (
    "aiweb_forge2_establishment_status_v4"
)

CONTROLLING_ROADMAP_ID: Final[str] = (
    "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"
)
CONTROLLING_ROADMAP_URL: Final[str] = (
    "https://docs.google.com/document/d/1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"
)

REMOTE_REPOSITORY: Final[str] = "BogaertN/forge2"
REMOTE_URL: Final[str] = (
    "https://github.com/BogaertN/forge2"
)

NEXT_PHASE: Final[str] = (
    "PHASE_1_IMMUTABLE_CORE_CONTRACTS_AND_STATE_IDENTITIES"
)


@dataclass(frozen=True, slots=True)
class EstablishmentStatus:
    schema_version: str
    build_id: str
    forge2_version: str
    phase: str
    acceptance_status: str
    next_phase: str
    next_phase_entry_authorized: bool
    repository_independent: bool
    forge1_runtime_dependency: bool
    product_capability_claimed: bool
    remote_configured: bool
    remote_repository: str
    remote_url: str
    verified_build_branch_ci_status: str
    verified_main_ci_status: str
    branch_protection_status: str
    compensating_controls_status: str
    roadmap_id: str
    roadmap_url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def establishment_status() -> EstablishmentStatus:
    """Return final accepted Phase 0 status."""

    return EstablishmentStatus(
        schema_version=STATUS_SCHEMA_VERSION,
        build_id=BUILD_ID,
        forge2_version=FORGE2_VERSION,
        phase="PHASE_0_ACCEPTED",
        acceptance_status="PASS",
        next_phase=NEXT_PHASE,
        next_phase_entry_authorized=True,
        repository_independent=True,
        forge1_runtime_dependency=False,
        product_capability_claimed=False,
        remote_configured=True,
        remote_repository=REMOTE_REPOSITORY,
        remote_url=REMOTE_URL,
        verified_build_branch_ci_status=(
            "VERIFIED_SUCCESS"
        ),
        verified_main_ci_status="VERIFIED_SUCCESS",
        branch_protection_status=(
            "UNAVAILABLE_FOR_PRIVATE_REPOSITORY_"
            "ON_CURRENT_ACCOUNT_PLAN"
        ),
        compensating_controls_status=(
            "ACTIVE_AND_VERIFIED"
        ),
        roadmap_id=CONTROLLING_ROADMAP_ID,
        roadmap_url=CONTROLLING_ROADMAP_URL,
    )
