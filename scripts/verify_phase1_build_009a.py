#!/usr/bin/env python3
"""Verify Forge 2 Phase 1 Build 009A."""

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

BUILD_ID = "FORGE2-PHASE1-BUILD-009A"
EXPECTED_PARENT = "503ec02599e8d1d92966ff03d3c586296fd07d00"
EXPECTED_SUBJECT = "Establish immutable ContextManifest"
EXPECTED_ORIGIN = "https://github.com/BogaertN/forge2.git"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"
ROADMAP_TITLE = "AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent"
EXPECTED_TEST_COUNT = 224

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_009A_SOURCE_AUTHORITY.json"
)
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_009A_RECEIPT.json"
)
PREDECESSOR_MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_008A_SOURCE_AUTHORITY.json"
)
PREDECESSOR_RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_008A_RECEIPT.json"
)
PREDECESSOR_CORRECTION_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_008A_R2_CORRECTION_RECEIPT.json"
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

FIXED_VECTORS = {"admitted_total_bytes": 107, "excluded_item_byte_count": 32, "excluded_item_content_hash": "60b808a47e97d974c48d0332ae4d80f0761de5dde75c98afac6ceedb9af8d6dc", "excluded_item_id": "aiweb.excluded-context-item:sha256:a4baf1f87e482d9c6b0a5a08c1140e2f716411f67a3f8f21db07bb18aaa0de15", "file_item_byte_count": 65, "file_item_content_hash": "aaf56c50cca67c8f3da808560d61f283f531a45d4d413feda0ea7cff8bbf7712", "file_item_id": "aiweb.context-item:sha256:baedb3701ddf41c9d6f20594b86a0ffc0e2db722ad2b347acd725d36b5681f86", "manifest_content_hash": "97f88513075253d9863c1a0b2aa79173f5254918e20a848e760545c8ba710e0b", "manifest_contract_id": "aiweb.contract:sha256:b07a6d3b5d35c3c0bf348838105299226755d0da200048682c9d42319b2c8a88", "policy_item_byte_count": 42, "policy_item_content_hash": "eafcb0eeb0c2ae6da917255d5b5cb398ea70b8dd57af79138523ec7f658ed1e8", "policy_item_id": "aiweb.context-item:sha256:9aba7d8169b895931565cd186d53841d47c8e424cb62f93d739e0ce21e5fed2e", "repository_snapshot_id": "aiweb.repository-snapshot:sha256:b9516abc6f5d5182a4d1444bfa6aaa32da1e3b88d2cea23eb0bac3ee8375876c"}


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
    correction = load_json(
        PREDECESSOR_CORRECTION_PATH
    )

    if (
        manifest.get("build_id")
        != "FORGE2-PHASE1-BUILD-008A"
        or receipt.get("build_id")
        != "FORGE2-PHASE1-BUILD-008A"
        or receipt.get("status") != "PASS"
        or receipt.get("correction_status")
        != "PASS"
        or correction.get("build_id")
        != "FORGE2-PHASE1-BUILD-008A-R2"
        or correction.get("status") != "PASS"
    ):
        raise VerificationError(
            "Build 008A predecessor evidence mismatch."
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
            "Build 008A manifest binding mismatch."
        )

    return {
        "manifest_sha256": sha256_file(
            PREDECESSOR_MANIFEST_PATH
        ),
        "receipt_sha256": sha256_file(
            PREDECESSOR_RECEIPT_PATH
        ),
        "correction_sha256": sha256_file(
            PREDECESSOR_CORRECTION_PATH
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
            "Build 009A requires zero runtime "
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

    if count != 11:
        raise VerificationError(
            "Expected eleven contract source files, "
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
        "CONTEXT_ITEM_ID_NAMESPACE",
        "CONTEXT_MANIFEST_SCHEMA_VERSION",
        "CONTEXT_MANIFEST_TYPE",
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
        "ContextBudget",
        "ContextItem",
        "ContextItemKind",
        "ContextManifest",
        "ContractIdentityError",
        "ContractIntegrityError",
        "ContractMetadata",
        "ContractReference",
        "ContractValidationError",
        "DeclaredEffect",
        "EXCLUDED_CONTEXT_ITEM_ID_NAMESPACE",
        "EffectKind",
        "ExcludedContextItem",
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
        "REPOSITORY_SNAPSHOT_ID_NAMESPACE",
        "REQUEST_CONTRACT_SCHEMA_VERSION",
        "REQUEST_CONTRACT_TYPE",
        "REQUEST_STATE_ID_NAMESPACE",
        "REQUEST_STATE_REGISTRY",
        "REQUEST_STATE_REGISTRY_NAMESPACE",
        "REQUEST_STATE_SCHEMA_VERSION",
        "REQUEST_STATE_SEQUENCE",
        "REQUEST_STATEMENT_ID_NAMESPACE",
        "RepositorySnapshot",
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
        "context_manifest_from_dict",
        "contract_metadata_from_dict",
        "contract_metadata_to_dict",
        "contract_reference_from_dict",
        "create_candidate_selection",
        "create_classification_candidate",
        "create_classification_candidate_set",
        "create_context_budget",
        "create_context_item",
        "create_context_manifest",
        "create_contract_metadata",
        "create_excluded_context_item",
        "create_feature_evidence",
        "create_input_event",
        "create_repository_snapshot",
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
        "verify_context_manifest",
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
        ContextBudget,
        ContextItem,
        ContextManifest,
        ExcludedContextItem,
        RepositorySnapshot,
    )

    values = (
        RepositorySnapshot,
        ContextBudget,
        ContextItem,
        ExcludedContextItem,
        ContextManifest,
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


def build_fixture() -> dict[str, Any]:
    from forge2.contracts import (
        CandidateDimension,
        CandidateOrigin,
        ContextItemKind,
        RequestStatementKind,
        create_candidate_selection,
        create_classification_candidate,
        create_classification_candidate_set,
        create_context_budget,
        create_context_item,
        create_context_manifest,
        create_excluded_context_item,
        create_feature_evidence,
        create_input_event,
        create_repository_snapshot,
        create_request_contract,
        create_request_statement,
    )

    input_event = create_input_event(
        raw_input=(
            "Inspect RequestContract using only "
            "the exact required source."
        ),
        conversation_context=[],
        identity_context={
            "actor_id": "user:nic",
            "actor_kind": "user",
        },
        session_metadata={
            "channel": "terminal",
            "session_id": "session-009",
        },
        created_at=datetime(
            2026,
            7,
            31,
            2,
            0,
            tzinfo=timezone.utc,
        ),
    )

    request_evidence = create_feature_evidence(
        source_pointer="/raw_input",
        feature_name="request_kind_phrase",
        observed_value="Inspect",
        span_start=0,
        span_end=7,
    )
    result_evidence = create_feature_evidence(
        source_pointer="/raw_input",
        feature_name="expected_result_phrase",
        observed_value="RequestContract",
        span_start=8,
        span_end=23,
    )
    constraint_evidence = create_feature_evidence(
        source_pointer="/raw_input",
        feature_name="context_constraint",
        observed_value=(
            "only the exact required source"
        ),
        span_start=30,
        span_end=60,
    )

    request_candidate = (
        create_classification_candidate(
            dimension=(
                CandidateDimension.REQUEST_KIND
            ),
            label="contract_inspection",
            origin=CandidateOrigin.RULE,
            producer_id=(
                "forge2.rule.request.v1"
            ),
            confidence_basis_points=9900,
            evidence=[request_evidence],
        )
    )
    result_candidate = (
        create_classification_candidate(
            dimension=(
                CandidateDimension
                .EXPECTED_RESULT
            ),
            label="bounded_context_manifest",
            origin=CandidateOrigin.RULE,
            producer_id=(
                "forge2.rule.result.v1"
            ),
            confidence_basis_points=9700,
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
            confidence_basis_points=10000,
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
                31,
                2,
                0,
                1,
                tzinfo=timezone.utc,
            ),
        )
    )

    request_contract = create_request_contract(
        input_event=input_event,
        classification_candidate_set=(
            candidate_set
        ),
        producer_id=(
            "forge2.request-contract."
            "context-fixture.v1"
        ),
        selected_candidates=[
            create_candidate_selection(
                candidate=request_candidate,
                basis_codes=[
                    "exact_request_phrase"
                ],
            ),
            create_candidate_selection(
                candidate=result_candidate,
                basis_codes=[
                    "exact_result_phrase"
                ],
            ),
            create_candidate_selection(
                candidate=effect_candidate,
                basis_codes=[
                    (
                        "explicit_read_only_"
                        "constraint"
                    )
                ],
            ),
        ],
        goals=[
            create_request_statement(
                kind=(
                    RequestStatementKind.GOAL
                ),
                code="inspect_request_contract",
                text="Inspect RequestContract.",
                evidence_ids=[
                    request_evidence.evidence_id,
                    result_evidence.evidence_id,
                ],
            )
        ],
        constraints=[
            create_request_statement(
                kind=(
                    RequestStatementKind
                    .CONSTRAINT
                ),
                code=(
                    "use_only_required_context"
                ),
                text=(
                    "Use only exact required context."
                ),
                evidence_ids=[
                    constraint_evidence.evidence_id
                ],
            )
        ],
        desired_result=(
            create_request_statement(
                kind=(
                    RequestStatementKind
                    .DESIRED_RESULT
                ),
                code=(
                    "bounded_context_manifest"
                ),
                text=(
                    "An exact bounded context manifest."
                ),
                evidence_ids=[
                    result_evidence.evidence_id
                ],
            )
        ),
        uncertainty_codes=[],
        created_at=datetime(
            2026,
            7,
            31,
            2,
            0,
            2,
            tzinfo=timezone.utc,
        ),
    )

    repository = create_repository_snapshot(
        repository_uri=(
            "git+https://github.com/"
            "BogaertN/forge2.git"
        ),
        commit_sha=EXPECTED_PARENT,
    )
    budget = create_context_budget(
        max_items=8,
        max_total_bytes=4096,
        max_item_bytes=2048,
    )
    file_item = create_context_item(
        kind=ContextItemKind.FILE_SLICE,
        source_uri=(
            "repo://BogaertN/forge2/"
            "src/forge2/contracts/"
            "request_contract.py"
        ),
        source_revision=EXPECTED_PARENT,
        locator="lines:1-20",
        content=(
            "RequestContract records one selected "
            "structured interpretation."
        ),
        admission_basis_codes=[
            "request_contract_dependency"
        ],
    )
    policy_item = create_context_item(
        kind=ContextItemKind.POLICY,
        source_uri=f"gdoc://{ROADMAP_ID}",
        source_revision=(
            "controlling-production-roadmap-2026-07-30"
        ),
        locator="section:10.3",
        content={
            "required": True,
            "rule": "bounded_context",
        },
        admission_basis_codes=[
            "controlling_build_bible"
        ],
    )
    excluded_item = create_excluded_context_item(
        kind=ContextItemKind.DOCUMENTATION,
        source_uri=(
            "repo://BogaertN/forge2/README.md"
        ),
        source_revision=EXPECTED_PARENT,
        locator="lines:1-10",
        content="Unrelated repository overview.",
        reason_code="not_needed_for_step",
        reason_text=(
            "The overview is not required "
            "to inspect RequestContract."
        ),
    )
    manifest = create_context_manifest(
        request_contract=request_contract,
        step_id="step.inspect_request_contract",
        repository=repository,
        budget=budget,
        producer_id=(
            "forge2.context-manifest.fixture.v1"
        ),
        admitted_items=[
            file_item,
            policy_item,
        ],
        excluded_items=[excluded_item],
        created_at=datetime(
            2026,
            7,
            31,
            2,
            0,
            3,
            tzinfo=timezone.utc,
        ),
    )

    return {
        "request_contract": request_contract,
        "repository": repository,
        "file_item": file_item,
        "policy_item": policy_item,
        "excluded_item": excluded_item,
        "manifest": manifest,
    }


def verify_behavior() -> dict[str, Any]:
    import forge2.contracts.context_manifest as module
    from forge2.contracts import (
        AuthorityStatus,
        canonical_json,
        context_manifest_from_dict,
        verify_context_manifest,
    )

    fixture = build_fixture()
    request_contract = fixture[
        "request_contract"
    ]
    manifest = fixture["manifest"]

    observed = {
        "repository_snapshot_id": (
            fixture["repository"].snapshot_id
        ),
        "file_item_id": (
            fixture["file_item"].item_id
        ),
        "file_item_content_hash": (
            fixture["file_item"].content_hash
        ),
        "file_item_byte_count": (
            fixture["file_item"].byte_count
        ),
        "policy_item_id": (
            fixture["policy_item"].item_id
        ),
        "policy_item_content_hash": (
            fixture["policy_item"].content_hash
        ),
        "policy_item_byte_count": (
            fixture["policy_item"].byte_count
        ),
        "excluded_item_id": (
            fixture["excluded_item"]
            .exclusion_id
        ),
        "excluded_item_content_hash": (
            fixture["excluded_item"]
            .content_hash
        ),
        "excluded_item_byte_count": (
            fixture["excluded_item"]
            .byte_count
        ),
        "manifest_content_hash": (
            manifest.metadata.content_hash
        ),
        "manifest_contract_id": (
            manifest.metadata.contract_id
        ),
        "admitted_total_bytes": (
            manifest.admitted_total_bytes
        ),
    }

    if observed != FIXED_VECTORS:
        raise VerificationError(
            "ContextManifest fixed vectors mismatch."
        )

    verify_context_manifest(
        manifest,
        request_contract=request_contract,
    )

    serialized = canonical_json(
        manifest.to_dict()
    )
    restored = context_manifest_from_dict(
        json.loads(serialized),
        request_contract=request_contract,
    )

    if (
        restored != manifest
        or canonical_json(
            restored.to_dict()
        )
        != serialized
        or (
            manifest
            .metadata
            .authority_status
            != AuthorityStatus.NONE
        )
        or manifest.metadata.declared_effects != ()
        or len(manifest.admitted_items) != 2
        or len(manifest.excluded_items) != 1
    ):
        raise VerificationError(
            "ContextManifest behavioral boundary failed."
        )

    excluded_serialized = (
        manifest.to_dict()
        ["body"]
        ["excluded_items"]
        [0]
    )

    if "content" in excluded_serialized:
        raise VerificationError(
            "Excluded content entered admitted payload."
        )

    for name in (
        "retrieve_context",
        "rank_context",
        "select_context",
        "build_context",
        "promote_memory",
        "plan_task",
        "authorize_context",
        "execute_context",
    ):
        if hasattr(module, name):
            raise VerificationError(
                "Premature context runtime API found: "
                f"{name}"
            )

    return {
        **observed,
        "round_trip": True,
        "authority_status": "none",
        "declared_effect_count": 0,
        "admitted_item_count": 2,
        "excluded_item_count": 1,
        "automatic_retrieval_performed": False,
        "automatic_selection_performed": False,
        "memory_promoted": False,
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
        or roadmap.get("title")
        != ROADMAP_TITLE
    ):
        raise VerificationError(
            "Manifest controlling-roadmap mismatch."
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

    anchor_paths = {
        "canonical_py_sha256": (
            "src/forge2/contracts/canonical.py"
        ),
        "identity_py_sha256": (
            "src/forge2/contracts/identity.py"
        ),
        "successor_py_sha256": (
            "src/forge2/contracts/successor.py"
        ),
        "request_state_py_sha256": (
            "src/forge2/contracts/request_state.py"
        ),
        "frozen_value_py_sha256": (
            "src/forge2/contracts/frozen_value.py"
        ),
        "codec_py_sha256": (
            "src/forge2/contracts/codec.py"
        ),
        "input_event_py_sha256": (
            "src/forge2/contracts/input_event.py"
        ),
        "classification_candidate_py_sha256": (
            "src/forge2/contracts/"
            "classification_candidate.py"
        ),
        "request_contract_py_sha256": (
            "src/forge2/contracts/"
            "request_contract.py"
        ),
    }

    for key, relative in anchor_paths.items():
        if (
            anchors.get(key)
            != sha256_file(ROOT / relative)
        ):
            raise VerificationError(
                f"Predecessor anchor mismatch: {key}"
            )

    if (
        manifest.get("expected_test_count")
        != EXPECTED_TEST_COUNT
    ):
        raise VerificationError(
            "Manifest test count mismatch."
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
            "context_manifest_added"
        ) is not True
        or receipt.get(
            "repository_snapshot_added"
        ) is not True
        or receipt.get(
            "context_budget_added"
        ) is not True
        or receipt.get(
            "explicit_admission_records_added"
        ) is not True
        or receipt.get(
            "explicit_exclusion_records_added"
        ) is not True
        or receipt.get(
            "expected_test_count"
        )
        != EXPECTED_TEST_COUNT
    ):
        raise VerificationError(
            "Receipt identity mismatch."
        )

    for field in (
        "forge1_modified",
        "forge1_source_copied",
        "forge1_donor_admitted",
        "external_dependency_admitted",
        "automatic_context_retrieval_added",
        "automatic_context_ranking_added",
        "automatic_context_selection_added",
        "context_builder_runtime_added",
        "stale_context_detection_added",
        "planner_added",
        "memory_promotion_added",
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
            "build_009a_verification_v1"
        ),
        "build_id": BUILD_ID,
        "controlling_roadmap": {
            "title": ROADMAP_TITLE,
            "document_id": ROADMAP_ID,
            "sections": [
                "3.2 Source custody",
                "8. Contract Architecture",
                "10.3 Context manifest",
                "10.4 Context versus memory",
            ],
        },
        "mode": arguments.mode,
        "status": "PASS",
        "phase_status": "PHASE_1_IN_PROGRESS",
        "expected_test_count": EXPECTED_TEST_COUNT,
        "contract_source_count": source_count,
        "public_api": list(public_api),
        "immutable_types": immutable_types,
        "fixed_vectors": fixed_vectors,
        "predecessor": predecessor,
        "manifest_file_count": len(
            manifest["files"]
        ),
        "receipt_status": receipt["status"],
        "context_manifest_added": True,
        "repository_snapshot_added": True,
        "context_budget_added": True,
        "explicit_admission_records_added": True,
        "explicit_exclusion_records_added": True,
        "automatic_context_retrieval_added": False,
        "automatic_context_ranking_added": False,
        "automatic_context_selection_added": False,
        "context_builder_runtime_added": False,
        "stale_context_detection_added": False,
        "planner_added": False,
        "memory_promotion_added": False,
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
