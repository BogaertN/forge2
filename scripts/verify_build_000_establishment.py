#!/usr/bin/env python3
"""Independent verifier for Phase 0 Build 000B."""

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
BUILD_ID = "FORGE2-PHASE0-BUILD-000B"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"
EXPECTED_COMMIT_SUBJECT = (
    "Establish independent Forge 2.0 production repository"
)

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "BUILD_000B_SOURCE_AUTHORITY.json"
)
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "BUILD_000B_ESTABLISHMENT_RECEIPT.json"
)

REQUIRED_PATHS = (
    ".github/workflows/ci.yml",
    ".gitignore",
    "CONTRIBUTING.md",
    "README.md",
    "SECURITY.md",
    "docs/architecture/SYSTEM_BOUNDARY.md",
    "docs/decisions/ADR-0001-INDEPENDENT-FORGE2-REPOSITORY.md",
    "docs/operations/REMOTE_AND_BRANCH_PROTECTION_PENDING.md",
    "docs/policies/CODING_STANDARDS.md",
    "docs/policies/FORGE1_DONOR_POLICY.md",
    "docs/policies/LICENSE_DECISION.md",
    "docs/policies/NO_LLM_AND_ML_BOUNDARY.md",
    "docs/policies/OPEN_SOURCE_FIRST_POLICY.md",
    "docs/roadmap/CONTROLLING_ROADMAP_REFERENCE.md",
    "manifests/BUILD_000B_SOURCE_AUTHORITY.json",
    "pyproject.toml",
    "scripts/verify_build_000_establishment.py",
    "src/forge2/__init__.py",
    "src/forge2/__main__.py",
    "src/forge2/establishment.py",
    "tests/test_establishment.py",
)


