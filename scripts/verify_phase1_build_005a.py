#!/usr/bin/env python3
"""Verify Forge 2 Phase 1 Build 005A."""

from __future__ import annotations

import argparse
import ast
from dataclasses import is_dataclass
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

BUILD_ID = "FORGE2-PHASE1-BUILD-005A"
EXPECTED_PARENT = "b1daf7e090d350d83315ca87c228bb5f47e0740b"
EXPECTED_SUBJECT = "Establish request lifecycle state identities"
EXPECTED_ORIGIN = "https://github.com/BogaertN/forge2.git"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_005A_SOURCE_AUTHORITY.json"
)
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_005A_RECEIPT.json"
)
PREDECESSOR_MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_004A_SOURCE_AUTHORITY.json"
)
PREDECESSOR_RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_004A_RECEIPT.json"
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
        != "FORGE2-PHASE1-BUILD-004A"
        or receipt.get("build_id")
        != "FORGE2-PHASE1-BUILD-004A"
        or receipt.get("status") != "PASS"
    ):
        raise VerificationError(
            "Build 004A evidence mismatch."
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
            "Build 004A evidence binding mismatch."
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
            "Build 005A requires zero runtime "
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

    if count != 5:
        raise VerificationError(
            "Expected five contract source files, "
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
        "REQUEST_STATE_ID_NAMESPACE",
        "REQUEST_STATE_REGISTRY",
        "REQUEST_STATE_REGISTRY_NAMESPACE",
        "REQUEST_STATE_SCHEMA_VERSION",
        "REQUEST_STATE_SEQUENCE",
        "RequestState",
        "RequestStateIdentity",
        "RequestStateRegistry",
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
        "create_request_state_registry",
        "create_successor",
        "request_state_from_value",
        "request_state_identity",
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
        RequestStateIdentity,
        RequestStateRegistry,
    )

    values = (
        RequestStateIdentity,
        RequestStateRegistry,
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
    import forge2.contracts.request_state as module
    from forge2.contracts import (
        REQUEST_STATE_REGISTRY,
        REQUEST_STATE_SEQUENCE,
        RequestState,
        create_request_state_registry,
        request_state_identity,
    )

    expected_values = (
        "RECEIVED",
        "CUSTODIED",
        "INTERPRETATION_CANDIDATES_READY",
        "CLARIFICATION_REQUIRED",
        "REQUEST_CONTRACT_READY",
        "CONTEXT_READY",
        "CAPABILITY_REQUIREMENTS_READY",
        "CAPABILITY_RESOLVED",
        "PLAN_READY",
        "AWAITING_AUTHORITY",
        "AUTHORIZED",
        "EXECUTING",
        "EXECUTION_COMPLETE",
        "VERIFYING",
        "VERIFIED",
        "FAILED",
        "HELD",
        "CANCELLED",
        "RESULT_READY",
        "DELIVERED",
        "APPLY_PENDING",
        "APPLIED",
        "COMMITTED",
        "RELEASED",
        "ARCHIVED",
    )

    observed_values = tuple(
        state.value
        for state in REQUEST_STATE_SEQUENCE
    )

    if observed_values != expected_values:
        raise VerificationError(
            "Request-state sequence mismatch."
        )

    if len(set(REQUEST_STATE_SEQUENCE)) != 25:
        raise VerificationError(
            "Request-state uniqueness mismatch."
        )

    received = request_state_identity(
        RequestState.RECEIVED
    )
    archived = request_state_identity(
        RequestState.ARCHIVED
    )
    registry = create_request_state_registry()

    expected_received_id = (
        "aiweb.request-state:sha256:"
        "60472d4866543431ce0836292deb9d62"
        "ae9157ba88a4eb433b82076db0a80c1d"
    )
    expected_archived_id = (
        "aiweb.request-state:sha256:"
        "c269691823c6c3b0c9f315df49eb5e48"
        "fb2114d2622534b4ece669963481ff25"
    )
    expected_registry_id = (
        "aiweb.request-state-registry:sha256:"
        "2abe0345a66300db59928e416dd358f8"
        "36dc05c8017cdfd8f75dd9b376b16e5b"
    )

    if (
        received.state_id != expected_received_id
        or archived.state_id
        != expected_archived_id
        or registry.registry_id
        != expected_registry_id
        or registry
        != REQUEST_STATE_REGISTRY
        or registry.transition_policy_defined
        is not False
    ):
        raise VerificationError(
            "Request-state fixed vector mismatch."
        )

    for name in (
        "allowed_request_transitions",
        "create_request_transition",
        "request_transition_allowed",
        "RequestStateTransitionReceipt",
    ):
        if hasattr(module, name):
            raise VerificationError(
                "Transition API was added "
                f"prematurely: {name}"
            )

    return {
        "state_count": 25,
        "first_state": received.state.value,
        "first_state_id": received.state_id,
        "last_state": archived.state.value,
        "last_state_id": archived.state_id,
        "registry_id": registry.registry_id,
        "transition_policy_defined": False,
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
            "src/forge2/contracts/canonical.py",
        ),
        (
            "identity_py_sha256",
            "src/forge2/contracts/identity.py",
        ),
        (
            "successor_py_sha256",
            "src/forge2/contracts/successor.py",
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
        "transition_policy_defined",
        "transition_permissions_added",
        "transition_receipts_added",
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
            "build_005a_verification_v1"
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
        "transition_policy_defined": False,
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
