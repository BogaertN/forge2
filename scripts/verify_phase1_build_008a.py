#!/usr/bin/env python3
"""Verify Forge 2 Phase 1 Build 008A."""

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

BUILD_ID = "FORGE2-PHASE1-BUILD-008A"
EXPECTED_PARENT = "340df5c41692f916649eb943cacf0303125024c4"
EXPECTED_SUBJECT = "Establish immutable RequestContract"
EXPECTED_ORIGIN = "https://github.com/BogaertN/forge2.git"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_008A_SOURCE_AUTHORITY.json"
)
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_008A_RECEIPT.json"
)
PREDECESSOR_MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_007A_SOURCE_AUTHORITY.json"
)
PREDECESSOR_RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_007A_RECEIPT.json"
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
        != "FORGE2-PHASE1-BUILD-007A"
        or receipt.get("build_id")
        != "FORGE2-PHASE1-BUILD-007A"
        or receipt.get("status") != "PASS"
    ):
        raise VerificationError(
            "Build 007A evidence mismatch."
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
            "Build 007A evidence binding mismatch."
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
            "Build 008A requires zero runtime "
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

    if count != 10:
        raise VerificationError(
            "Expected ten contract source files, "
            f"found {count}."
        )

    return count


def verify_public_api() -> tuple[str, ...]:
    import forge2.contracts as contracts

    expected = (
        "AuthorityStatus",
        "CANDIDATE_SELECTION_ID_NAMESPACE",
        "CLASSIFICATION_CANDIDATE_ID_NAMESPACE",
        "CLASSIFICATION_CANDIDATE_SET_CONTRACT_TYPE",
        "CLASSIFICATION_CANDIDATE_SET_SCHEMA_VERSION",
        "CONFIDENCE_SCALE_BASIS_POINTS",
        "CONTRACT_ID_NAMESPACE",
        "CandidateDimension",
        "CandidateOrigin",
        "CandidateSelection",
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
        "REQUEST_CONTRACT_SCHEMA_VERSION",
        "REQUEST_CONTRACT_TYPE",
        "REQUEST_STATE_ID_NAMESPACE",
        "REQUEST_STATE_REGISTRY",
        "REQUEST_STATE_REGISTRY_NAMESPACE",
        "REQUEST_STATE_SCHEMA_VERSION",
        "REQUEST_STATE_SEQUENCE",
        "REQUEST_STATEMENT_ID_NAMESPACE",
        "RequestContract",
        "RequestState",
        "RequestStateIdentity",
        "RequestStateRegistry",
        "RequestStatement",
        "RequestStatementKind",
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
        "create_candidate_selection",
        "create_classification_candidate",
        "create_classification_candidate_set",
        "create_contract_metadata",
        "create_feature_evidence",
        "create_input_event",
        "create_request_contract",
        "create_request_state_registry",
        "create_request_statement",
        "create_successor",
        "declared_effect_from_dict",
        "freeze_canonical",
        "input_event_from_dict",
        "is_frozen_canonical",
        "request_contract_from_dict",
        "request_state_from_value",
        "request_state_identity",
        "stable_identifier",
        "thaw_canonical",
        "verify_classification_candidate_set",
        "verify_contract_metadata",
        "verify_input_event",
        "verify_request_contract",
        "verify_successor",
    )

    if contracts.__all__ != expected:
        raise VerificationError(
            "Contract public API mismatch."
        )

    return contracts.__all__


def verify_immutable_types() -> list[str]:
    from forge2.contracts import (
        CandidateSelection,
        RequestContract,
        RequestStatement,
    )

    values = (
        CandidateSelection,
        RequestStatement,
        RequestContract,
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
    import forge2.contracts.request_contract as module
    from forge2.contracts import (
        AuthorityStatus,
        CandidateDimension,
        CandidateOrigin,
        RequestStatementKind,
        canonical_json,
        create_candidate_selection,
        create_classification_candidate,
        create_classification_candidate_set,
        create_feature_evidence,
        create_input_event,
        create_request_contract,
        create_request_statement,
        request_contract_from_dict,
        verify_request_contract,
    )

    input_event = create_input_event(
        raw_input=(
            "Explain the repository "
            "without changing files."
        ),
        conversation_context=[],
        identity_context={
            "actor_id": "user:nic",
            "actor_kind": "user",
        },
        session_metadata={
            "channel": "terminal",
            "session_id": "session-008",
        },
        created_at=datetime(
            2026,
            7,
            30,
            22,
            0,
            tzinfo=timezone.utc,
        ),
    )

    request_evidence = create_feature_evidence(
        source_pointer="/raw_input",
        feature_name="request_kind_phrase",
        observed_value="Explain",
        span_start=0,
        span_end=7,
    )
    result_evidence = create_feature_evidence(
        source_pointer="/raw_input",
        feature_name="expected_result_phrase",
        observed_value="repository",
        span_start=12,
        span_end=22,
    )
    constraint_evidence = (
        create_feature_evidence(
            source_pointer="/raw_input",
            feature_name=(
                "preservation_constraint"
            ),
            observed_value=(
                "without changing files"
            ),
            span_start=23,
            span_end=45,
        )
    )

    request_candidate = (
        create_classification_candidate(
            dimension=(
                CandidateDimension.REQUEST_KIND
            ),
            label="repository_explanation",
            origin=CandidateOrigin.RULE,
            producer_id=(
                "forge2.rule.request.v1"
            ),
            confidence_basis_points=9800,
            evidence=[request_evidence],
        )
    )
    result_candidate = (
        create_classification_candidate(
            dimension=(
                CandidateDimension
                .EXPECTED_RESULT
            ),
            label=(
                "human_readable_explanation"
            ),
            origin=CandidateOrigin.RULE,
            producer_id=(
                "forge2.rule.result.v1"
            ),
            confidence_basis_points=9500,
            evidence=[result_evidence],
        )
    )
    effect_candidate = (
        create_classification_candidate(
            dimension=(
                CandidateDimension
                .SIDE_EFFECT_CLASS
            ),
            label="read_only",
            origin=CandidateOrigin.RULE,
            producer_id=(
                "forge2.rule.side_effect.v1"
            ),
            confidence_basis_points=9900,
            evidence=[constraint_evidence],
        )
    )

    candidate_set = (
        create_classification_candidate_set(
            input_event=input_event,
            candidates=[
                request_candidate,
                result_candidate,
                effect_candidate,
            ],
            created_at=datetime(
                2026,
                7,
                30,
                22,
                0,
                1,
                tzinfo=timezone.utc,
            ),
        )
    )

    request_selection = (
        create_candidate_selection(
            candidate=request_candidate,
            basis_codes=[
                "exact_request_phrase"
            ],
        )
    )
    result_selection = (
        create_candidate_selection(
            candidate=result_candidate,
            basis_codes=[
                "exact_result_phrase"
            ],
        )
    )
    effect_selection = (
        create_candidate_selection(
            candidate=effect_candidate,
            basis_codes=[
                (
                    "explicit_preservation_"
                    "constraint"
                )
            ],
        )
    )

    goal = create_request_statement(
        kind=RequestStatementKind.GOAL,
        code="explain_repository",
        text="Explain the repository.",
        evidence_ids=[
            request_evidence.evidence_id,
            result_evidence.evidence_id,
        ],
    )
    constraint = create_request_statement(
        kind=RequestStatementKind.CONSTRAINT,
        code="preserve_files",
        text="Do not change files.",
        evidence_ids=[
            constraint_evidence.evidence_id
        ],
    )
    desired_result = create_request_statement(
        kind=(
            RequestStatementKind
            .DESIRED_RESULT
        ),
        code="human_readable_explanation",
        text=(
            "A human-readable repository "
            "explanation."
        ),
        evidence_ids=[
            result_evidence.evidence_id
        ],
    )

    request_contract = create_request_contract(
        input_event=input_event,
        classification_candidate_set=(
            candidate_set
        ),
        producer_id=(
            "forge2.request-contract.fixture.v1"
        ),
        selected_candidates=[
            request_selection,
            result_selection,
            effect_selection,
        ],
        goals=[goal],
        constraints=[constraint],
        desired_result=desired_result,
        uncertainty_codes=[],
        created_at=datetime(
            2026,
            7,
            30,
            22,
            0,
            2,
            tzinfo=timezone.utc,
        ),
    )

    expected_values = {
        "input_event_content_hash": (
            "411ea0770af587aa2ebe3b2c0a44978b"
            "50bb803cff80ecce9d2ee7c8c42113cc"
        ),
        "input_event_contract_id": (
            "aiweb.contract:sha256:"
            "b7427c374c1567c048034f262ba4a2f4"
            "7ddf2222dcff923ea43d9717795ea1c7"
        ),
        "candidate_set_content_hash": (
            "827f61ad25a3bac1c52ea421716d1d11"
            "9d3bedb7815d4e638095d81439f87011"
        ),
        "candidate_set_contract_id": (
            "aiweb.contract:sha256:"
            "0c690f7b61cf88e2870fa860fc678bca"
            "ebe4ffbd506b6191d64d55474f071a57"
        ),
        "request_contract_content_hash": (
            "527b122ea8a909e22651e0f0bf86d5a2"
            "fb725fee4e2071e9a86f2df0e9b5e560"
        ),
        "request_contract_id": (
            "aiweb.contract:sha256:"
            "0ed80df9842671f7804cd165ab11bd82"
            "d480e578992c05decd16cd4e503f521f"
        ),
    }

    observed_values = {
        "input_event_content_hash": (
            input_event.metadata.content_hash
        ),
        "input_event_contract_id": (
            input_event.metadata.contract_id
        ),
        "candidate_set_content_hash": (
            candidate_set.metadata.content_hash
        ),
        "candidate_set_contract_id": (
            candidate_set.metadata.contract_id
        ),
        "request_contract_content_hash": (
            request_contract
            .metadata
            .content_hash
        ),
        "request_contract_id": (
            request_contract
            .metadata
            .contract_id
        ),
    }

    if observed_values != expected_values:
        raise VerificationError(
            "RequestContract fixed vector mismatch."
        )

    verify_request_contract(
        request_contract,
        input_event=input_event,
        classification_candidate_set=(
            candidate_set
        ),
    )

    serialized = canonical_json(
        request_contract.to_dict()
    )
    restored = request_contract_from_dict(
        json.loads(serialized),
        input_event=input_event,
        classification_candidate_set=(
            candidate_set
        ),
    )

    if (
        restored != request_contract
        or canonical_json(
            restored.to_dict()
        )
        != serialized
        or (
            request_contract
            .metadata
            .authority_status
            != AuthorityStatus.NONE
        )
        or (
            request_contract
            .metadata
            .declared_effects
            != ()
        )
    ):
        raise VerificationError(
            "RequestContract round trip or "
            "authority boundary failed."
        )

    for name in (
        "compile_request",
        "resolve_candidate_conflicts",
        "select_candidate",
        "authorize_request",
        "plan_request",
        "select_tool",
        "execute_request",
        "build_context",
    ):
        if hasattr(module, name):
            raise VerificationError(
                "Premature compiler or authority "
                f"API found: {name}"
            )

    return {
        **observed_values,
        "selected_candidate_count": len(
            request_contract
            .selected_candidates
        ),
        "goal_count": len(
            request_contract.goals
        ),
        "constraint_count": len(
            request_contract.constraints
        ),
        "desired_result_code": (
            request_contract
            .desired_result
            .code
        ),
        "uncertainty_count": len(
            request_contract
            .uncertainty_codes
        ),
        "round_trip": True,
        "authority_status": "none",
        "declared_effect_count": 0,
        "automatic_selection_performed": False,
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
        (
            "classification_candidate_py_sha256",
            (
                "src/forge2/contracts/"
                "classification_candidate.py"
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
        or receipt.get(
            "request_contract_added"
        ) is not True
        or receipt.get(
            "candidate_selection_recording_added"
        ) is not True
    ):
        raise VerificationError(
            "Receipt identity mismatch."
        )

    for field in (
        "forge1_modified",
        "forge1_source_copied",
        "forge1_donor_admitted",
        "external_dependency_admitted",
        "automatic_candidate_selection_added",
        "candidate_selection_policy_added",
        "request_compiler_runtime_added",
        "clarification_resolution_added",
        "context_builder_added",
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
            "build_008a_verification_v1"
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
        "request_contract_added": True,
        "candidate_selection_recording_added": True,
        "automatic_candidate_selection_added": False,
        "candidate_selection_policy_added": False,
        "request_compiler_runtime_added": False,
        "clarification_resolution_added": False,
        "context_builder_added": False,
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
