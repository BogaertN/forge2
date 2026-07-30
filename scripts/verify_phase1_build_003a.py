#!/usr/bin/env python3
"""Verify Forge 2 Phase 1 Build 003A."""

from __future__ import annotations

import argparse
import ast
from dataclasses import is_dataclass
from datetime import datetime, timezone
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

BUILD_ID = "FORGE2-PHASE1-BUILD-003A"
EXPECTED_PARENT = "28482b4a09257b9651d825bd78674dac7abf8885"
EXPECTED_SUBJECT = "Establish immutable contract identity metadata"
EXPECTED_ORIGIN = "https://github.com/BogaertN/forge2.git"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_003A_SOURCE_AUTHORITY.json"
)
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_003A_RECEIPT.json"
)

PREDECESSOR_MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_002A_SOURCE_AUTHORITY.json"
)
PREDECESSOR_RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_002A_RECEIPT.json"
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


def verify_predecessor_evidence() -> dict[str, str]:
    manifest = load_json(
        PREDECESSOR_MANIFEST_PATH
    )
    receipt = load_json(
        PREDECESSOR_RECEIPT_PATH
    )

    if (
        manifest.get("build_id")
        != "FORGE2-PHASE1-BUILD-002A"
        or receipt.get("build_id")
        != "FORGE2-PHASE1-BUILD-002A"
        or receipt.get("status") != "PASS"
    ):
        raise VerificationError(
            "Build 002A evidence identity mismatch."
        )

    if (
        receipt.get(
            "source_authority_manifest_sha256"
        )
        != sha256_file(
            PREDECESSOR_MANIFEST_PATH
        )
    ):
        raise VerificationError(
            "Build 002A evidence binding mismatch."
        )

    return {
        "manifest_sha256": sha256_file(
            PREDECESSOR_MANIFEST_PATH
        ),
        "receipt_sha256": sha256_file(
            PREDECESSOR_RECEIPT_PATH
        ),
    }


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
            "Build 003A requires zero declared "
            "runtime dependencies."
        )


def verify_contract_sources() -> int:
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
            "subprocess",
            "requests",
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
                    "Unexpected contract import in "
                    f"{path.relative_to(ROOT)}: "
                    + ", ".join(unexpected)
                )

        count += 1

    if count != 3:
        raise VerificationError(
            "Expected exactly three contract source "
            f"files, found {count}."
        )

    return count


def verify_public_api() -> tuple[str, ...]:
    import forge2.contracts as contracts

    expected = (
        "AuthorityStatus",
        "CONTRACT_ID_NAMESPACE",
        "CanonicalJsonValue",
        "CanonicalKeyCollisionError",
        "CanonicalizationCycleError",
        "CanonicalizationError",
        "ContractIdentityError",
        "ContractIntegrityError",
        "ContractMetadata",
        "ContractReference",
        "ContractValidationError",
        "DeclaredEffect",
        "EffectKind",
        "InvalidStableNamespaceError",
        "LifecycleState",
        "MAX_SAFE_INTEGER",
        "MIN_SAFE_INTEGER",
        "MutableDataclassError",
        "SCHEMA_COMPONENT_MAX",
        "SchemaVersion",
        "UnsupportedCanonicalTypeError",
        "canonical_bytes",
        "canonical_json",
        "canonical_sha256",
        "canonicalize",
        "create_contract_metadata",
        "stable_identifier",
        "verify_contract_metadata",
    )

    if contracts.__all__ != expected:
        raise VerificationError(
            "Contract public API mismatch."
        )

    return contracts.__all__


def verify_immutable_types() -> list[str]:
    from forge2.contracts import (
        ContractMetadata,
        ContractReference,
        DeclaredEffect,
        SchemaVersion,
    )

    types = (
        SchemaVersion,
        DeclaredEffect,
        ContractReference,
        ContractMetadata,
    )

    names: list[str] = []

    for value in types:
        if not is_dataclass(value):
            raise VerificationError(
                f"{value.__name__} is not a dataclass."
            )

        parameters = getattr(
            value,
            "__dataclass_params__",
            None,
        )

        if (
            parameters is None
            or parameters.frozen is not True
        ):
            raise VerificationError(
                f"{value.__name__} is not frozen."
            )

        if not hasattr(value, "__slots__"):
            raise VerificationError(
                f"{value.__name__} is not slotted."
            )

        names.append(value.__name__)

    return names


