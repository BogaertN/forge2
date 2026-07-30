#!/usr/bin/env python3
"""Independent verifier for Phase 0 Build 000C-B."""

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

BUILD_ID = "FORGE2-PHASE0-BUILD-000C-B"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"
EXPECTED_REMOTE_REPOSITORY = "BogaertN/forge2"
EXPECTED_REMOTE_URL = "https://github.com/BogaertN/forge2"
EXPECTED_COMMIT_SUBJECT = "Establish private Forge 2.0 GitHub remote"

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "BUILD_000C_B_SOURCE_AUTHORITY.json"
)
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "BUILD_000C_B_REMOTE_ESTABLISHMENT_RECEIPT.json"
)


class VerificationError(RuntimeError):
    """Raised when Build 000C-B verification fails."""


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


def normalize_url(value: str) -> str:
    normalized = value.strip().rstrip("/")

    if normalized.endswith(".git"):
        normalized = normalized[:-4]

    return normalized


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


def verify_python_sources() -> int:
    count = 0

    for source_root in (
        ROOT / "src",
        ROOT / "tests",
        ROOT / "scripts",
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
                    f"Syntax error in {path.relative_to(ROOT)}: "
                    f"{error}"
                ) from error

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_name = alias.name.split(
                            ".",
                            1,
                        )[0]

                        if root_name in {
                            "main",
                            "rmc_engine_v1",
                        }:
                            raise VerificationError(
                                "Forge 1 runtime import found in "
                                f"{path.relative_to(ROOT)}"
                            )

                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    root_name = module.split(
                        ".",
                        1,
                    )[0]

                    if root_name in {
                        "main",
                        "rmc_engine_v1",
                    }:
                        raise VerificationError(
                            "Forge 1 runtime import found in "
                            f"{path.relative_to(ROOT)}"
                        )

            if "/home/nic/" + "forge" in source:
                raise VerificationError(
                    "Forge 1 absolute runtime path found in "
                    f"{path.relative_to(ROOT)}"
                )

            count += 1

    return count


