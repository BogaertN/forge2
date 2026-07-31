#!/usr/bin/env python3
"""Verify Forge 2 Phase 1 Build 010A-R2."""

from __future__ import annotations

import argparse
import ast
from dataclasses import is_dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
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

BUILD_ID = "FORGE2-PHASE1-BUILD-010A-R2"
ORIGINAL_BUILD_ID = "FORGE2-PHASE1-BUILD-010A"
EXPECTED_PARENT = "6d2e6b6560b78a490500aded6428e6f768987c81"
EXPECTED_SUBJECT = "Establish immutable CapabilityRequirement"
EXPECTED_ORIGIN = "https://github.com/BogaertN/forge2.git"
EXPECTED_TEST_COUNT = 272
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"
ROADMAP_TITLE = "AI.Web Forge 2.0 Production Build Bible — Open-Source-First Non-LLM Self-Constructing Engineering Agent"

MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_010A_SOURCE_AUTHORITY.json"
)
RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_010A_RECEIPT.json"
)
CORRECTION_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_010A_R2_CORRECTION_RECEIPT.json"
)
PREDECESSOR_MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "PHASE1_BUILD_009A_SOURCE_AUTHORITY.json"
)
PREDECESSOR_RECEIPT_PATH = (
    ROOT
    / "receipts"
    / "PHASE1_BUILD_009A_RECEIPT.json"
)
TEST_PATH = (
    ROOT
    / "tests"
    / "contracts"
    / "test_capability_requirement.py"
)

FIXED_VECTORS = {"acceptance_criterion_count": 1, "capability_requirement_content_hash": "e76690e8b55576bf4ab1bc1b6fcf5a3771e46a48e54ece6972c2dde51fb74958", "capability_requirement_contract_id": "aiweb.contract:sha256:ebaf6ca262d8efe08672f476bf8536b7aa5fb023cfabf4076195c3a20541fb09", "criterion_id": "aiweb.capability-acceptance-criterion:sha256:c2f9fa586ddc53035f99c7835e6c997defac514e3cb540a6454113d875f7686b", "input_requirement_count": 1, "input_requirement_id": "aiweb.capability-data-requirement:sha256:ce9552d3558f398a1fa914ab18cd821aa6f028ed5b80d90a1c2f20cc74bb379d", "output_requirement_count": 1, "output_requirement_id": "aiweb.capability-data-requirement:sha256:618dc158780f4f06d98b3381dfea423e43c19160e3736eb828fd5cb2c5d2cff5", "side_effect_class": "read_only", "side_effect_selection_id": "aiweb.candidate-selection:sha256:362ece729c78221a4baf8cdaf3712b693c0dff0b4fdd661d925b19953c12cf9a"}

ALLOWED_IMPORT_ROOTS = {
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

PROVIDER_FIELDS = {
    "provider_id",
    "provider_name",
    "package_name",
    "tool_name",
    "version",
    "command",
    "endpoint",
    "executable",
    "adapter",
    "qualification_score",
}


class VerificationError(RuntimeError):
    pass


def run(arguments: list[str]):
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
            f"JSON object required: {path}"
        )

    return value


def normalize_url(value: str) -> str:
    normalized = value.strip().rstrip("/")

    if normalized.endswith(".git"):
        normalized = normalized[:-4]

    return normalized