def verify_behavior() -> dict[str, Any]:
    from forge2.contracts import (
        AuthorityStatus,
        ContractIntegrityError,
        DeclaredEffect,
        EffectKind,
        LifecycleState,
        SchemaVersion,
        canonical_sha256,
        create_contract_metadata,
        verify_contract_metadata,
    )

    body = {
        "raw_input": "hello",
        "conversation_context": [],
    }
    created_at = datetime(
        2026,
        7,
        30,
        20,
        15,
        tzinfo=timezone.utc,
    )

    metadata = create_contract_metadata(
        schema_version="1.0.0",
        contract_type="InputEvent",
        body=body,
        created_at=created_at,
    )

    expected_body_hash = (
        "42d05d320c302a6fb5c5657f12d1f47f"
        "f4c5394a04b5ede825ed880d92ad9e31"
    )
    expected_contract_id = (
        "aiweb.contract:sha256:"
        "511d7a8fae0fa5279524c6f2042347c7"
        "d8c22fe80a8589cbfd13bf6b65607140"
    )

    if canonical_sha256(body) != expected_body_hash:
        raise VerificationError(
            "Canonical predecessor vector changed."
        )

    if metadata.content_hash != expected_body_hash:
        raise VerificationError(
            "Contract content-hash vector mismatch."
        )

    if metadata.contract_id != expected_contract_id:
        raise VerificationError(
            "Contract identity vector mismatch."
        )

    if (
        metadata.schema_version
        != SchemaVersion(1, 0, 0)
        or metadata.lifecycle_state
        != LifecycleState.CANDIDATE
        or metadata.authority_status
        != AuthorityStatus.NONE
    ):
        raise VerificationError(
            "Contract metadata defaults mismatch."
        )

    verify_contract_metadata(
        metadata,
        body,
    )

    try:
        verify_contract_metadata(
            metadata,
            {"changed": True},
        )
    except ContractIntegrityError as error:
        if error.code != "content_hash_mismatch":
            raise VerificationError(
                "Integrity error code mismatch."
            ) from error
    else:
        raise VerificationError(
            "Changed body was not rejected."
        )

    effects = [
        DeclaredEffect(
            EffectKind.WRITE,
            "workspace:/receipt",
        ),
        DeclaredEffect(
            EffectKind.READ,
            "workspace:/repository",
        ),
    ]

    with_effects = create_contract_metadata(
        schema_version="1.0.0",
        contract_type="InputEvent",
        body=body,
        created_at=created_at,
        authority_status=(
            AuthorityStatus.REQUESTED
        ),
        declared_effects=effects,
    )

    if tuple(
        effect.kind
        for effect in with_effects.declared_effects
    ) != (
        EffectKind.READ,
        EffectKind.WRITE,
    ):
        raise VerificationError(
            "Effect canonical ordering failed."
        )

    successor = create_contract_metadata(
        schema_version="1.0.0",
        contract_type="InputEvent",
        body=body,
        created_at=created_at,
        parent=metadata.to_reference(),
    )

    if (
        successor.parent
        != metadata.to_reference()
        or successor.contract_id
        == metadata.contract_id
    ):
        raise VerificationError(
            "Parent reference identity binding failed."
        )

    return {
        "content_hash": metadata.content_hash,
        "contract_id": metadata.contract_id,
        "schema_version": str(
            metadata.schema_version
        ),
        "lifecycle_state": (
            metadata.lifecycle_state.value
        ),
        "authority_status": (
            metadata.authority_status.value
        ),
        "effect_order": [
            effect.kind.value
            for effect
            in with_effects.declared_effects
        ],
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
                "Invalid manifest file entry."
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

    anchors = manifest.get(
        "predecessor_anchors"
    )

    if not isinstance(anchors, dict):
        raise VerificationError(
            "Predecessor anchors missing."
        )

    canonical_path = (
        ROOT
        / "src"
        / "forge2"
        / "contracts"
        / "canonical.py"
    )

    if (
        anchors.get("canonical_py_sha256")
        != sha256_file(canonical_path)
    ):
        raise VerificationError(
            "Canonical predecessor source changed."
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

    for field in (
        "forge1_modified",
        "forge1_source_copied",
        "forge1_donor_admitted",
        "external_dependency_admitted",
        "product_capability_claimed",
        "runtime_authority_added",
    ):
        if receipt.get(field) is not False:
            raise VerificationError(
                f"Receipt boundary mismatch: {field}"
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
                "Build 003A parent mismatch."
            )

        if (
            subject.returncode != 0
            or subject.stdout.strip()
            != EXPECTED_SUBJECT
        ):
            raise VerificationError(
                "Build 003A subject mismatch."
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

    predecessor = verify_predecessor_evidence()
    verify_dependencies()
    source_count = verify_contract_sources()
    public_api = verify_public_api()
    immutable_types = verify_immutable_types()
    fixed_vectors = verify_behavior()
    manifest = verify_manifest()
    receipt = verify_receipt()
    git_state = verify_git(arguments.mode)

    result = {
        "schema_version": (
            "aiweb_forge2_phase1_"
            "build_003a_verification_v1"
        ),
        "build_id": BUILD_ID,
        "mode": arguments.mode,
        "status": "PASS",
        "phase_status": "PHASE_1_IN_PROGRESS",
        "contract_source_count": source_count,
        "public_api": list(public_api),
        "immutable_types": immutable_types,
        "fixed_vectors": fixed_vectors,
        "predecessor": predecessor,
        "manifest_file_count": len(
            manifest["files"]
        ),
        "receipt_status": receipt["status"],
        "runtime_authority_added": False,
        "product_capability_claimed": False,
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