def verify_manifest() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH)

    if manifest.get("build_id") != BUILD_ID:
        raise VerificationError(
            "Source manifest build identity mismatch"
        )

    roadmap = manifest.get("controlling_roadmap")

    if not isinstance(roadmap, dict):
        raise VerificationError(
            "Source manifest roadmap is missing"
        )

    if roadmap.get("document_id") != ROADMAP_ID:
        raise VerificationError(
            "Source manifest roadmap identity mismatch"
        )

    entries = manifest.get("files")

    if not isinstance(entries, list) or not entries:
        raise VerificationError(
            "Source manifest file entries are missing"
        )

    for entry in entries:
        if not isinstance(entry, dict):
            raise VerificationError(
                "Invalid manifest file entry"
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

        if sha256_file(path) != expected_hash:
            raise VerificationError(
                f"Manifest hash mismatch: {relative}"
            )

        if path.stat().st_size != expected_size:
            raise VerificationError(
                f"Manifest size mismatch: {relative}"
            )

    return manifest


def verify_package() -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    result = run(
        [sys.executable, "-m", "forge2"],
        env=environment,
    )

    if result.returncode != 0:
        raise VerificationError(
            "Forge 2 establishment package failed: "
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
            "Forge 2 build identity mismatch"
        )

    if payload.get("repository_independent") is not True:
        raise VerificationError(
            "Repository independence is not asserted"
        )

    if payload.get("forge1_runtime_dependency") is not False:
        raise VerificationError(
            "Forge 1 runtime dependency is not prohibited"
        )

    if payload.get("product_capability_claimed") is not False:
        raise VerificationError(
            "Build 000C-B claims a product capability"
        )

    if payload.get("remote_configured") is not True:
        raise VerificationError(
            "Remote configuration state is not established"
        )

    if (
        payload.get("remote_repository")
        != EXPECTED_REMOTE_REPOSITORY
    ):
        raise VerificationError(
            "Remote repository identity mismatch"
        )

    if (
        normalize_url(str(payload.get("remote_url", "")))
        != normalize_url(EXPECTED_REMOTE_URL)
    ):
        raise VerificationError(
            "Remote URL identity mismatch"
        )

    return payload


def verify_receipt() -> dict[str, Any]:
    receipt = load_json(RECEIPT_PATH)

    if receipt.get("build_id") != BUILD_ID:
        raise VerificationError(
            "Remote receipt build identity mismatch"
        )

    if receipt.get("status") != "PASS":
        raise VerificationError(
            "Remote receipt is not PASS"
        )

    if receipt.get("remote_created") is not True:
        raise VerificationError(
            "Remote receipt does not record creation"
        )

    if receipt.get("remote_visibility") != "PRIVATE":
        raise VerificationError(
            "Remote repository is not recorded as private"
        )

    if (
        receipt.get("remote_repository")
        != EXPECTED_REMOTE_REPOSITORY
    ):
        raise VerificationError(
            "Remote receipt repository mismatch"
        )

    if receipt.get("forge1_modified") is not False:
        raise VerificationError(
            "Remote receipt does not preserve Forge 1"
        )

    if receipt.get("product_capability_claimed") is not False:
        raise VerificationError(
            "Remote receipt claims a product capability"
        )

    expected_manifest_hash = receipt.get(
        "source_authority_manifest_sha256"
    )

    if expected_manifest_hash != sha256_file(MANIFEST_PATH):
        raise VerificationError(
            "Remote receipt manifest binding mismatch"
        )

    return receipt


def verify_git(mode: str) -> dict[str, Any]:
    values: dict[str, Any] = {}

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
            "Could not inspect Git status"
        )

    if mode == "remote" and status_result.stdout.strip():
        raise VerificationError(
            "Forge 2 repository is not clean"
        )

    if mode in {"precommit", "remote"}:
        remote_result = run(
            [
                "git",
                "remote",
                "get-url",
                "origin",
            ]
        )

        if remote_result.returncode != 0:
            raise VerificationError(
                "Required origin remote is missing"
            )

        observed_remote = remote_result.stdout.strip()

        if (
            normalize_url(observed_remote)
            != normalize_url(EXPECTED_REMOTE_URL)
        ):
            raise VerificationError(
                "Unexpected origin URL: "
                f"{observed_remote!r}"
            )

        values["origin"] = observed_remote

    if mode == "remote":
        head_result = run(
            ["git", "rev-parse", "HEAD"]
        )
        subject_result = run(
            [
                "git",
                "log",
                "-1",
                "--format=%s",
            ]
        )

        if (
            head_result.returncode != 0
            or subject_result.returncode != 0
        ):
            raise VerificationError(
                "Could not inspect committed state"
            )

        subject = subject_result.stdout.strip()

        if subject != EXPECTED_COMMIT_SUBJECT:
            raise VerificationError(
                "Unexpected commit subject: "
                f"{subject!r}"
            )

        if (
            os.environ.get("GITHUB_ACTIONS")
            != "true"
        ):
            branch_result = run(
                ["git", "branch", "--show-current"]
            )

            if (
                branch_result.returncode != 0
                or branch_result.stdout.strip() != "main"
            ):
                raise VerificationError(
                    "Local remote verification "
                    "requires main branch"
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
            "remote",
        ),
        required=True,
    )
    arguments = parser.parse_args()

    source_count = verify_python_sources()
    manifest = verify_manifest()
    package = verify_package()

    receipt: dict[str, Any] | None = None

    if arguments.mode in {
        "precommit",
        "remote",
    }:
        receipt = verify_receipt()

    git_state = verify_git(arguments.mode)

    result = {
        "schema_version": (
            "aiweb_forge2_build000cb_verification_v1"
        ),
        "build_id": BUILD_ID,
        "mode": arguments.mode,
        "status": "PASS",
        "python_source_count": source_count,
        "manifest_file_count": len(
            manifest["files"]
        ),
        "receipt_verified": receipt is not None,
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
