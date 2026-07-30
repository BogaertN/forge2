"""Phase 0 establishment identity.

This module reports repository-establishment state only. It does not
provide a product capability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Final


BUILD_ID: Final[str] = "FORGE2-PHASE0-BUILD-000B"
FORGE2_VERSION: Final[str] = "0.0.0"
STATUS_SCHEMA_VERSION: Final[str] = (
    "aiweb_forge2_establishment_status_v1"
)
CONTROLLING_ROADMAP_ID: Final[str] = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"
CONTROLLING_ROADMAP_URL: Final[str] = "https://docs.google.com/document/d/1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"


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
    roadmap_id: str
    roadmap_url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def establishment_status() -> EstablishmentStatus:
    """Return immutable Phase 0 repository-establishment status."""

    return EstablishmentStatus(
        schema_version=STATUS_SCHEMA_VERSION,
        build_id=BUILD_ID,
        forge2_version=FORGE2_VERSION,
        phase="PHASE_0_LOCAL_ESTABLISHMENT",
        repository_independent=True,
        forge1_runtime_dependency=False,
        product_capability_claimed=False,
        remote_configured=False,
        roadmap_id=CONTROLLING_ROADMAP_ID,
        roadmap_url=CONTROLLING_ROADMAP_URL,
    )
