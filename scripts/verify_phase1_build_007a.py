#!/usr/bin/env python3
"""Verify Forge 2 Phase 1 Build 007A."""

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

BUILD_ID = "FORGE2-PHASE1-BUILD-007A"
EXPECTED_PARENT = "39802d2abc3e61a370f3dc2aab99fc024b5447c6"
EXPECTED_SUBJECT = "Establish ClassificationCandidateSet contract"
EXPECTED_ORIGIN = "https://github.com/BogaertN/forge2.git"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_007A_SOURCE_AUTHORITY.json"
)
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_007A_RECEIPT.json"
)
PREDECESSOR_MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_006A_SOURCE_AUTHORITY.json"
)
PREDECESSOR_RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_006A_RECEIPT.json"
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
        != "FORGE2-PHASE1-BUILD-006A"
        or receipt.get("build_id")
        != "FORGE2-PHASE1-BUILD-006A"
        or receipt.get("status") != "PASS"
    ):
        raise VerificationError(
            "Build 006A evidence mismatch."
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
            "Build 006A evidence binding mismatch."
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
            "Build 007A requires zero runtime "
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

    if count != 9:
        raise VerificationError(
            "Expected nine contract source files, "
            f"found {count}."
        )

    return count


def verify_public_api() -> tuple[str, ...]:
    import forge2.contracts as contracts

    expected = (
        "AuthorityStatus",
        "CLASSIFICATION_CANDIDATE_ID_NAMESPACE",
        "CLASSIFICATION_CANDIDATE_SET_CONTRACT_TYPE",
        "CLASSIFICATION_CANDIDATE_SET_SCHEMA_VERSION",
        "CONFIDENCE_SCALE_BASIS_POINTS",
        "CONTRACT_ID_NAMESPACE",
        "CandidateDimension",
        "CandidateOrigin",
        "CanonicalJsonValue",
        "CanonicalKeyCollisionError",
        "CanonicalizationCycleError",
        "CanonicalizationError",
        "ClassificationCandidate",
        "ClassificationCandidateSet",
        "ContractIdentityError",
        "ContractIntegrityError",
        "ContractMetadata",
        "ContractReference",
        "ContractValidationError",
        "DeclaredEffect",
        "EffectKind",
        "FEATURE_EVIDENCE_ID_NAMESPACE",
        "FeatureEvidence",
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
        "classification_candidate_set_from_dict",
        "contract_metadata_from_dict",
        "contract_metadata_to_dict",
        "contract_reference_from_dict",
        "create_classification_candidate",
        "create_classification_candidate_set",
        "create_contract_metadata",
        "create_feature_evidence",
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
        "verify_classification_candidate_set",
        "verify_contract_metadata",
        "verify_input_event",
        "verify_successor",
    )

    if contracts.__all__ != expected:
        raise VerificationError(
            "Contract public API mismatch."
        )

    return contracts.__all__


def verify_immutable_types() -> list[str]:
    from forge2.contracts import (
        ClassificationCandidate,
        ClassificationCandidateSet,
        FeatureEvidence,
    )

    values = (
        FeatureEvidence,
        ClassificationCandidate,
        ClassificationCandidateSet,
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
    import forge2.contracts.classification_candidate as module
    from forge2.contracts import (
        AuthorityStatus,
        CandidateDimension,
        CandidateOrigin,
        canonical_json,
        classification_candidate_set_from_dict,
        create_classification_candidate,
        create_classification_candidate_set,
        create_feature_evidence,
        create_input_event,
        verify_classification_candidate_set,
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
    evidence = create_feature_evidence(
        source_pointer="/raw_input",
        feature_name="lexical_request_verb",
        observed_value="hello",
        span_start=0,
        span_end=5,
    )
    candidate = create_classification_candidate(
        dimension=CandidateDimension.REQUEST_KIND,
        label="conversation",
        origin=CandidateOrigin.RULE,
        producer_id="forge2.rule.lexical.v1",
        confidence_basis_points=9000,
        evidence=[evidence],
    )
    candidate_set = (
        create_classification_candidate_set(
            input_event=event,
            candidates=[candidate],
            created_at=datetime(
                2026,
                7,
                30,
                21,
                1,
                tzinfo=timezone.utc,
            ),
        )
    )

    expected_evidence_id = (
        "aiweb.feature-evidence:sha256:"
        "c1cf02dc8c86d7c9b5eda8829ae2842c"
        "668f4604723cb4b93731dd09a320e42c"
    )
    expected_candidate_id = (
        "aiweb.classification-candidate:sha256:"
        "a3a5a303683777075afb8c61989dfbcf"
        "489fc03054aa934061ca426e3596fa9e"
    )
    expected_content_hash = (
        "a930d2b717a8b5b636fa6553c7b383fc"
        "c387a18a3fdc63890799aa0d65e7d5df"
    )
    expected_contract_id = (
        "aiweb.contract:sha256:"
        "0a8e16ab65ce40e4fc59862b0b85bbe2"
        "aaa3fecba26a18846e934afe43fca74d"
    )

    if (
        evidence.evidence_id
        != expected_evidence_id
        or candidate.candidate_id
        != expected_candidate_id
        or candidate_set.metadata.content_hash
        != expected_content_hash
        or candidate_set.metadata.contract_id
        != expected_contract_id
        or candidate_set.metadata.authority_status
        != AuthorityStatus.NONE
        or candidate_set.metadata.declared_effects
        != ()
    ):
        raise VerificationError(
            "ClassificationCandidateSet fixed "
            "vector mismatch."
        )

    verify_classification_candidate_set(
        candidate_set,
        input_event=event,
    )

    serialized = canonical_json(
        candidate_set.to_dict()
    )
    restored = (
        classification_candidate_set_from_dict(
            json.loads(serialized),
            input_event=event,
        )
    )

    if (
        restored != candidate_set
        or canonical_json(
            restored.to_dict()
        )
        != serialized
    ):
        raise VerificationError(
            "ClassificationCandidateSet round "
            "trip failed."
        )

    for name in (
        "select_candidate",
        "selected_candidate",
        "authorize_candidate",
        "execute_candidate",
        "classification_to_request_contract",
    ):
        if hasattr(module, name):
            raise VerificationError(
                "Selection or execution API was "
                f"added prematurely: {name}"
            )

    return {
        "input_event_contract_id": (
            event.metadata.contract_id
        ),
        "feature_evidence_id": (
            evidence.evidence_id
        ),
        "candidate_id": (
            candidate.candidate_id
        ),
        "candidate_set_content_hash": (
            candidate_set.metadata.content_hash
        ),
        "candidate_set_contract_id": (
            candidate_set.metadata.contract_id
        ),
        "candidate_count": 1,
        "candidate_dimension": (
            candidate.dimension.value
        ),
        "confidence_basis_points": (
            candidate.confidence_basis_points
        ),
        "round_trip": True,
        "authority_status": "none",
        "declared_effect_count": 0,
        "selection_performed": False,
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
        (
            "request_state_py_sha256",
            "src/forge2/contracts/request_state.py",
        ),
        (
            "frozen_value_py_sha256",
            "src/forge2/contracts/frozen_value.py",
        ),
        (
            "codec_py_sha256",
            "src/forge2/contracts/codec.py",
        ),
        (
            "input_event_py_sha256",
            "src/forge2/contracts/input_event.py",
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
        "classifier_execution_added",
        "model_training_added",
        "candidate_selection_added",
        "request_contract_added",
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
            or head.returncode != 0
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
            "build_007a_verification_v1"
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
        "classifier_execution_added": False,
        "model_training_added": False,
        "candidate_selection_added": False,
        "request_contract_added": False,
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