def load_test_module():
    spec = importlib.util.spec_from_file_location(
        "forge2_build010a_tests",
        TEST_PATH,
    )

    if spec is None or spec.loader is None:
        raise VerificationError(
            "Could not load CapabilityRequirement tests."
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def verify_predecessor() -> None:
    manifest = load_json(
        PREDECESSOR_MANIFEST_PATH
    )
    receipt = load_json(
        PREDECESSOR_RECEIPT_PATH
    )

    if (
        manifest.get("build_id")
        != "FORGE2-PHASE1-BUILD-009A"
        or receipt.get("build_id")
        != "FORGE2-PHASE1-BUILD-009A"
        or receipt.get("status") != "PASS"
        or receipt.get(
            "context_manifest_added"
        )
        is not True
        or receipt.get(
            "source_authority_manifest_sha256"
        )
        != sha256_file(
            PREDECESSOR_MANIFEST_PATH
        )
    ):
        raise VerificationError(
            "Build 009A predecessor evidence mismatch."
        )


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
            "Build 010A requires zero runtime dependencies."
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
                    f"Forbidden token {token!r} in {path}"
                )

        for node in ast.walk(tree):
            roots: list[str] = []

            if isinstance(node, ast.Import):
                roots = [
                    alias.name.split(".", 1)[0]
                    for alias in node.names
                ]

            if (
                isinstance(node, ast.ImportFrom)
                and node.level == 0
            ):
                roots = [
                    (node.module or "")
                    .split(".", 1)[0]
                ]

            unexpected = [
                root
                for root in roots
                if (
                    root
                    and root
                    not in ALLOWED_IMPORT_ROOTS
                )
            ]

            if unexpected:
                raise VerificationError(
                    f"Unexpected import in {path}: "
                    + ", ".join(unexpected)
                )

        count += 1

    if count != 12:
        raise VerificationError(
            f"Expected 12 contract files, found {count}."
        )

    return count


def verify_public_api(
    manifest: dict[str, Any],
) -> int:
    import forge2.contracts as contracts

    expected = manifest.get(
        "expected_public_api"
    )

    if (
        not isinstance(expected, list)
        or tuple(expected) != contracts.__all__
        or len(expected) != len(set(expected))
    ):
        raise VerificationError(
            "Contract public API mismatch."
        )

    required = {
        "CapabilityAcceptanceCriterion",
        "CapabilityDataDirection",
        "CapabilityDataRequirement",
        "CapabilityRequirement",
        "capability_requirement_from_dict",
        "create_capability_acceptance_criterion",
        "create_capability_data_requirement",
        "create_capability_requirement",
        "verify_capability_requirement",
    }

    if not required.issubset(set(expected)):
        raise VerificationError(
            "CapabilityRequirement public API is incomplete."
        )

    return len(expected)


def verify_immutable_types() -> list[str]:
    from forge2.contracts import (
        CapabilityAcceptanceCriterion,
        CapabilityDataRequirement,
        CapabilityRequirement,
    )

    values = (
        CapabilityDataRequirement,
        CapabilityAcceptanceCriterion,
        CapabilityRequirement,
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
                f"{value.__name__} is not frozen and slotted."
            )

        names.append(value.__name__)

    return names


