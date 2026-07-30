"""Phase 0 closure-candidate identity.

This module reports establishment state only.
It does not provide a product capability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Final


BUILD_ID: Final[str] = "FORGE2-PHASE0-BUILD-000C-C-B1"
FORGE2_VERSION: Final[str] = "0.0.0"

STATUS_SCHEMA_VERSION: Final[str] = (
    "aiweb_forge2_establishment_status_v3"
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


@dataclass(frozen=True, slots=True)
class EstablishmentStatus:
    schema_version: str
    build_id: str
    forge2_version: str
    phase: str
    repository_independent: bool
    forge1_runtime_dependency: bool
    product_capability_claimed: bool
    remote_configured: bool
    remote_repository: str
    remote_url: str
    parent_ci_status: str
    closure_candidate_ci_status: str
    branch_protection_status: str
    compensating_controls_status: str
    roadmap_id: str
    roadmap_url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def establishment_status() -> EstablishmentStatus:
    """Return Phase 0 closure-candidate status."""

    return EstablishmentStatus(
        schema_version=STATUS_SCHEMA_VERSION,
        build_id=BUILD_ID,
        forge2_version=FORGE2_VERSION,
        phase="PHASE_0_CLOSURE_CANDIDATE",
        repository_independent=True,
        forge1_runtime_dependency=False,
        product_capability_claimed=False,
        remote_configured=True,
        remote_repository=REMOTE_REPOSITORY,
        remote_url=REMOTE_URL,
        parent_ci_status="VERIFIED_SUCCESS",
        closure_candidate_ci_status=(
            "REQUIRED_BEFORE_FINAL_ACCEPTANCE"
        ),
        branch_protection_status=(
            "UNAVAILABLE_FOR_PRIVATE_REPOSITORY_"
            "ON_CURRENT_ACCOUNT_PLAN"
        ),
        compensating_controls_status=(
            "BRANCH_FIRST_CI_BEFORE_MAIN_"
            "AND_LOCAL_PRE_PUSH_GATE"
        ),
        roadmap_id=CONTROLLING_ROADMAP_ID,
        roadmap_url=CONTROLLING_ROADMAP_URL,
    )