class VerificationError(RuntimeError):
    """Raised when Build 000B verification fails."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


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


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception as error:
        raise VerificationError(
            f"Invalid JSON: {path.relative_to(ROOT)}: {error}"
        ) from error

    if not isinstance(value, dict):
        raise VerificationError(
            f"JSON object required: {path.relative_to(ROOT)}"
        )

    return value


def verify_required_paths() -> None:
    missing = [
        relative
        for relative in REQUIRED_PATHS
        if not (ROOT / relative).is_file()
    ]

    if missing:
        raise VerificationError(
            "Missing required paths: "
            + ", ".join(sorted(missing))
        )


def verify_no_forge1_runtime_imports() -> None:
    source_roots = (
        ROOT / "src",
        ROOT / "tests",
    )

    forbidden_modules = {
        "main",
        "rmc_engine_v1",
    }

    for source_root in source_roots:
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
                    f"Syntax error in {path.relative_to(ROOT)}: "
                    f"{error}"
                ) from error

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_module = alias.name.split(
                            ".",
                            1,
                        )[0]

                        if root_module in forbidden_modules:
                            raise VerificationError(
                                "Forge 1 runtime import found in "
                                f"{path.relative_to(ROOT)}"
                            )

                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    root_module = module.split(
                        ".",
                        1,
                    )[0]

                    if root_module in forbidden_modules:
                        raise VerificationError(
                            "Forge 1 runtime import found in "
                            f"{path.relative_to(ROOT)}"
                        )

            if "/home/nic/" + "forge" in source:
                raise VerificationError(
                    "Forge 1 absolute runtime path found in "
                    f"{path.relative_to(ROOT)}"
                )


def verify_manifest() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH)

    if manifest.get("build_id") != BUILD_ID:
        raise VerificationError(
            "Source manifest build identity mismatch"
        )

    roadmap = manifest.get("controlling_roadmap")

    if not isinstance(roadmap, dict):
        raise VerificationError(
            "Source manifest roadmap object missing"
        )

    if roadmap.get("document_id") != ROADMAP_ID:
        raise VerificationError(
            "Source manifest roadmap identity mismatch"
        )

    entries = manifest.get("files")

    if not isinstance(entries, list) or not entries:
        raise VerificationError(
            "Source manifest files are missing"
        )

    observed_paths: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            raise VerificationError(
                "Invalid source manifest file entry"
            )

        relative = entry.get("path")
        expected_hash = entry.get("sha256")
        expected_size = entry.get("size_bytes")

        if not isinstance(relative, str):
            raise VerificationError(
                "Manifest path must be text"
            )

        path = ROOT / relative

        if not path.is_file():
            raise VerificationError(
                f"Manifest file missing: {relative}"
            )

        observed_hash = sha256_file(path)
        observed_size = path.stat().st_size

        if observed_hash != expected_hash:
            raise VerificationError(
                f"Manifest hash mismatch: {relative}"
            )

        if observed_size != expected_size:
            raise VerificationError(
                f"Manifest size mismatch: {relative}"
            )

        observed_paths.add(relative)

    required_manifest_entries = {
        relative
        for relative in REQUIRED_PATHS
        if relative
        not in {
            str(MANIFEST_PATH.relative_to(ROOT)),
        }
    }

    missing_entries = sorted(
        required_manifest_entries - observed_paths
    )

    if missing_entries:
        raise VerificationError(
            "Required source paths absent from manifest: "
            + ", ".join(missing_entries)
        )

    return manifest


def verify_package_execution() -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    result = run(
        [sys.executable, "-m", "forge2"],
        env=environment,
    )

    if result.returncode != 0:
        raise VerificationError(
            "Forge 2 establishment package did not run: "
            + result.stderr.strip()
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise VerificationError(
            "Forge 2 establishment output is not JSON"
        ) from error

    if payload.get("build_id") != BUILD_ID:
        raise VerificationError(
            "Forge 2 package build identity mismatch"
        )

    if payload.get("repository_independent") is not True:
        raise VerificationError(
            "Forge 2 independent-repository claim missing"
        )

    if payload.get("forge1_runtime_dependency") is not False:
        raise VerificationError(
            "Forge 1 runtime dependency is not prohibited"
        )

    if payload.get("product_capability_claimed") is not False:
        raise VerificationError(
            "Build 000B improperly claims a product capability"
        )

    if payload.get("remote_configured") is not False:
        raise VerificationError(
            "Build 000B incorrectly claims a configured remote"
        )

    return payload


def verify_receipt() -> dict[str, Any]:
    if not RECEIPT_PATH.is_file():
        raise VerificationError(
            "Establishment receipt is missing"
        )

    receipt = load_json(RECEIPT_PATH)

    if receipt.get("build_id") != BUILD_ID:
        raise VerificationError(
            "Establishment receipt identity mismatch"
        )

    if receipt.get("status") != "PASS":
        raise VerificationError(
            "Establishment receipt is not PASS"
        )

    if receipt.get("product_capability_claimed") is not False:
        raise VerificationError(
            "Receipt improperly claims a product capability"
        )

    if receipt.get("forge1_modified") is not False:
        raise VerificationError(
            "Receipt does not preserve Forge 1"
        )

    if receipt.get("remote_configured") is not False:
        raise VerificationError(
            "Receipt remote state is incorrect"
        )

    expected_manifest_hash = receipt.get(
        "source_authority_manifest_sha256"
    )

    if expected_manifest_hash != sha256_file(MANIFEST_PATH):
        raise VerificationError(
            "Receipt source-manifest binding mismatch"
        )

    return receipt


def verify_git(mode: str) -> dict[str, str]:
    branch_result = run(
        ["git", "branch", "--show-current"]
    )

    if branch_result.returncode != 0:
        raise VerificationError(
            "Could not inspect Git branch"
        )

    branch = branch_result.stdout.strip()

    if branch != "main":
        raise VerificationError(
            f"Expected main branch, observed {branch!r}"
        )

    remote_result = run(["git", "remote"])

    if remote_result.returncode != 0:
        raise VerificationError(
            "Could not inspect Git remotes"
        )

    if remote_result.stdout.strip():
        raise VerificationError(
            "Build 000B must not configure a remote"
        )

    values = {
        "branch": branch,
        "remote_state": "NONE",
    }

    if mode == "committed":
        head_result = run(
            ["git", "rev-parse", "HEAD"]
        )

        if head_result.returncode != 0:
            raise VerificationError(
                "Committed mode requires a Git commit"
            )

        subject_result = run(
            [
                "git",
                "log",
                "-1",
                "--format=%s",
            ]
        )

        if subject_result.returncode != 0:
            raise VerificationError(
                "Could not inspect commit subject"
            )

        subject = subject_result.stdout.strip()

        if subject != EXPECTED_COMMIT_SUBJECT:
            raise VerificationError(
                "Unexpected initial commit subject: "
                f"{subject!r}"
            )

        status_result = run(
            [
                "git",
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ]
        )

        if status_result.returncode != 0:
            raise VerificationError(
                "Could not inspect committed status"
            )

        if status_result.stdout.strip():
            raise VerificationError(
                "Committed repository is not clean"
            )

        values["head"] = head_result.stdout.strip()
        values["subject"] = subject

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

    verify_required_paths()
    verify_no_forge1_runtime_imports()
    manifest = verify_manifest()
    package = verify_package_execution()
    git_state = verify_git(arguments.mode)

    receipt: dict[str, Any] | None = None

    if arguments.mode in {
        "precommit",
        "committed",
    }:
        receipt = verify_receipt()

    result = {
        "schema_version": (
            "aiweb_forge2_build000b_verification_v1"
        ),
        "build_id": BUILD_ID,
        "mode": arguments.mode,
        "status": "PASS",
        "manifest_file_count": len(
            manifest["files"]
        ),
        "package": package,
        "git": git_state,
        "receipt_verified": receipt is not None,
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
    except VerificationError as error:
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
