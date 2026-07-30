#!/usr/bin/env python3
"""Verify Phase 0 Build 000C-C-B1."""

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

BUILD_ID = "FORGE2-PHASE0-BUILD-000C-C-B1"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"
EXPECTED_PARENT = "d805691e169e52bc00ea9ec674eba706abd3ddda"
EXPECTED_ORIGIN = "https://github.com/BogaertN/forge2.git"
EXPECTED_SUBJECT = "Record Phase 0 CI and branch protection disposition"

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "BUILD_000C_C_B1_SOURCE_AUTHORITY.json"
)

RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "BUILD_000C_C_B1_PROTECTION_DISPOSITION.json"
)


class VerificationError(RuntimeError):
    pass


def run(
    arguments: list[str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=ROOT,
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


def normalize_url(value: str) -> str:
    normalized = value.strip().rstrip("/")

    if normalized.endswith(".git"):
        normalized = normalized[:-4]

    return normalized


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


def verify_python() -> int:
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

            for node in ast.walk(tree):
                names: list[str] = []

                if isinstance(node, ast.Import):
                    names = [
                        alias.name.split(".", 1)[0]
                        for alias in node.names
                    ]

                if isinstance(node, ast.ImportFrom):
                    names = [
                        (node.module or "")
                        .split(".", 1)[0]
                    ]

                if any(
                    name in {
                        "main",
                        "rmc_engine_v1",
                    }
                    for name in names
                ):
                    raise VerificationError(
                        "Forge 1 runtime import found in "
                        f"{path.relative_to(ROOT)}"
                    )

            count += 1

    return count


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
            "Manifest roadmap mismatch"
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
            "Receipt build identity mismatch"
        )

    if receipt.get("status") != "PASS":
        raise VerificationError(
            "Receipt status is not PASS"
        )

    if receipt.get("forge1_modified") is not False:
        raise VerificationError(
            "Receipt does not preserve Forge 1"
        )

    if (
        receipt.get("product_capability_claimed")
        is not False
    ):
        raise VerificationError(
            "Receipt claims a product capability"
        )

    if (
        receipt.get(
            "server_branch_protection_status"
        )
        != "UNAVAILABLE_CURRENT_ACCOUNT_PLAN"
    ):
        raise VerificationError(
            "Protection disposition mismatch"
        )

    if (
        receipt.get("repository_remains_private")
        is not True
    ):
        raise VerificationError(
            "Private repository state mismatch"
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

    if result.returncode != 0:
        raise VerificationError(
            "Forge 2 package failed"
        )

    payload = json.loads(result.stdout)

    if payload.get("build_id") != BUILD_ID:
        raise VerificationError(
            "Package build mismatch"
        )

    if (
        payload.get("phase")
        != "PHASE_0_CLOSURE_CANDIDATE"
    ):
        raise VerificationError(
            "Package phase mismatch"
        )

    if (
        payload.get(
            "product_capability_claimed"
        )
        is not False
    ):
        raise VerificationError(
            "Package claims a capability"
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
                "Commit subject mismatch"
            )

        parent = run(
            [
                "git",
                "rev-parse",
                "HEAD^",
            ]
        )

        if (
            parent.returncode != 0
            or parent.stdout.strip()
            != EXPECTED_PARENT
        ):
            raise VerificationError(
                "Commit parent mismatch"
            )

        head = run(
            [
                "git",
                "rev-parse",
                "HEAD",
            ]
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

    source_count = verify_python()
    manifest = verify_manifest()
    package = verify_package()

    receipt = None

    if arguments.mode in {
        "precommit",
        "committed",
    }:
        receipt = verify_receipt()

    git_state = verify_git(arguments.mode)

    result = {
        "schema_version": (
            "aiweb_forge2_phase0_"
            "closure_candidate_verification_v1"
        ),
        "build_id": BUILD_ID,
        "mode": arguments.mode,
        "status": "PASS",
        "python_source_count": source_count,
        "manifest_file_count": len(
            manifest["files"]
        ),
        "receipt_verified": (
            receipt is not None
        ),
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
