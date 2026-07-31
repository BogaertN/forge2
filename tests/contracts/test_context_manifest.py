"""Invariant tests for immutable ContextManifest."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import json
import unittest

import forge2.contracts.context_manifest as module
from forge2.contracts import (
    AuthorityStatus,
    CandidateDimension,
    CandidateOrigin,
    ContextBudget,
    ContextItemKind,
    ContractIntegrityError,
    ContractValidationError,
    EffectKind,
    RequestStatementKind,
    canonical_json,
    context_manifest_from_dict,
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
    verify_context_manifest,
)


PARENT_COMMIT = "503ec02599e8d1d92966ff03d3c586296fd07d00"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"


class ContextManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request_contract = (
            self._make_request_contract(
                producer_id=(
                    "forge2.request-contract."
                    "context-fixture.v1"
                )
            )
        )

        self.repository = (
            create_repository_snapshot(
                repository_uri=(
                    "git+https://github.com/"
                    "BogaertN/forge2.git"
                ),
                commit_sha=PARENT_COMMIT,
            )
        )
        self.budget = create_context_budget(
            max_items=8,
            max_total_bytes=4096,
            max_item_bytes=2048,
        )
        self.file_item = create_context_item(
            kind=ContextItemKind.FILE_SLICE,
            source_uri=(
                "repo://BogaertN/forge2/"
                "src/forge2/contracts/"
                "request_contract.py"
            ),
            source_revision=PARENT_COMMIT,
            locator="lines:1-20",
            content=(
                "RequestContract records one "
                "selected structured interpretation."
            ),
            admission_basis_codes=[
                "request_contract_dependency"
            ],
        )
        self.policy_item = create_context_item(
            kind=ContextItemKind.POLICY,
            source_uri=(
                f"gdoc://{ROADMAP_ID}"
            ),
            source_revision=(
                "controlling-production-"
                "roadmap-2026-07-30"
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
        self.excluded_item = (
            create_excluded_context_item(
                kind=(
                    ContextItemKind
                    .DOCUMENTATION
                ),
                source_uri=(
                    "repo://BogaertN/forge2/"
                    "README.md"
                ),
                source_revision=PARENT_COMMIT,
                locator="lines:1-10",
                content=(
                    "Unrelated repository overview."
                ),
                reason_code=(
                    "not_needed_for_step"
                ),
                reason_text=(
                    "The overview is not required "
                    "to inspect RequestContract."
                ),
            )
        )
        self.created_at = datetime(
            2026,
            7,
            31,
            2,
            0,
            3,
            tzinfo=timezone.utc,
        )

    def _make_request_contract(
        self,
        *,
        producer_id: str,
    ):
        input_event = create_input_event(
            raw_input=(
                "Inspect RequestContract using "
                "only the exact required source."
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

        request_evidence = (
            create_feature_evidence(
                source_pointer="/raw_input",
                feature_name=(
                    "request_kind_phrase"
                ),
                observed_value="Inspect",
                span_start=0,
                span_end=7,
            )
        )
        result_evidence = (
            create_feature_evidence(
                source_pointer="/raw_input",
                feature_name=(
                    "expected_result_phrase"
                ),
                observed_value=(
                    "RequestContract"
                ),
                span_start=8,
                span_end=23,
            )
        )
        constraint_evidence = (
            create_feature_evidence(
                source_pointer="/raw_input",
                feature_name=(
                    "context_constraint"
                ),
                observed_value=(
                    "only the exact required source"
                ),
                span_start=30,
                span_end=60,
            )
        )

        request_candidate = (
            create_classification_candidate(
                dimension=(
                    CandidateDimension
                    .REQUEST_KIND
                ),
                label="contract_inspection",
                origin=CandidateOrigin.RULE,
                producer_id=(
                    "forge2.rule.request.v1"
                ),
                confidence_basis_points=9900,
                evidence=[
                    request_evidence
                ],
            )
        )
        result_candidate = (
            create_classification_candidate(
                dimension=(
                    CandidateDimension
                    .EXPECTED_RESULT
                ),
                label=(
                    "bounded_context_manifest"
                ),
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
                evidence=[
                    constraint_evidence
                ],
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

        selections = [
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
        ]

        goal = create_request_statement(
            kind=RequestStatementKind.GOAL,
            code="inspect_request_contract",
            text="Inspect RequestContract.",
            evidence_ids=[
                request_evidence.evidence_id,
                result_evidence.evidence_id,
            ],
        )
        constraint = create_request_statement(
            kind=(
                RequestStatementKind.CONSTRAINT
            ),
            code="use_only_required_context",
            text=(
                "Use only exact required context."
            ),
            evidence_ids=[
                constraint_evidence.evidence_id
            ],
        )
        desired_result = (
            create_request_statement(
                kind=(
                    RequestStatementKind
                    .DESIRED_RESULT
                ),
                code=(
                    "bounded_context_manifest"
                ),
                text=(
                    "An exact bounded "
                    "context manifest."
                ),
                evidence_ids=[
                    result_evidence.evidence_id
                ],
            )
        )

        return create_request_contract(
            input_event=input_event,
            classification_candidate_set=(
                candidate_set
            ),
            producer_id=producer_id,
            selected_candidates=selections,
            goals=[goal],
            constraints=[constraint],
            desired_result=desired_result,
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

    def create(self):
        return create_context_manifest(
            request_contract=(
                self.request_contract
            ),
            step_id=(
                "step.inspect_request_contract"
            ),
            repository=self.repository,
            budget=self.budget,
            producer_id=(
                "forge2.context-manifest."
                "fixture.v1"
            ),
            admitted_items=[
                self.file_item,
                self.policy_item,
            ],
            excluded_items=[
                self.excluded_item
            ],
            created_at=self.created_at,
        )

    def test_fixed_repository_snapshot(
        self,
    ) -> None:
        self.assertEqual(
            self.repository.snapshot_id,
            "aiweb.repository-snapshot:sha256:b9516abc6f5d5182a4d1444bfa6aaa32da1e3b88d2cea23eb0bac3ee8375876c",
        )

    def test_fixed_file_item_vector(
        self,
    ) -> None:
        self.assertEqual(
            self.file_item.item_id,
            "aiweb.context-item:sha256:baedb3701ddf41c9d6f20594b86a0ffc0e2db722ad2b347acd725d36b5681f86",
        )
        self.assertEqual(
            self.file_item.content_hash,
            "aaf56c50cca67c8f3da808560d61f283f531a45d4d413feda0ea7cff8bbf7712",
        )
        self.assertEqual(
            self.file_item.byte_count,
            65,
        )

    def test_fixed_policy_item_vector(
        self,
    ) -> None:
        self.assertEqual(
            self.policy_item.item_id,
            "aiweb.context-item:sha256:9aba7d8169b895931565cd186d53841d47c8e424cb62f93d739e0ce21e5fed2e",
        )
        self.assertEqual(
            self.policy_item.content_hash,
            "eafcb0eeb0c2ae6da917255d5b5cb398ea70b8dd57af79138523ec7f658ed1e8",
        )
        self.assertEqual(
            self.policy_item.byte_count,
            42,
        )

    def test_fixed_exclusion_vector(
        self,
    ) -> None:
        self.assertEqual(
            self.excluded_item.exclusion_id,
            "aiweb.excluded-context-item:sha256:a4baf1f87e482d9c6b0a5a08c1140e2f716411f67a3f8f21db07bb18aaa0de15",
        )
        self.assertEqual(
            self.excluded_item.content_hash,
            "60b808a47e97d974c48d0332ae4d80f0761de5dde75c98afac6ceedb9af8d6dc",
        )
        self.assertEqual(
            self.excluded_item.byte_count,
            32,
        )

    def test_fixed_manifest_vector(
        self,
    ) -> None:
        manifest = self.create()

        self.assertEqual(
            manifest.metadata.content_hash,
            "97f88513075253d9863c1a0b2aa79173f5254918e20a848e760545c8ba710e0b",
        )
        self.assertEqual(
            manifest.metadata.contract_id,
            "aiweb.contract:sha256:b07a6d3b5d35c3c0bf348838105299226755d0da200048682c9d42319b2c8a88",
        )
        self.assertEqual(
            manifest.admitted_total_bytes,
            107,
        )

    def test_manifest_is_authority_neutral(
        self,
    ) -> None:
        manifest = self.create()

        self.assertEqual(
            manifest
            .metadata
            .authority_status,
            AuthorityStatus.NONE,
        )
        self.assertEqual(
            manifest
            .metadata
            .declared_effects,
            (),
        )

    def test_round_trip(self) -> None:
        manifest = self.create()
        serialized = canonical_json(
            manifest.to_dict()
        )
        restored = context_manifest_from_dict(
            json.loads(serialized),
            request_contract=(
                self.request_contract
            ),
        )

        self.assertEqual(
            restored,
            manifest,
        )
        self.assertEqual(
            canonical_json(
                restored.to_dict()
            ),
            serialized,
        )

    def test_manifest_is_immutable(
        self,
    ) -> None:
        manifest = self.create()

        with self.assertRaises(
            FrozenInstanceError
        ):
            manifest.step_id = "changed"

    def test_repository_is_immutable(
        self,
    ) -> None:
        with self.assertRaises(
            FrozenInstanceError
        ):
            self.repository.commit_sha = (
                "0" * 40
            )

    def test_budget_is_immutable(
        self,
    ) -> None:
        with self.assertRaises(
            FrozenInstanceError
        ):
            self.budget.max_items = 1

    def test_context_item_is_immutable(
        self,
    ) -> None:
        with self.assertRaises(
            FrozenInstanceError
        ):
            self.file_item.locator = "changed"

    def test_excluded_item_is_immutable(
        self,
    ) -> None:
        with self.assertRaises(
            FrozenInstanceError
        ):
            self.excluded_item.reason_code = (
                "changed"
            )

    def test_source_mutation_has_no_effect(
        self,
    ) -> None:
        source = {
            "required": True,
            "nested": ["a"],
        }
        item = create_context_item(
            kind=ContextItemKind.POLICY,
            source_uri=f"gdoc://{ROADMAP_ID}",
            source_revision="revision-1",
            locator="section:10.3",
            content=source,
            admission_basis_codes=[
                "controlling_build_bible"
            ],
        )
        original = item.to_dict()

        source["required"] = False
        source["nested"].append("b")

        self.assertEqual(
            item.to_dict(),
            original,
        )

    def test_admitted_order_is_canonical(
        self,
    ) -> None:
        first = create_context_manifest(
            request_contract=(
                self.request_contract
            ),
            step_id=(
                "step.inspect_request_contract"
            ),
            repository=self.repository,
            budget=self.budget,
            producer_id=(
                "forge2.context-manifest."
                "fixture.v1"
            ),
            admitted_items=[
                self.file_item,
                self.policy_item,
            ],
            excluded_items=[
                self.excluded_item
            ],
            created_at=self.created_at,
        )
        second = create_context_manifest(
            request_contract=(
                self.request_contract
            ),
            step_id=(
                "step.inspect_request_contract"
            ),
            repository=self.repository,
            budget=self.budget,
            producer_id=(
                "forge2.context-manifest."
                "fixture.v1"
            ),
            admitted_items=[
                self.policy_item,
                self.file_item,
            ],
            excluded_items=[
                self.excluded_item
            ],
            created_at=self.created_at,
        )

        self.assertEqual(first, second)

    def test_excluded_order_is_canonical(
        self,
    ) -> None:
        second_exclusion = (
            create_excluded_context_item(
                kind=(
                    ContextItemKind
                    .PRIOR_TASK_RESULT
                ),
                source_uri=(
                    "task-result://prior-001"
                ),
                source_revision="result-1",
                locator="result",
                content={"status": "held"},
                reason_code="not_current_step",
                reason_text=(
                    "The prior result is not "
                    "required for this step."
                ),
            )
        )

        first = create_context_manifest(
            request_contract=(
                self.request_contract
            ),
            step_id=(
                "step.inspect_request_contract"
            ),
            repository=self.repository,
            budget=self.budget,
            producer_id=(
                "forge2.context-manifest."
                "fixture.v1"
            ),
            admitted_items=[
                self.file_item
            ],
            excluded_items=[
                self.excluded_item,
                second_exclusion,
            ],
            created_at=self.created_at,
        )
        second = create_context_manifest(
            request_contract=(
                self.request_contract
            ),
            step_id=(
                "step.inspect_request_contract"
            ),
            repository=self.repository,
            budget=self.budget,
            producer_id=(
                "forge2.context-manifest."
                "fixture.v1"
            ),
            admitted_items=[
                self.file_item
            ],
            excluded_items=[
                second_exclusion,
                self.excluded_item,
            ],
            created_at=self.created_at,
        )

        self.assertEqual(first, second)

    def test_admitted_context_required(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_context_manifest(
                request_contract=(
                    self.request_contract
                ),
                step_id="step.empty",
                repository=self.repository,
                budget=self.budget,
                producer_id=(
                    "forge2.context-manifest."
                    "fixture.v1"
                ),
                admitted_items=[],
                excluded_items=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "admitted_context_required",
        )

    def test_admission_basis_required(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_context_item(
                kind=ContextItemKind.POLICY,
                source_uri=f"gdoc://{ROADMAP_ID}",
                source_revision="revision-1",
                locator="section:10.3",
                content={"required": True},
                admission_basis_codes=[],
            )

        self.assertEqual(
            context.exception.code,
            "code_required",
        )

    def test_item_count_budget(
        self,
    ) -> None:
        budget = create_context_budget(
            max_items=1,
            max_total_bytes=4096,
            max_item_bytes=2048,
        )

        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_context_manifest(
                request_contract=(
                    self.request_contract
                ),
                step_id=(
                    "step.inspect_request_contract"
                ),
                repository=self.repository,
                budget=budget,
                producer_id=(
                    "forge2.context-manifest."
                    "fixture.v1"
                ),
                admitted_items=[
                    self.file_item,
                    self.policy_item,
                ],
                excluded_items=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "context_item_budget_exceeded",
        )

    def test_total_byte_budget(
        self,
    ) -> None:
        budget = create_context_budget(
            max_items=8,
            max_total_bytes=1,
            max_item_bytes=1,
        )

        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_context_manifest(
                request_contract=(
                    self.request_contract
                ),
                step_id=(
                    "step.inspect_request_contract"
                ),
                repository=self.repository,
                budget=budget,
                producer_id=(
                    "forge2.context-manifest."
                    "fixture.v1"
                ),
                admitted_items=[
                    self.file_item
                ],
                excluded_items=[],
                created_at=self.created_at,
            )

        self.assertIn(
            context.exception.code,
            {
                "context_per_item_budget_exceeded",
                "context_total_budget_exceeded",
            },
        )

    def test_per_item_byte_budget(
        self,
    ) -> None:
        budget = create_context_budget(
            max_items=8,
            max_total_bytes=4096,
            max_item_bytes=1,
        )

        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_context_manifest(
                request_contract=(
                    self.request_contract
                ),
                step_id=(
                    "step.inspect_request_contract"
                ),
                repository=self.repository,
                budget=budget,
                producer_id=(
                    "forge2.context-manifest."
                    "fixture.v1"
                ),
                admitted_items=[
                    self.file_item
                ],
                excluded_items=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "context_per_item_budget_exceeded",
        )

    def test_invalid_budget_relation(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            ContextBudget(
                max_items=1,
                max_total_bytes=10,
                max_item_bytes=11,
            )

        self.assertEqual(
            context.exception.code,
            "item_budget_exceeds_total",
        )

    def test_duplicate_admitted_item(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_context_manifest(
                request_contract=(
                    self.request_contract
                ),
                step_id=(
                    "step.inspect_request_contract"
                ),
                repository=self.repository,
                budget=self.budget,
                producer_id=(
                    "forge2.context-manifest."
                    "fixture.v1"
                ),
                admitted_items=[
                    self.file_item,
                    self.file_item,
                ],
                excluded_items=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "duplicate_context_item",
        )

    def test_admitted_excluded_overlap(
        self,
    ) -> None:
        overlap = (
            create_excluded_context_item(
                kind=ContextItemKind.FILE_SLICE,
                source_uri=(
                    self.file_item.source_uri
                ),
                source_revision=(
                    self.file_item.source_revision
                ),
                locator=self.file_item.locator,
                content=(
                    "RequestContract records one "
                    "selected structured "
                    "interpretation."
                ),
                reason_code="not_needed",
                reason_text=(
                    "This exact source was marked "
                    "as excluded."
                ),
            )
        )

        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_context_manifest(
                request_contract=(
                    self.request_contract
                ),
                step_id=(
                    "step.inspect_request_contract"
                ),
                repository=self.repository,
                budget=self.budget,
                producer_id=(
                    "forge2.context-manifest."
                    "fixture.v1"
                ),
                admitted_items=[
                    self.file_item
                ],
                excluded_items=[overlap],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            (
                "context_admission_"
                "exclusion_overlap"
            ),
        )

    def test_excluded_content_not_admitted(
        self,
    ) -> None:
        value = self.create().to_dict()
        excluded = value[
            "body"
        ]["excluded_items"][0]

        self.assertNotIn(
            "content",
            excluded,
        )
        self.assertIn(
            "content_hash",
            excluded,
        )
        self.assertIn(
            "reason_code",
            excluded,
        )

    def test_request_reference_is_exact(
        self,
    ) -> None:
        manifest = self.create()

        self.assertEqual(
            manifest.request_contract,
            (
                self.request_contract
                .metadata
                .to_reference()
            ),
        )

    def test_wrong_request_contract(
        self,
    ) -> None:
        manifest = self.create()
        other = self._make_request_contract(
            producer_id=(
                "forge2.request-contract."
                "other-fixture.v1"
            )
        )

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            verify_context_manifest(
                manifest,
                request_contract=other,
            )

        self.assertEqual(
            context.exception.code,
            (
                "context_request_"
                "contract_mismatch"
            ),
        )

    def test_changed_item_content_rejected(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"][
            "admitted_items"
        ][0]["content"] = "changed"

        with self.assertRaises(
            ContractIntegrityError
        ):
            context_manifest_from_dict(
                value,
                request_contract=(
                    self.request_contract
                ),
            )

    def test_changed_body_rejected(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"][
            "producer_id"
        ] = "forge2.changed.v1"

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            context_manifest_from_dict(
                value,
                request_contract=(
                    self.request_contract
                ),
            )

        self.assertEqual(
            context.exception.code,
            "content_hash_mismatch",
        )

    def test_admitted_count_tamper(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"][
            "admitted_item_count"
        ] = 99

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            context_manifest_from_dict(
                value,
                request_contract=(
                    self.request_contract
                ),
            )

        self.assertEqual(
            context.exception.code,
            "admitted_item_count_mismatch",
        )

    def test_total_bytes_tamper(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"][
            "admitted_total_bytes"
        ] += 1

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            context_manifest_from_dict(
                value,
                request_contract=(
                    self.request_contract
                ),
            )

        self.assertEqual(
            context.exception.code,
            "admitted_total_bytes_mismatch",
        )

    def test_hidden_top_level_field(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["hidden"] = True

        with self.assertRaises(
            ContractValidationError
        ):
            context_manifest_from_dict(
                value,
                request_contract=(
                    self.request_contract
                ),
            )

    def test_hidden_body_field(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"]["hidden"] = True

        with self.assertRaises(
            ContractValidationError
        ):
            context_manifest_from_dict(
                value,
                request_contract=(
                    self.request_contract
                ),
            )

    def test_hidden_context_item_field(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"][
            "admitted_items"
        ][0]["hidden"] = True

        with self.assertRaises(
            ContractValidationError
        ):
            context_manifest_from_dict(
                value,
                request_contract=(
                    self.request_contract
                ),
            )

    def test_hidden_excluded_item_field(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"][
            "excluded_items"
        ][0]["hidden"] = True

        with self.assertRaises(
            ContractValidationError
        ):
            context_manifest_from_dict(
                value,
                request_contract=(
                    self.request_contract
                ),
            )

    def test_unknown_context_kind(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"][
            "admitted_items"
        ][0]["kind"] = "unknown"

        with self.assertRaises(
            ContractValidationError
        ) as context:
            context_manifest_from_dict(
                value,
                request_contract=(
                    self.request_contract
                ),
            )

        self.assertEqual(
            context.exception.code,
            "invalid_context_item_kind",
        )

    def test_invalid_repository_commit(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_repository_snapshot(
                repository_uri=(
                    "git+https://github.com/"
                    "BogaertN/forge2.git"
                ),
                commit_sha="short",
            )

        self.assertEqual(
            context.exception.code,
            "invalid_git_commit",
        )

    def test_invalid_source_uri(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_context_item(
                kind=ContextItemKind.POLICY,
                source_uri="not a uri",
                source_revision="revision-1",
                locator="section:10.3",
                content={"required": True},
                admission_basis_codes=[
                    "controlling_build_bible"
                ],
            )

        self.assertEqual(
            context.exception.code,
            "invalid_source_uri",
        )

    def test_authority_is_forbidden(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["metadata"][
            "authority_status"
        ] = "authorized"

        with self.assertRaises(
            (
                ContractIntegrityError,
                ContractValidationError,
            )
        ):
            context_manifest_from_dict(
                value,
                request_contract=(
                    self.request_contract
                ),
            )

    def test_effects_are_forbidden(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["metadata"][
            "declared_effects"
        ] = [
            {
                "kind": EffectKind.READ.value,
                "target": "repository",
                "description": None,
            }
        ]

        with self.assertRaises(
            (
                ContractIntegrityError,
                ContractValidationError,
            )
        ):
            context_manifest_from_dict(
                value,
                request_contract=(
                    self.request_contract
                ),
            )

    def test_no_runtime_selection_api(
        self,
    ) -> None:
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
            with self.subTest(name=name):
                self.assertFalse(
                    hasattr(module, name)
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