def verify_behavior() -> dict[str, Any]:
    import forge2.contracts.capability_requirement as module
    from forge2.contracts import (
        AuthorityStatus,
        canonical_json,
        capability_requirement_from_dict,
        create_capability_requirement,
        verify_capability_requirement,
    )

    test_module = load_test_module()
    fixture = test_module.build_reference_fixture()

    requirement = create_capability_requirement(
        request_contract=fixture["request_contract"],
        context_manifest=fixture["context_manifest"],
        producer_id=(
            "forge2.capability-requirement.fixture.v1"
        ),
        requirement_code=(
            "describe_required_capability"
        ),
        behavior_description=(
            "Describe the behavior required to inspect "
            "RequestContract without assuming a provider."
        ),
        behavior_statement_ids=[
            fixture["goal"].statement_id,
            fixture["desired_result"].statement_id,
        ],
        input_requirements=[
            fixture["input_requirement"]
        ],
        output_requirements=[
            fixture["output_requirement"]
        ],
        required_property_codes=[
            "authority_neutral",
            "provider_neutral",
            "reproducible",
        ],
        acceptance_criteria=[
            fixture["criterion"]
        ],
        uncertainty_codes=[
            "provider_resolution_pending"
        ],
        created_at=datetime(
            2026,
            7,
            31,
            14,
            30,
            4,
            tzinfo=timezone.utc,
        ),
    )

    observed = {
        "input_requirement_id": (
            fixture[
                "input_requirement"
            ].requirement_id
        ),
        "output_requirement_id": (
            fixture[
                "output_requirement"
            ].requirement_id
        ),
        "criterion_id": (
            fixture["criterion"].criterion_id
        ),
        "side_effect_selection_id": (
            requirement.side_effect_selection_id
        ),
        "side_effect_class": (
            requirement.side_effect_class
        ),
        "capability_requirement_content_hash": (
            requirement.metadata.content_hash
        ),
        "capability_requirement_contract_id": (
            requirement.metadata.contract_id
        ),
        "input_requirement_count": len(
            requirement.input_requirements
        ),
        "output_requirement_count": len(
            requirement.output_requirements
        ),
        "acceptance_criterion_count": len(
            requirement.acceptance_criteria
        ),
    }

    if observed != FIXED_VECTORS:
        raise VerificationError(
            "CapabilityRequirement fixed vectors mismatch."
        )

    verify_capability_requirement(
        requirement,
        request_contract=fixture["request_contract"],
        context_manifest=fixture["context_manifest"],
    )

    serialized = canonical_json(
        requirement.to_dict()
    )
    restored = capability_requirement_from_dict(
        json.loads(serialized),
        request_contract=fixture["request_contract"],
        context_manifest=fixture["context_manifest"],
    )

    if (
        restored != requirement
        or canonical_json(
            restored.to_dict()
        )
        != serialized
        or (
            requirement
            .metadata
            .authority_status
            != AuthorityStatus.NONE
        )
        or requirement.metadata.declared_effects != ()
    ):
        raise VerificationError(
            "CapabilityRequirement behavior failed."
        )

    body = requirement.to_dict()["body"]

    if PROVIDER_FIELDS & set(body):
        raise VerificationError(
            "Provider fields entered the requirement body."
        )

    for name in (
        "discover_provider",
        "rank_provider",
        "select_provider",
        "resolve_provider",
        "install_package",
        "register_capability",
        "qualify_tool",
        "create_capability_contract",
        "create_tool_candidate",
        "plan_task",
        "authorize_capability",
        "execute_capability",
    ):
        if hasattr(module, name):
            raise VerificationError(
                f"Premature runtime API found: {name}"
            )

    return {
        **observed,
        "round_trip": True,
        "authority_status": "none",
        "provider_selected": False,
        "discovery_performed": False,
        "qualification_performed": False,
    }


def verify_manifest() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH)

    if (
        manifest.get("build_id")
        != ORIGINAL_BUILD_ID
        or manifest.get("correction_build_id")
        != BUILD_ID
        or manifest.get("expected_parent")
        != EXPECTED_PARENT
        or manifest.get("expected_test_count")
        != EXPECTED_TEST_COUNT
    ):
        raise VerificationError(
            "Build 010A manifest identity mismatch."
        )

    roadmap = manifest.get(
        "controlling_roadmap"
    )

    if (
        not isinstance(roadmap, dict)
        or roadmap.get("title")
        != ROADMAP_TITLE
        or roadmap.get("document_id")
        != ROADMAP_ID
    ):
        raise VerificationError(
            "Controlling roadmap mismatch."
        )

    correction = manifest.get("correction")

    if (
        not isinstance(correction, dict)
        or correction.get("correct_span")
        != {"start": 60, "end": 87}
        or correction.get("corrected_occurrences")
        != 3
        or correction.get(
            "baseline_verifier_isolated"
        )
        is not True
    ):
        raise VerificationError(
            "Build 010A-R2 correction manifest mismatch."
        )

    files = manifest.get("files")

    if not isinstance(files, list):
        raise VerificationError(
            "Manifest file list missing."
        )

    for entry in files:
        if not isinstance(entry, dict):
            raise VerificationError(
                "Invalid manifest file entry."
            )

        relative = entry.get("path")
        path = ROOT / str(relative)

        if (
            not path.is_file()
            or sha256_file(path)
            != entry.get("sha256")
            or path.stat().st_size
            != entry.get("size_bytes")
        ):
            raise VerificationError(
                f"Manifest file mismatch: {relative}"
            )

    return manifest


