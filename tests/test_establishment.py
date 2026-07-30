"""Acceptance tests for Phase 0 Build 000C-B."""

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
            "FORGE2-PHASE0-BUILD-000C-B",
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

    def test_no_product_capability_is_claimed(self) -> None:
        self.assertIs(
            establishment_status()
            .product_capability_claimed,
            False,
        )

    def test_private_remote_identity(self) -> None:
        status = establishment_status()

        self.assertIs(
            status.remote_configured,
            True,
        )
        self.assertEqual(
            status.remote_repository,
            "BogaertN/forge2",
        )
        self.assertEqual(
            status.remote_url,
            "https://github.com/BogaertN/forge2",
        )

    def test_phase_zero_remains_open(self) -> None:
        status = establishment_status()

        self.assertEqual(
            status.ci_status,
            "PENDING_REMOTE_RUN_INSPECTION",
        )
        self.assertEqual(
            status.branch_protection_status,
            "PENDING_BUILD_000C_C",
        )

    def test_controlling_roadmap_identity(self) -> None:
        self.assertEqual(
            establishment_status().roadmap_id,
            "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0",
        )

    def test_module_runs_independently(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(
            ROOT / "src"
        )
        environment["PYTHONDONTWRITEBYTECODE"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "forge2"],
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
            payload["build_id"],
            BUILD_ID,
        )
        self.assertIs(
            payload["remote_configured"],
            True,
        )
        self.assertIs(
            payload["product_capability_claimed"],
            False,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
