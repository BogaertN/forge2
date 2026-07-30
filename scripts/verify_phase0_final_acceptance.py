#!/usr/bin/env python3
"""Verify final Forge 2.0 Phase 0 acceptance."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

BUILD_ID = "FORGE2-PHASE0-BUILD-000C-C-B3"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"
EXPECTED_PARENT = "2175de8f82c0526e2034533abd4d495f9ca3ed14"
EXPECTED_SUBJECT = "Accept Phase 0 clean establishment"
EXPECTED_ORIGIN = "https://github.com/BogaertN/forge2.git"
NEXT_PHASE = "PHASE_1_IMMUTABLE_CORE_CONTRACTS_AND_STATE_IDENTITIES"

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE_0_FINAL_ACCEPTANCE_SOURCE_AUTHORITY.json"
)
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE_0_FINAL_ACCEPTANCE_RECEIPT.json"
)

REQUIRED_HISTORICAL_EVIDENCE = (
    "receipts/"
    "BUILD_000C_C_B1_PROTECTION_DISPOSITION.json",
    "receipts/"
    "BUILD_000C_C_B1_R2_CI_CORRECTION.json",
    "scripts/"
    "verify_phase0_ci_history_correction.py",
    "docs/decisions/"
    "ADR-0003-BRANCH-PROTECTION-DISPOSITION.md",
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
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception as error:
        raise VerificationError(
            "Invalid JSON "
            f"{path.relative_to(ROOT)}: {error}"
        ) from error

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


def verify_historical_evidence() -> None:
    missing = [
        relative
        for relative in REQUIRED_HISTORICAL_EVIDENCE
        if not (ROOT / relative).is_file()
    ]

    if missing:
        raise VerificationError(
            "Historical Phase 0 evidence missing: "
            + ", ".join(sorted(missing))
        )


def verify_python_boundaries() -> int:
    count = 0

    for source_root in (
        ROOT / "src",
        ROOT / "tests",
        ROOT / "scripts",
        ROOT / ".githooks",
    ):
        for path in sorted(
            source_root.rglob("*.py")
        ):
            source = path.read_text(
                encoding="utf-8"
            )

            try:
                tree = ast.parse(
                    source,
                    filename=str(path),
                )
            except SyntaxError as error:
                raise VerificationError(
                    "Syntax error in "
                    f"{path.relative_to(ROOT)}: "
                    f"{error}"
                ) from error

            if source_root in {
                ROOT / "src",
                ROOT / "tests",
            }:
                for node in ast.walk(tree):
                    roots: list[str] = []

                    if isinstance(node, ast.Import):
                        roots = [
                            alias.name.split(".", 1)[0]
                            for alias in node.names
                        ]

                    if isinstance(node, ast.ImportFrom):
                        roots = [
                            (node.module or "")
                            .split(".", 1)[0]
                        ]

                    if any(
                        root in {
                            "main",
                            "rmc_engine_v1",
                        }
                        for root in roots
                    ):
                        raise VerificationError(
                            "Forge 1 runtime import found in "
                            f"{path.relative_to(ROOT)}"
                        )

            count += 1

    return count


def verify_workflow_and_hook() -> None:
    workflow = (
        ROOT
        / ".github"
        / "workflows"
        / "ci.yml"
    ).read_text(encoding="utf-8")

    if workflow.count(
        "uses: actions/checkout@v4"
    ) != 1:
        raise VerificationError(
            "Unexpected checkout action count"
        )

    if workflow.count("fetch-depth: 2") != 1:
        raise VerificationError(
            "Workflow must retain fetch-depth 2"
        )

    hook = ROOT / ".githooks" / "pre-push"

    if not hook.is_file():
        raise VerificationError(
            "Tracked pre-push hook is missing"
        )

    if not os.access(hook, os.X_OK):
        raise VerificationError(
            "Tracked pre-push hook is not executable"
        )


def verify_manifest() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH)

    if manifest.get("build_id") != BUILD_ID:
        raise VerificationError(
            "Manifest build identity mismatch"
        )

    if (
        manifest.get("expected_parent")
        != EXPECTED_PARENT
    ):
        raise VerificationError(
            "Manifest parent mismatch"
        )

    roadmap = manifest.get(
        "controlling_roadmap"
    )

    if not isinstance(roadmap, dict):
        raise VerificationError(
            "Manifest roadmap missing"
        )

    if roadmap.get("document_id") != ROADMAP_ID:
        raise VerificationError(
            "Manifest roadmap identity mismatch"
        )

    entries = manifest.get("files")

    if not isinstance(entries, list) or not entries:
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


def verify_receipt() -> dict[str, Any]:
    receipt = load_json(RECEIPT_PATH)

    if receipt.get("build_id") != BUILD_ID:
        raise VerificationError(
            "Acceptance receipt identity mismatch"
        )

    if receipt.get("status") != "PASS":
        raise VerificationError(
            "Acceptance receipt is not PASS"
        )

    if receipt.get("accepted_phase") != "PHASE_0":
        raise VerificationError(
            "Accepted phase mismatch"
        )

    if (
        receipt.get("next_phase")
        != NEXT_PHASE
    ):
        raise VerificationError(
            "Next phase mismatch"
        )

    if (
        receipt.get(
            "next_phase_entry_authorized"
        )
        is not True
    ):
        raise VerificationError(
            "Phase 1 entry is not authorized"
        )

    if (
        receipt.get("forge1_modified")
        is not False
    ):
        raise VerificationError(
            "Forge 1 preservation mismatch"
        )

    if (
        receipt.get(
            "repository_independent"
        )
        is not True
    ):
        raise VerificationError(
            "Repository independence mismatch"
        )

    if (
        receipt.get(
            "repository_remains_private"
        )
        is not True
    ):
        raise VerificationError(
            "Repository visibility mismatch"
        )

    if (
        receipt.get(
            "product_capability_claimed"
        )
        is not False
    ):
        raise VerificationError(
            "Receipt claims a product capability"
        )

    if (
        receipt.get(
            "source_authority_manifest_sha256"
        )
        != sha256_file(MANIFEST_PATH)
    ):
        raise VerificationError(
            "Receipt manifest binding mismatch"
        )

    return receipt


def verify_package() -> dict[str, Any]:
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
            "-m",
            "forge2",
        ],
        env=environment,
    )

    if result.returncode != 0:
        raise VerificationError(
            "Forge 2 establishment package failed: "
            + result.stderr.strip()
        )

    payload = json.loads(result.stdout)

    if payload.get("build_id") != BUILD_ID:
        raise VerificationError(
            "Package build identity mismatch"
        )

    if payload.get("phase") != "PHASE_0_ACCEPTED":
        raise VerificationError(
            "Package Phase 0 status mismatch"
        )

    if payload.get("acceptance_status") != "PASS":
        raise VerificationError(
            "Package acceptance mismatch"
        )

    if (
        payload.get(
            "next_phase_entry_authorized"
        )
        is not True
    ):
        raise VerificationError(
            "Package Phase 1 authority mismatch"
        )

    if (
        payload.get(
            "product_capability_claimed"
        )
        is not False
    ):
        raise VerificationError(
            "Package claims a product capability"
        )

    return payload


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
                "Acceptance commit subject mismatch"
            )

        if (
            parent.returncode != 0
            or parent.stdout.strip()
            != EXPECTED_PARENT
        ):
            raise VerificationError(
                "Acceptance commit parent mismatch"
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

    verify_historical_evidence()
    source_count = verify_python_boundaries()
    verify_workflow_and_hook()
    manifest = verify_manifest()
    receipt = verify_receipt()
    package = verify_package()
    git_state = verify_git(arguments.mode)

    result = {
        "schema_version": (
            "aiweb_forge2_phase0_"
            "final_acceptance_verification_v1"
        ),
        "build_id": BUILD_ID,
        "mode": arguments.mode,
        "status": "PASS",
        "accepted_phase": "PHASE_0",
        "next_phase": NEXT_PHASE,
        "next_phase_entry_authorized": True,
        "python_source_count": source_count,
        "manifest_file_count": len(
            manifest["files"]
        ),
        "receipt_status": receipt["status"],
        "package": package,
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
