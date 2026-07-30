"""Tests for Phase 0 Build 000C-C-B1."""

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
            "FORGE2-PHASE0-BUILD-000C-C-B1",
        )

    def test_independent_repository(self) -> None:
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

    def test_parent_ci_verified(self) -> None:
        self.assertEqual(
            establishment_status()
            .parent_ci_status,
            "VERIFIED_SUCCESS",
        )

    def test_candidate_ci_not_preclaimed(self) -> None:
        self.assertEqual(
            establishment_status()
            .closure_candidate_ci_status,
            "REQUIRED_BEFORE_FINAL_ACCEPTANCE",
        )

    def test_branch_protection_limitation(self) -> None:
        self.assertEqual(
            establishment_status()
            .branch_protection_status,
            (
                "UNAVAILABLE_FOR_PRIVATE_REPOSITORY_"
                "ON_CURRENT_ACCOUNT_PLAN"
            ),
        )

    def test_compensating_controls(self) -> None:
        self.assertEqual(
            establishment_status()
            .compensating_controls_status,
            (
                "BRANCH_FIRST_CI_BEFORE_MAIN_"
                "AND_LOCAL_PRE_PUSH_GATE"
            ),
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
        environment["PYTHONDONTWRITEBYTECODE"] = "1"

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
            "PHASE_0_CLOSURE_CANDIDATE",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
