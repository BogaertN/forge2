#!/usr/bin/env python3
"""Verify the Phase 0 CI parent-history correction."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

BUILD_ID = "FORGE2-PHASE0-BUILD-000C-C-B1-R2"
ORIGINAL_BUILD_ID = (
    "FORGE2-PHASE0-BUILD-000C-C-B1"
)

EXPECTED_PARENT = "e683ffedf26506d8a2490707a89b4dfce5f73611"
EXPECTED_MAIN_PARENT = "d805691e169e52bc00ea9ec674eba706abd3ddda"
EXPECTED_SUBJECT = "Correct Phase 0 CI parent history custody"
EXPECTED_ORIGIN = "https://github.com/BogaertN/forge2.git"

EXPECTED_FAILED_RUN = 30571121938
EXPECTED_FAILED_JOB = 90967820591
EXPECTED_FAILURE = "Commit parent mismatch"

ORIGINAL_VERIFIER = (
    ROOT
    / "scripts"
    / "verify_phase0_closure_candidate.py"
)
WORKFLOW_PATH = (
    ROOT / ".github" / "workflows" / "ci.yml"
)
MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "BUILD_000C_C_B1_SOURCE_AUTHORITY.json"
)
DISPOSITION_PATH = (
    ROOT
    / "receipts"
    / "BUILD_000C_C_B1_PROTECTION_DISPOSITION.json"
)
CORRECTION_PATH = (
    ROOT
    / "receipts"
    / "BUILD_000C_C_B1_R2_CI_CORRECTION.json"
)


class VerificationError(RuntimeError):
    pass


def run(
    arguments: list[str],
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(value, dict):
        raise VerificationError(
            "JSON object required: "
            f"{path.relative_to(ROOT)}"
        )

    return value


def normalize_url(value: str) -> str:
    normalized = value.strip().rstrip("/")

    if normalized.endswith(".git"):
        normalized = normalized[:-4]

    return normalized


def verify_original_candidate() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(
        ROOT / "src"
    )
    environment[
        "PYTHONDONTWRITEBYTECODE"
    ] = "1"

    result = run(
        [
            sys.executable,
            str(ORIGINAL_VERIFIER),
            "--mode",
            "precommit",
        ],
        env=environment,
    )

    if result.returncode != 0:
        raise VerificationError(
            "Updated closure authority failed: "
            + result.stderr.strip()
        )

    payload = json.loads(result.stdout)

    if payload.get("status") != "PASS":
        raise VerificationError(
            "Closure authority is not PASS"
        )


def verify_workflow() -> None:
    workflow = WORKFLOW_PATH.read_text(
        encoding="utf-8"
    )

    if workflow.count(
        "uses: actions/checkout@v4"
    ) != 1:
        raise VerificationError(
            "Unexpected checkout action count"
        )

    if workflow.count(
        "fetch-depth: 2"
    ) != 1:
        raise VerificationError(
            "Workflow must declare fetch-depth 2 "
            "exactly once"
        )

    if "fetch-depth: 0" in workflow:
        raise VerificationError(
            "Unlimited history is not approved"
        )


def verify_manifest() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH)

    if (
        manifest.get("build_id")
        != ORIGINAL_BUILD_ID
    ):
        raise VerificationError(
            "Original manifest identity mismatch"
        )

    if (
        manifest.get(
            "latest_correction_build_id"
        )
        != BUILD_ID
    ):
        raise VerificationError(
            "Correction identity missing "
            "from source authority"
        )

    entries = manifest.get("files")

    if not isinstance(entries, list):
        raise VerificationError(
            "Manifest file entries missing"
        )

    for entry in entries:
        if not isinstance(entry, dict):
            raise VerificationError(
                "Invalid manifest entry"
            )

        relative = entry.get("path")

        if not isinstance(relative, str):
            raise VerificationError(
                "Manifest path must be text"
            )

        path = ROOT / relative

        if not path.is_file():
            raise VerificationError(
                f"Manifest file missing: {relative}"
            )

        if (
            sha256_file(path)
            != entry.get("sha256")
        ):
            raise VerificationError(
                f"Manifest hash mismatch: {relative}"
            )

        if (
            path.stat().st_size
            != entry.get("size_bytes")
        ):
            raise VerificationError(
                f"Manifest size mismatch: {relative}"
            )

    return manifest


def verify_receipts() -> dict[str, Any]:
    disposition = load_json(
        DISPOSITION_PATH
    )
    correction = load_json(
        CORRECTION_PATH
    )

    manifest_hash = sha256_file(
        MANIFEST_PATH
    )

    if (
        disposition.get(
            "source_authority_manifest_sha256"
        )
        != manifest_hash
    ):
        raise VerificationError(
            "Disposition manifest binding mismatch"
        )

    if (
        disposition.get(
            "latest_correction_build_id"
        )
        != BUILD_ID
    ):
        raise VerificationError(
            "Disposition correction mismatch"
        )

    if correction.get("build_id") != BUILD_ID:
        raise VerificationError(
            "Correction receipt identity mismatch"
        )

    if correction.get("status") != "PASS":
        raise VerificationError(
            "Correction receipt is not PASS"
        )

    failed = correction.get(
        "failed_ci_attempt"
    )

    if not isinstance(failed, dict):
        raise VerificationError(
            "Failed CI evidence is missing"
        )

    if (
        failed.get("run_id")
        != EXPECTED_FAILED_RUN
        or failed.get("job_id")
        != EXPECTED_FAILED_JOB
        or failed.get("verifier_error")
        != EXPECTED_FAILURE
    ):
        raise VerificationError(
            "Failed CI evidence mismatch"
        )

    action = correction.get("correction")

    if not isinstance(action, dict):
        raise VerificationError(
            "Correction action is missing"
        )

    if (
        action.get("fetch_depth_before")
        != 1
        or action.get("fetch_depth_after")
        != 2
    ):
        raise VerificationError(
            "Fetch-depth correction mismatch"
        )

    if (
        correction.get(
            "source_authority_manifest_sha256"
        )
        != manifest_hash
    ):
        raise VerificationError(
            "Correction manifest binding mismatch"
        )

    return correction


def verify_git(mode: str) -> dict[str, str]:
    origin = run(
        [
            "git",
            "remote",
            "get-url",
            "origin",
        ]
    )

    if origin.returncode != 0:
        raise VerificationError(
            "Origin is missing"
        )

    if (
        normalize_url(origin.stdout)
        != normalize_url(EXPECTED_ORIGIN)
    ):
        raise VerificationError(
            "Origin mismatch"
        )

    values = {
        "origin": origin.stdout.strip(),
    }

    if mode == "committed":
        status = run(
            [
                "git",
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ]
        )

        if (
            status.returncode != 0
            or status.stdout.strip()
        ):
            raise VerificationError(
                "Committed repository is not clean"
            )

        head = run(
            ["git", "rev-parse", "HEAD"]
        )
        parent = run(
            ["git", "rev-parse", "HEAD^"]
        )
        grandparent = run(
            ["git", "rev-parse", "HEAD^^"]
        )
        subject = run(
            [
                "git",
                "log",
                "-1",
                "--format=%s",
            ]
        )

        if (
            subject.returncode != 0
            or subject.stdout.strip()
            != EXPECTED_SUBJECT
        ):
            raise VerificationError(
                "Correction subject mismatch"
            )

        if (
            parent.returncode != 0
            or parent.stdout.strip()
            != EXPECTED_PARENT
        ):
            raise VerificationError(
                "Correction parent mismatch"
            )

        # HEAD^^ may not exist in a two-commit CI
        # checkout. The direct parent is the required
        # custody proof for this correction.
        if (
            grandparent.returncode == 0
            and grandparent.stdout.strip()
            != EXPECTED_MAIN_PARENT
        ):
            raise VerificationError(
                "Closure candidate parent mismatch"
            )

        values.update(
            {
                "head": head.stdout.strip(),
                "parent": parent.stdout.strip(),
                "subject": subject.stdout.strip(),
            }
        )

    return values


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        choices=(
            "source",
            "precommit",
            "committed",
        ),
        required=True,
    )

    arguments = parser.parse_args()

    verify_original_candidate()
    verify_workflow()
    manifest = verify_manifest()
    correction = verify_receipts()
    git_state = verify_git(arguments.mode)

    result = {
        "schema_version": (
            "aiweb_forge2_phase0_"
            "ci_history_correction_verification_v1"
        ),
        "build_id": BUILD_ID,
        "mode": arguments.mode,
        "status": "PASS",
        "manifest_file_count": len(
            manifest["files"]
        ),
        "failed_run_preserved": (
            correction[
                "failed_ci_attempt"
            ]["run_id"]
        ),
        "checkout_fetch_depth": 2,
        "git": git_state,
    }

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            json.dumps(
                {
                    "build_id": BUILD_ID,
                    "status": "FAIL",
                    "error": str(error),
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)
