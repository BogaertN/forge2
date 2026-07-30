#!/usr/bin/env python3
"""Verify Phase 1 Build 002A."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

BUILD_ID = "FORGE2-PHASE1-BUILD-002A"
EXPECTED_PARENT = "270a72674af92f81bad307a1dc926866eeadcdba"
EXPECTED_SUBJECT = "Establish canonical contract serialization"
EXPECTED_ORIGIN = "https://github.com/BogaertN/forge2.git"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_002A_SOURCE_AUTHORITY.json"
)
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_002A_RECEIPT.json"
)

REQUIRED_PHASE0_EVIDENCE = (
    "docs/operations/PHASE_0_FINAL_ACCEPTANCE.md",
    "docs/roadmap/PHASE_1_ENTRY_GATE.md",
    (
        "manifests/"
        "PHASE_0_FINAL_ACCEPTANCE_SOURCE_AUTHORITY.json"
    ),
    (
        "receipts/"
        "PHASE_0_FINAL_ACCEPTANCE_RECEIPT.json"
    ),
    "scripts/verify_phase0_final_acceptance.py",
)

ALLOWED_CONTRACT_IMPORT_ROOTS = {
    "__future__",
    "collections",
    "dataclasses",
    "datetime",
    "enum",
    "hashlib",
    "json",
    "re",
    "typing",
    "unicodedata",
}


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


def verify_phase0_evidence() -> None:
    missing = [
        relative
        for relative in REQUIRED_PHASE0_EVIDENCE
        if not (ROOT / relative).is_file()
    ]

    if missing:
        raise VerificationError(
            "Phase 0 evidence missing: "
            + ", ".join(sorted(missing))
        )


def verify_dependencies() -> None:
    pyproject = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )

    project = pyproject.get("project", {})
    dependencies = project.get(
        "dependencies",
        [],
    )

    if dependencies != []:
        raise VerificationError(
            "Build 002A requires zero declared "
            "runtime dependencies."
        )


def verify_contract_imports() -> int:
    count = 0

    for path in sorted(
        (SRC / "forge2" / "contracts").rglob(
            "*.py"
        )
    ):
        source = path.read_text(
            encoding="utf-8"
        )
        tree = ast.parse(
            source,
            filename=str(path),
        )

        forbidden_tokens = (
            "pickle",
            "eval(",
            "exec(",
            "rmc_engine_v1",
        )

        for token in forbidden_tokens:
            if token in source:
                raise VerificationError(
                    "Forbidden contract-kernel token "
                    f"{token!r} in "
                    f"{path.relative_to(ROOT)}"
                )

        for node in ast.walk(tree):
            roots: list[str] = []

            if isinstance(node, ast.Import):
                roots = [
                    alias.name.split(".", 1)[0]
                    for alias in node.names
                ]

            if isinstance(node, ast.ImportFrom):
                if node.level > 0:
                    roots = []
                else:
                    roots = [
                        (node.module or "")
                        .split(".", 1)[0]
                    ]

            unexpected = sorted(
                root
                for root in roots
                if (
                    root
                    and root
                    not in ALLOWED_CONTRACT_IMPORT_ROOTS
                )
            )

            if unexpected:
                raise VerificationError(
                    "Unexpected contract-kernel import "
                    f"in {path.relative_to(ROOT)}: "
                    + ", ".join(unexpected)
                )

        count += 1

    if count != 2:
        raise VerificationError(
            "Expected exactly two contract-kernel "
            f"source files, found {count}."
        )

    return count


def verify_public_api() -> tuple[str, ...]:
    import forge2.contracts as contracts

    expected = (
        "CanonicalJsonValue",
        "CanonicalKeyCollisionError",
        "CanonicalizationCycleError",
        "CanonicalizationError",
        "InvalidStableNamespaceError",
        "MAX_SAFE_INTEGER",
        "MIN_SAFE_INTEGER",
        "MutableDataclassError",
        "UnsupportedCanonicalTypeError",
        "canonical_bytes",
        "canonical_json",
        "canonical_sha256",
        "canonicalize",
        "stable_identifier",
    )

    if contracts.__all__ != expected:
        raise VerificationError(
            "Contract-kernel public API mismatch."
        )

    return contracts.__all__


def verify_behavior() -> dict[str, str]:
    from forge2.contracts import (
        UnsupportedCanonicalTypeError,
        canonical_json,
        canonical_sha256,
        stable_identifier,
    )

    value = {
        "schema_version": "1.0.0",
        "name": "café",
        "items": [3, 2, 1],
        "enabled": True,
        "none": None,
    }

    expected_json = (
        '{"enabled":true,"items":[3,2,1],'
        '"name":"café","none":null,'
        '"schema_version":"1.0.0"}'
    )
    expected_hash = (
        "90ec26e3b46bc29f9a00493509f8dbb3"
        "8f072b701d32e3508502ac1e599d20bd"
    )

    observed_json = canonical_json(value)
    observed_hash = canonical_sha256(value)

    if observed_json != expected_json:
        raise VerificationError(
            "Fixed canonical JSON vector mismatch."
        )

    if observed_hash != expected_hash:
        raise VerificationError(
            "Fixed canonical SHA-256 vector mismatch."
        )

    reordered = {
        "none": None,
        "enabled": True,
        "items": [3, 2, 1],
        "name": "café",
        "schema_version": "1.0.0",
    }

    if canonical_sha256(reordered) != expected_hash:
        raise VerificationError(
            "Mapping-order invariance failed."
        )

    try:
        canonical_json({"value": 1.0})
    except UnsupportedCanonicalTypeError:
        pass
    else:
        raise VerificationError(
            "Floating-point rejection failed."
        )

    identifier = stable_identifier(
        "aiweb.contract",
        value,
    )

    expected_identifier = (
        "aiweb.contract:sha256:"
        + expected_hash
    )

    if identifier != expected_identifier:
        raise VerificationError(
            "Stable identifier vector mismatch."
        )

    return {
        "canonical_json": observed_json,
        "canonical_sha256": observed_hash,
        "stable_identifier": identifier,
    }


def verify_manifest() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH)

    if manifest.get("build_id") != BUILD_ID:
        raise VerificationError(
            "Manifest build identity mismatch."
        )

    if (
        manifest.get("expected_parent")
        != EXPECTED_PARENT
    ):
        raise VerificationError(
            "Manifest parent mismatch."
        )

    roadmap = manifest.get(
        "controlling_roadmap"
    )

    if not isinstance(roadmap, dict):
        raise VerificationError(
            "Manifest roadmap record missing."
        )

    if roadmap.get("document_id") != ROADMAP_ID:
        raise VerificationError(
            "Manifest roadmap identity mismatch."
        )

    files = manifest.get("files")

    if not isinstance(files, list) or not files:
        raise VerificationError(
            "Manifest file entries missing."
        )

    for entry in files:
        if not isinstance(entry, dict):
            raise VerificationError(
                "Invalid manifest entry."
            )

        relative = entry.get("path")

        if not isinstance(relative, str):
            raise VerificationError(
                "Manifest path must be text."
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
            "Receipt build identity mismatch."
        )

    if receipt.get("status") != "PASS":
        raise VerificationError(
            "Receipt status is not PASS."
        )

    if (
        receipt.get("phase_status")
        != "PHASE_1_IN_PROGRESS"
    ):
        raise VerificationError(
            "Receipt phase status mismatch."
        )

    if receipt.get("forge1_modified") is not False:
        raise VerificationError(
            "Forge 1 preservation mismatch."
        )

    if (
        receipt.get("forge1_donor_admitted")
        is not False
    ):
        raise VerificationError(
            "Receipt improperly admits a donor."
        )

    if (
        receipt.get(
            "external_dependency_admitted"
        )
        is not False
    ):
        raise VerificationError(
            "Receipt improperly admits a dependency."
        )

    if (
        receipt.get(
            "product_capability_claimed"
        )
        is not False
    ):
        raise VerificationError(
            "Receipt claims a product capability."
        )

    if (
        receipt.get(
            "source_authority_manifest_sha256"
        )
        != sha256_file(MANIFEST_PATH)
    ):
        raise VerificationError(
            "Receipt manifest binding mismatch."
        )

    return receipt


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
            "Origin is missing."
        )

    if (
        normalize_url(origin.stdout)
        != normalize_url(EXPECTED_ORIGIN)
    ):
        raise VerificationError(
            "Origin mismatch."
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
            status.returncode != 0
            or status.stdout.strip()
        ):
            raise VerificationError(
                "Committed repository is not clean."
            )

        if (
            parent.returncode != 0
            or parent.stdout.strip()
            != EXPECTED_PARENT
        ):
            raise VerificationError(
                "Build 002A commit parent mismatch."
            )

        if (
            subject.returncode != 0
            or subject.stdout.strip()
            != EXPECTED_SUBJECT
        ):
            raise VerificationError(
                "Build 002A commit subject mismatch."
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

    verify_phase0_evidence()
    verify_dependencies()
    source_count = verify_contract_imports()
    public_api = verify_public_api()
    behavior = verify_behavior()
    manifest = verify_manifest()
    receipt = verify_receipt()
    git_state = verify_git(arguments.mode)

    result = {
        "schema_version": (
            "aiweb_forge2_phase1_"
            "build_002a_verification_v1"
        ),
        "build_id": BUILD_ID,
        "mode": arguments.mode,
        "status": "PASS",
        "phase_status": "PHASE_1_IN_PROGRESS",
        "contract_source_count": source_count,
        "public_api": list(public_api),
        "fixed_vectors": behavior,
        "manifest_file_count": len(
            manifest["files"]
        ),
        "receipt_status": receipt["status"],
        "git": git_state,
        "product_capability_claimed": False,
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
