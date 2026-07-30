#!/usr/bin/env python3
"""Verify Forge 2 Phase 1 Build 004A."""

from __future__ import annotations

import argparse
import ast
from dataclasses import is_dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
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

BUILD_ID = "FORGE2-PHASE1-BUILD-004A"
EXPECTED_PARENT = "195cfecc44ca5829b01309206e2f21f456043e72"
EXPECTED_SUBJECT = "Establish append-only contract successor laws"
EXPECTED_ORIGIN = "https://github.com/BogaertN/forge2.git"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_004A_SOURCE_AUTHORITY.json"
)
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_004A_RECEIPT.json"
)
PREDECESSOR_MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_003A_SOURCE_AUTHORITY.json"
)
PREDECESSOR_RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_003A_RECEIPT.json"
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


def verify_predecessor() -> dict[str, str]:
    manifest = load_json(
        PREDECESSOR_MANIFEST_PATH
    )
    receipt = load_json(
        PREDECESSOR_RECEIPT_PATH
    )

    if (
        manifest.get("build_id")
        != "FORGE2-PHASE1-BUILD-003A"
        or receipt.get("build_id")
        != "FORGE2-PHASE1-BUILD-003A"
        or receipt.get("status") != "PASS"
    ):
        raise VerificationError(
            "Build 003A evidence mismatch."
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
            "Build 003A evidence binding mismatch."
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

    dependencies = (
        pyproject
        .get("project", {})
        .get("dependencies", [])
    )

    if dependencies != []:
        raise VerificationError(
            "Build 004A requires zero runtime "
            "dependencies."
        )


def verify_sources() -> int:
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

        for token in (
            "pickle",
            "eval(",
            "exec(",
            "rmc_engine_v1",
            "requests",
            "subprocess",
        ):
            if token in source:
                raise VerificationError(
                    "Forbidden contract token "
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
                if node.level == 0:
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

    if count != 4:
        raise VerificationError(
            "Expected four contract source files, "
            f"found {count}."
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
        "SUCCESSOR_ID_NAMESPACE",
        "SchemaVersion",
        "SuccessorKind",
        "SuccessorReceipt",
        "SuccessorTransition",
        "UnsupportedCanonicalTypeError",
        "canonical_bytes",
        "canonical_json",
        "canonical_sha256",
        "canonicalize",
        "create_contract_metadata",
        "create_successor",
        "stable_identifier",
        "verify_contract_metadata",
        "verify_successor",
    )

    if contracts.__all__ != expected:
        raise VerificationError(
            "Contract public API mismatch."
        )

    return contracts.__all__


def verify_immutable_types() -> list[str]:
    from forge2.contracts import (
        SuccessorReceipt,
        SuccessorTransition,
    )

    values = (
        SuccessorReceipt,
        SuccessorTransition,
    )
    names: list[str] = []

    for value in values:
        parameters = getattr(
            value,
            "__dataclass_params__",
            None,
        )

        if (
            not is_dataclass(value)
            or parameters is None
            or parameters.frozen is not True
            or not hasattr(value, "__slots__")
        ):
            raise VerificationError(
                f"{value.__name__} is not "
                "frozen and slotted."
            )

        names.append(value.__name__)

    return names


def verify_behavior() -> dict[str, Any]:
    from forge2.contracts import (
        ContractValidationError,
        SuccessorKind,
        create_contract_metadata,
        create_successor,
        verify_successor,
    )

    body = {
        "raw_input": "hello",
        "conversation_context": [],
    }
    next_body = {
        "raw_input": "hello again",
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
    next_time = (
        created_at + timedelta(minutes=1)
    )

    predecessor = create_contract_metadata(
        schema_version="1.0.0",
        contract_type="InputEvent",
        body=body,
        created_at=created_at,
    )
    transition = create_successor(
        predecessor=predecessor,
        predecessor_body=body,
        successor_body=next_body,
        created_at=next_time,
    )

    expected_successor_id = (
        "aiweb.contract:sha256:"
        "e376a287b2624dcb84b0ebadb2743d41"
        "4d557e59ff9c68bf650b0814f9d8f963"
    )
    expected_receipt_id = (
        "aiweb.successor:sha256:"
        "b642c2e56c5df8513aa00314940a4852"
        "7874e6ea1fc94431ced4696af30384a0"
    )

    if (
        transition.metadata.contract_id
        != expected_successor_id
        or transition.receipt.receipt_id
        != expected_receipt_id
        or transition.receipt.kind
        != SuccessorKind.BODY_REVISION
        or transition.receipt.changed_fields
        != ("body",)
    ):
        raise VerificationError(
            "Successor fixed vector mismatch."
        )

    verify_successor(
        predecessor=predecessor,
        predecessor_body=body,
        successor=transition.metadata,
        successor_body=next_body,
        receipt=transition.receipt,
    )

    try:
        create_successor(
            predecessor=predecessor,
            predecessor_body=body,
            successor_body=body,
            created_at=next_time,
        )
    except ContractValidationError as error:
        if error.code != "no_successor_change":
            raise VerificationError(
                "No-op error code mismatch."
            ) from error
    else:
        raise VerificationError(
            "No-op successor was accepted."
        )

    return {
        "predecessor_contract_id": (
            predecessor.contract_id
        ),
        "successor_contract_id": (
            transition.metadata.contract_id
        ),
        "successor_receipt_id": (
            transition.receipt.receipt_id
        ),
        "successor_kind": (
            transition.receipt.kind.value
        ),
        "successor_rule": (
            transition.receipt.rule_id
        ),
        "changed_fields": list(
            transition.receipt.changed_fields
        ),
    }


def verify_manifest() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH)

    if (
        manifest.get("build_id") != BUILD_ID
        or manifest.get("expected_parent")
        != EXPECTED_PARENT
    ):
        raise VerificationError(
            "Manifest identity mismatch."
        )

    roadmap = manifest.get(
        "controlling_roadmap"
    )

    if (
        not isinstance(roadmap, dict)
        or roadmap.get("document_id")
        != ROADMAP_ID
    ):
        raise VerificationError(
            "Manifest roadmap mismatch."
        )

    files = manifest.get("files")

    if not isinstance(files, list) or not files:
        raise VerificationError(
            "Manifest files missing."
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

        if (
            not path.is_file()
            or sha256_file(path)
            != entry.get("sha256")
            or path.stat().st_size
            != entry.get("size_bytes")
        ):
            raise VerificationError(
                "Manifest file mismatch: "
                f"{relative}"
            )

    anchors = manifest.get(
        "predecessor_anchors"
    )

    if not isinstance(anchors, dict):
        raise VerificationError(
            "Predecessor anchors missing."
        )

    for key, relative in (
        (
            "canonical_py_sha256",
            (
                "src/forge2/contracts/"
                "canonical.py"
            ),
        ),
        (
            "identity_py_sha256",
            (
                "src/forge2/contracts/"
                "identity.py"
            ),
        ),
    ):
        if (
            anchors.get(key)
            != sha256_file(ROOT / relative)
        ):
            raise VerificationError(
                f"Predecessor anchor mismatch: {key}"
            )

    return manifest


def verify_receipt() -> dict[str, Any]:
    receipt = load_json(RECEIPT_PATH)

    if (
        receipt.get("build_id") != BUILD_ID
        or receipt.get("status") != "PASS"
        or receipt.get("phase_status")
        != "PHASE_1_IN_PROGRESS"
    ):
        raise VerificationError(
            "Receipt identity mismatch."
        )

    for field in (
        "forge1_modified",
        "forge1_source_copied",
        "forge1_donor_admitted",
        "external_dependency_admitted",
        "runtime_authority_added",
        "product_capability_claimed",
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

    if (
        origin.returncode != 0
        or normalize_url(origin.stdout)
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
            or parent.returncode != 0
            or parent.stdout.strip()
            != EXPECTED_PARENT
            or subject.returncode != 0
            or subject.stdout.strip()
            != EXPECTED_SUBJECT
        ):
            raise VerificationError(
                "Committed Git state mismatch."
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

    predecessor = verify_predecessor()
    verify_dependencies()
    source_count = verify_sources()
    public_api = verify_public_api()
    immutable_types = verify_immutable_types()
    fixed_vectors = verify_behavior()
    manifest = verify_manifest()
    receipt = verify_receipt()
    git_state = verify_git(arguments.mode)

    result = {
        "schema_version": (
            "aiweb_forge2_phase1_"
            "build_004a_verification_v1"
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