def verify_receipts() -> None:
    receipt = load_json(RECEIPT_PATH)
    correction = load_json(CORRECTION_PATH)

    if (
        receipt.get("build_id")
        != ORIGINAL_BUILD_ID
        or receipt.get("correction_build_id")
        != BUILD_ID
        or receipt.get("status") != "PASS"
        or receipt.get(
            "capability_requirement_added"
        )
        is not True
        or receipt.get(
            "source_authority_manifest_sha256"
        )
        != sha256_file(MANIFEST_PATH)
    ):
        raise VerificationError(
            "Build 010A receipt mismatch."
        )

    if (
        correction.get("build_id") != BUILD_ID
        or correction.get("status") != "PASS"
        or correction.get(
            "corrected_fixture_occurrences"
        )
        != 3
        or correction.get(
            "test_expectation_weakened"
        )
        is not False
        or correction.get("correct_span")
        != {"start": 60, "end": 87}
        or correction.get(
            "r2_baseline_verifier_isolated"
        )
        is not True
    ):
        raise VerificationError(
            "Build 010A-R2 correction receipt mismatch."
        )

    for field in (
        "provider_identity_added",
        "package_name_assumption_added",
        "tool_name_assumption_added",
        "capability_registry_runtime_added",
        "capability_contract_added",
        "tool_candidate_added",
        "provider_discovery_added",
        "provider_ranking_added",
        "provider_selection_added",
        "qualification_runtime_added",
        "planner_added",
        "request_transition_policy_defined",
        "runtime_authority_added",
        "product_capability_claimed",
    ):
        if receipt.get(field) is not False:
            raise VerificationError(
                f"Receipt boundary mismatch: {field}"
            )


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
            "Git origin mismatch."
        )

    result = {
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

        result.update(
            {
                "head": head.stdout.strip(),
                "parent": parent.stdout.strip(),
                "subject": subject.stdout.strip(),
            }
        )

    return result


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

    verify_predecessor()
    verify_dependencies()
    source_count = verify_sources()
    manifest = verify_manifest()
    public_api_count = verify_public_api(
        manifest
    )
    immutable_types = verify_immutable_types()
    behavior = verify_behavior()
    verify_receipts()
    git_state = verify_git(arguments.mode)

    print(
        json.dumps(
            {
                "schema_version": (
                    "aiweb_forge2_phase1_"
                    "build_010a_r2_verification_v1"
                ),
                "build_id": BUILD_ID,
                "corrected_build_id": (
                    ORIGINAL_BUILD_ID
                ),
                "status": "PASS",
                "mode": arguments.mode,
                "phase_status": (
                    "PHASE_1_IN_PROGRESS"
                ),
                "expected_test_count": (
                    EXPECTED_TEST_COUNT
                ),
                "contract_source_count": (
                    source_count
                ),
                "public_api_count": (
                    public_api_count
                ),
                "immutable_types": (
                    immutable_types
                ),
                "fixed_vectors": behavior,
                "fixture_span_corrections": 3,
                "baseline_verifier_isolated": True,
                "test_expectation_weakened": False,
                "capability_requirement_added": True,
                "provider_selected": False,
                "capability_contract_added": False,
                "tool_candidate_added": False,
                "discovery_runtime_added": False,
                "qualification_runtime_added": False,
                "planner_added": False,
                "runtime_authority_added": False,
                "product_capability_claimed": False,
                "git": git_state,
            },
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
