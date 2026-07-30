#!/usr/bin/env python3
"""Verify Forge 2 Phase 1 Build 006A."""

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

BUILD_ID = "FORGE2-PHASE1-BUILD-006A"
EXPECTED_PARENT = "b551b6c97efcca44b2653821db8143e88abf39bd"
EXPECTED_SUBJECT = "Establish immutable InputEvent contract"
EXPECTED_ORIGIN = "https://github.com/BogaertN/forge2.git"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"
RMC_INPUT_EVENT_ID = "17Ul43iJuo0NyFZsOuFwy7Lhhjey9Ah_DZbJJAOOyFvU"

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_006A_SOURCE_AUTHORITY.json"
)
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_006A_RECEIPT.json"
)
PREDECESSOR_MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_005A_SOURCE_AUTHORITY.json"
)
PREDECESSOR_RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_005A_RECEIPT.json"
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
        != "FORGE2-PHASE1-BUILD-005A"
        or receipt.get("build_id")
        != "FORGE2-PHASE1-BUILD-005A"
        or receipt.get("status") != "PASS"
    ):
        raise VerificationError(
            "Build 005A evidence mismatch."
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
            "Build 005A evidence binding mismatch."
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
            "Build 006A requires zero runtime "
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

    if count != 8:
        raise VerificationError(
            "Expected eight contract source files, "
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
        "FrozenCanonicalList",
        "FrozenCanonicalMap",
        "FrozenCanonicalScalar",
        "FrozenCanonicalValue",
        "INPUT_EVENT_CONTRACT_TYPE",
        "INPUT_EVENT_SCHEMA_VERSION",
        "InputEvent",
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
        "contract_metadata_from_dict",
        "contract_metadata_to_dict",
        "contract_reference_from_dict",
        "create_contract_metadata",
        "create_input_event",
        "create_request_state_registry",
        "create_successor",
        "declared_effect_from_dict",
        "freeze_canonical",
        "input_event_from_dict",
        "is_frozen_canonical",
        "request_state_from_value",
        "request_state_identity",
        "stable_identifier",
        "thaw_canonical",
        "verify_contract_metadata",
        "verify_input_event",
        "verify_successor",
    )

    if contracts.__all__ != expected:
        raise VerificationError(
            "Contract public API mismatch."
        )

    return contracts.__all__


def verify_behavior() -> dict[str, Any]:
    from forge2.contracts import (
        AuthorityStatus,
        InputEvent,
        canonical_json,
        create_input_event,
        input_event_from_dict,
        verify_input_event,
    )

    event = create_input_event(
        raw_input="hello",
        conversation_context=[],
        identity_context={
            "actor_id": "user:nic",
            "actor_kind": "user",
        },
        session_metadata={
            "channel": "terminal",
            "session_id": "session-001",
        },
        created_at=datetime(
            2026,
            7,
            30,
            21,
            0,
            tzinfo=timezone.utc,
        ),
    )

    expected_content_hash = (
        "adbd199e314785b7fa34f61dc0eb45f7"
        "b6926b42a231dd2c6f2f10420059a203"
    )
    expected_contract_id = (
        "aiweb.contract:sha256:"
        "0dd5d9a67c192c391b3dbdc1ded74cff"
        "2e906fc24fe41c492c06ca310e417798"
    )

    if (
        event.metadata.content_hash
        != expected_content_hash
        or event.metadata.contract_id
        != expected_contract_id
        or event.metadata.authority_status
        != AuthorityStatus.NONE
        or event.metadata.declared_effects
        != ()
    ):
        raise VerificationError(
            "InputEvent fixed vector mismatch."
        )

    verify_input_event(event)

    serialized = canonical_json(
        event.to_dict()
    )
    restored = input_event_from_dict(
        json.loads(serialized)
    )

    if (
        not isinstance(restored, InputEvent)
        or restored != event
        or canonical_json(
            restored.to_dict()
        )
        != serialized
    ):
        raise VerificationError(
            "InputEvent round trip failed."
        )

    return {
        "contract_type": (
            event.metadata.contract_type
        ),
        "schema_version": str(
            event.metadata.schema_version
        ),
        "content_hash": (
            event.metadata.content_hash
        ),
        "contract_id": (
            event.metadata.contract_id
        ),
        "body_fields": sorted(
            event.body().keys()
        ),
        "round_trip": True,
        "authority_status": (
            event.metadata
            .authority_status
            .value
        ),
        "declared_effect_count": 0,
    }


def verify_immutable_type() -> str:
    from forge2.contracts import InputEvent

    parameters = getattr(
        InputEvent,
        "__dataclass_params__",
        None,
    )

    if (
        not is_dataclass(InputEvent)
        or parameters is None
        or parameters.frozen is not True
        or not hasattr(InputEvent, "__slots__")
    ):
        raise VerificationError(
            "InputEvent is not frozen and slotted."
        )

    return "InputEvent"


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
    reference = manifest.get(
        "architecture_reference"
    )

    if (
        not isinstance(roadmap, dict)
        or roadmap.get("document_id")
        != ROADMAP_ID
        or not isinstance(reference, dict)
        or reference.get("document_id")
        != RMC_INPUT_EVENT_ID
    ):
        raise VerificationError(
            "Manifest source authority mismatch."
        )

    files = manifest.get("files")

    if not isinstance(files, list) or not files:
        raise VerificationError(
            "Manifest files missing."
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
        "request_transition_policy_defined",
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
    immutable_type = verify_immutable_type()
    fixed_vectors = verify_behavior()
    manifest = verify_manifest()
    receipt = verify_receipt()
    git_state = verify_git(arguments.mode)

    result = {
        "schema_version": (
            "aiweb_forge2_phase1_"
            "build_006a_verification_v1"
        ),
        "build_id": BUILD_ID,
        "mode": arguments.mode,
        "status": "PASS",
        "phase_status": "PHASE_1_IN_PROGRESS",
        "contract_source_count": source_count,
        "public_api": list(public_api),
        "immutable_type": immutable_type,
        "fixed_vectors": fixed_vectors,
        "predecessor": predecessor,
        "manifest_file_count": len(
            manifest["files"]
        ),
        "receipt_status": receipt["status"],
        "request_transition_policy_defined": False,
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
