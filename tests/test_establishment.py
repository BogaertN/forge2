"""Tests for final Phase 0 acceptance."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from forge2 import BUILD_ID, establishment_status


ROOT = Path(__file__).resolve().parents[1]


class EstablishmentTests(unittest.TestCase):
    def test_build_identity(self) -> None:
        self.assertEqual(
            BUILD_ID,
            "FORGE2-PHASE0-BUILD-000C-C-B3",
        )

    def test_phase_zero_is_accepted(self) -> None:
        status = establishment_status()

        self.assertEqual(
            status.phase,
            "PHASE_0_ACCEPTED",
        )
        self.assertEqual(
            status.acceptance_status,
            "PASS",
        )

    def test_phase_one_entry_is_authorized(self) -> None:
        status = establishment_status()

        self.assertIs(
            status.next_phase_entry_authorized,
            True,
        )
        self.assertEqual(
            status.next_phase,
            "PHASE_1_IMMUTABLE_CORE_CONTRACTS_AND_STATE_IDENTITIES",
        )

    def test_repository_is_independent(self) -> None:
        status = establishment_status()

        self.assertIs(
            status.repository_independent,
            True,
        )
        self.assertIs(
            status.forge1_runtime_dependency,
            False,
        )

    def test_no_product_capability_claim(self) -> None:
        self.assertIs(
            establishment_status()
            .product_capability_claimed,
            False,
        )

    def test_remote_is_established(self) -> None:
        status = establishment_status()

        self.assertIs(
            status.remote_configured,
            True,
        )
        self.assertEqual(
            status.remote_repository,
            "BogaertN/forge2",
        )

    def test_ci_is_verified(self) -> None:
        status = establishment_status()

        self.assertEqual(
            status.verified_build_branch_ci_status,
            "VERIFIED_SUCCESS",
        )
        self.assertEqual(
            status.verified_main_ci_status,
            "VERIFIED_SUCCESS",
        )

    def test_protection_disposition_is_honest(self) -> None:
        self.assertEqual(
            establishment_status()
            .branch_protection_status,
            (
                "UNAVAILABLE_FOR_PRIVATE_REPOSITORY_"
                "ON_CURRENT_ACCOUNT_PLAN"
            ),
        )

    def test_compensating_controls_are_active(self) -> None:
        self.assertEqual(
            establishment_status()
            .compensating_controls_status,
            "ACTIVE_AND_VERIFIED",
        )

    def test_roadmap_identity(self) -> None:
        self.assertEqual(
            establishment_status().roadmap_id,
            "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0",
        )

    def test_module_execution(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(
            ROOT / "src"
        )
        environment[
            "PYTHONDONTWRITEBYTECODE"
        ] = "1"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "forge2",
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stderr,
        )

        payload = json.loads(result.stdout)

        self.assertEqual(
            payload["phase"],
            "PHASE_0_ACCEPTED",
        )
        self.assertIs(
            payload["next_phase_entry_authorized"],
            True,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
