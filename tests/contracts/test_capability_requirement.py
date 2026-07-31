"""Invariant tests for CapabilityRequirement."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import json
import unittest

import forge2.contracts.capability_requirement as module
from forge2.contracts import (
    AuthorityStatus,
    CandidateDimension,
    CandidateOrigin,
    CapabilityDataDirection,
    ContextItemKind,
    ContractIntegrityError,
    ContractValidationError,
    EffectKind,
    RequestStatementKind,
    canonical_json,
    capability_requirement_from_dict,
    create_candidate_selection,
    create_capability_acceptance_criterion,
    create_capability_data_requirement,
    create_capability_requirement,
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
    verify_capability_requirement,
)


PARENT_COMMIT = "6d2e6b6560b78a490500aded6428e6f768987c81"
ROADMAP_ID = "1WrnuwxhX_mrjNTJXXNlijMLVA6gYv7S4mWwXnnjmjP0"

SOURCE_TEXT = (
    "Describe the capability required to inspect "
    "RequestContract without choosing a provider."
)


def build_reference_fixture(
    *,
    request_producer: str = (
        "forge2.request-contract."
        "capability-fixture.v1"
    ),
    context_step: str = (
        "step.define_capability_requirement"
    ),
    context_producer: str = (
        "forge2.context-manifest."
        "capability-fixture.v1"
    ),
):
    input_event = create_input_event(
        raw_input=SOURCE_TEXT,
        conversation_context=[],
        identity_context={
            "actor_id": "user:nic",
            "actor_kind": "user",
        },
        session_metadata={
            "channel": "terminal",
            "session_id": "session-010",
        },
        created_at=datetime(
            2026,
            7,
            31,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )

    request_evidence = create_feature_evidence(
        source_pointer="/raw_input",
        feature_name="request_kind_phrase",
        observed_value="Describe",
        span_start=0,
        span_end=8,
    )
    result_evidence = create_feature_evidence(
        source_pointer="/raw_input",
        feature_name="expected_result_phrase",
        observed_value="capability",
        span_start=13,
        span_end=23,
    )
    constraint_evidence = create_feature_evidence(
        source_pointer="/raw_input",
        feature_name="provider_constraint",
        observed_value="without choosing a provider",
        span_start=60,
        span_end=87,
    )

    request_candidate = create_classification_candidate(
        dimension=CandidateDimension.REQUEST_KIND,
        label="capability_description",
        origin=CandidateOrigin.RULE,
        producer_id="forge2.rule.request.v1",
        confidence_basis_points=9900,
        evidence=[request_evidence],
    )
    result_candidate = create_classification_candidate(
        dimension=CandidateDimension.EXPECTED_RESULT,
        label=(
            "provider_neutral_"
            "capability_requirement"
        ),
        origin=CandidateOrigin.RULE,
        producer_id="forge2.rule.result.v1",
        confidence_basis_points=9800,
        evidence=[result_evidence],
    )
    effect_candidate = create_classification_candidate(
        dimension=CandidateDimension.SIDE_EFFECT_CLASS,
        label="read_only",
        origin=CandidateOrigin.RULE,
        producer_id="forge2.rule.side_effect.v1",
        confidence_basis_points=10000,
        evidence=[constraint_evidence],
    )

    candidate_set = (
        create_classification_candidate_set(
            input_event=input_event,
            candidates=[
                request_candidate,
                result_candidate,
                effect_candidate,
            ],
            uncertainty_codes=[
                "provider_resolution_pending"
            ],
            clarification_recommended=False,
            clarification_reason_codes=[],
            created_at=datetime(
                2026,
                7,
                31,
                14,
                30,
                1,
                tzinfo=timezone.utc,
            ),
        )
    )

    goal = create_request_statement(
        kind=RequestStatementKind.GOAL,
        code="describe_required_capability",
        text=(
            "Describe the required capability behavior."
        ),
        evidence_ids=[
            request_evidence.evidence_id,
            result_evidence.evidence_id,
        ],
    )
    constraint = create_request_statement(
        kind=RequestStatementKind.CONSTRAINT,
        code="do_not_choose_provider",
        text=(
            "Do not name or select a capability provider."
        ),
        evidence_ids=[
            constraint_evidence.evidence_id
        ],
    )
    desired_result = create_request_statement(
        kind=RequestStatementKind.DESIRED_RESULT,
        code=(
            "provider_neutral_"
            "capability_requirement"
        ),
        text=(
            "A provider-neutral CapabilityRequirement."
        ),
        evidence_ids=[
            result_evidence.evidence_id,
            constraint_evidence.evidence_id,
        ],
    )

    request_contract = create_request_contract(
        input_event=input_event,
        classification_candidate_set=candidate_set,
        producer_id=request_producer,
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
                    "explicit_read_only_constraint"
                ],
            ),
        ],
        goals=[goal],
        constraints=[constraint],
        desired_result=desired_result,
        uncertainty_codes=[
            "provider_resolution_pending"
        ],
        created_at=datetime(
            2026,
            7,
            31,
            14,
            30,
            2,
            tzinfo=timezone.utc,
        ),
    )

    repository = create_repository_snapshot(
        repository_uri=(
            "git+https://github.com/"
            "BogaertN/forge2.git"
        ),
        commit_sha=PARENT_COMMIT,
    )
    budget = create_context_budget(
        max_items=8,
        max_total_bytes=4096,
        max_item_bytes=2048,
    )
    request_source = create_context_item(
        kind=ContextItemKind.FILE_SLICE,
        source_uri=(
            "repo://BogaertN/forge2/"
            "src/forge2/contracts/request_contract.py"
        ),
        source_revision=PARENT_COMMIT,
        locator="symbol:RequestContract",
        content=(
            "RequestContract preserves selected request "
            "meaning without granting runtime authority."
        ),
        admission_basis_codes=[
            "request_contract_dependency"
        ],
    )
    roadmap_source = create_context_item(
        kind=ContextItemKind.POLICY,
        source_uri=f"gdoc://{ROADMAP_ID}",
        source_revision=(
            "controlling-production-roadmap-2026-07-30"
        ),
        locator="sections:8,11,11.3",
        content={
            "capability_requirement": (
                "provider-neutral required behavior"
            ),
            "discovery_rule": (
                "describe behavior, not package name"
            ),
        },
        admission_basis_codes=[
            "controlling_build_bible"
        ],
    )
    excluded_source = create_excluded_context_item(
        kind=ContextItemKind.DOCUMENTATION,
        source_uri=(
            "repo://BogaertN/forge2/README.md"
        ),
        source_revision=PARENT_COMMIT,
        locator="lines:1-10",
        content=(
            "General repository documentation."
        ),
        reason_code="not_required_for_behavior",
        reason_text=(
            "General documentation is not needed "
            "to define this capability behavior."
        ),
    )

    context_manifest = create_context_manifest(
        request_contract=request_contract,
        step_id=context_step,
        repository=repository,
        budget=budget,
        producer_id=context_producer,
        admitted_items=[
            request_source,
            roadmap_source,
        ],
        excluded_items=[excluded_source],
        created_at=datetime(
            2026,
            7,
            31,
            14,
            30,
            3,
            tzinfo=timezone.utc,
        ),
    )

    input_requirement = (
        create_capability_data_requirement(
            direction=CapabilityDataDirection.INPUT,
            code="request_contract_source",
            description=(
                "Exact immutable RequestContract input."
            ),
            media_type=(
                "application/vnd.aiweb."
                "request-contract+json"
            ),
            schema_uri=(
                "aiweb-schema://contracts/"
                "RequestContract/1.0.0"
            ),
            required=True,
            source_statement_ids=[
                goal.statement_id
            ],
        )
    )
    output_requirement = (
        create_capability_data_requirement(
            direction=CapabilityDataDirection.OUTPUT,
            code="capability_requirement_record",
            description=(
                "Provider-neutral capability "
                "requirement record."
            ),
            media_type=(
                "application/vnd.aiweb."
                "capability-requirement+json"
            ),
            schema_uri=(
                "aiweb-schema://contracts/"
                "CapabilityRequirement/1.0.0"
            ),
            required=True,
            source_statement_ids=[
                desired_result.statement_id
            ],
        )
    )
    criterion = (
        create_capability_acceptance_criterion(
            code="provider_neutral",
            description=(
                "The requirement must not name, "
                "select, rank, or authorize a provider."
            ),
            source_statement_ids=[
                constraint.statement_id,
                desired_result.statement_id,
            ],
        )
    )

    return {
        "request_contract": request_contract,
        "context_manifest": context_manifest,
        "goal": goal,
        "constraint": constraint,
        "desired_result": desired_result,
        "input_requirement": input_requirement,
        "output_requirement": output_requirement,
        "criterion": criterion,
    }


class CapabilityRequirementTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = build_reference_fixture()

        self.request_contract = fixture[
            "request_contract"
        ]
        self.context_manifest = fixture[
            "context_manifest"
        ]
        self.goal = fixture["goal"]
        self.constraint = fixture["constraint"]
        self.desired_result = fixture[
            "desired_result"
        ]
        self.input_requirement = fixture[
            "input_requirement"
        ]
        self.output_requirement = fixture[
            "output_requirement"
        ]
        self.criterion = fixture["criterion"]
        self.created_at = datetime(
            2026,
            7,
            31,
            14,
            30,
            4,
            tzinfo=timezone.utc,
        )

    def create(
        self,
        *,
        input_requirements=None,
        output_requirements=None,
        acceptance_criteria=None,
        behavior_statement_ids=None,
        required_property_codes=None,
        uncertainty_codes=None,
    ):
        return create_capability_requirement(
            request_contract=self.request_contract,
            context_manifest=self.context_manifest,
            producer_id=(
                "forge2.capability-requirement."
                "fixture.v1"
            ),
            requirement_code=(
                "describe_required_capability"
            ),
            behavior_description=(
                "Describe the behavior required to "
                "inspect RequestContract without "
                "assuming a provider."
            ),
            behavior_statement_ids=(
                behavior_statement_ids
                if behavior_statement_ids is not None
                else [
                    self.goal.statement_id,
                    self.desired_result.statement_id,
                ]
            ),
            input_requirements=(
                input_requirements
                if input_requirements is not None
                else [self.input_requirement]
            ),
            output_requirements=(
                output_requirements
                if output_requirements is not None
                else [self.output_requirement]
            ),
            required_property_codes=(
                required_property_codes
                if required_property_codes is not None
                else [
                    "authority_neutral",
                    "provider_neutral",
                    "reproducible",
                ]
            ),
            acceptance_criteria=(
                acceptance_criteria
                if acceptance_criteria is not None
                else [self.criterion]
            ),
            uncertainty_codes=(
                uncertainty_codes
                if uncertainty_codes is not None
                else [
                    "provider_resolution_pending"
                ]
            ),
            created_at=self.created_at,
        )

    def test_fixed_input_vector(self):
        self.assertEqual(
            self.input_requirement.requirement_id,
            "aiweb.capability-data-requirement:sha256:ce9552d3558f398a1fa914ab18cd821aa6f028ed5b80d90a1c2f20cc74bb379d",
        )

    def test_fixed_output_vector(self):
        self.assertEqual(
            self.output_requirement.requirement_id,
            "aiweb.capability-data-requirement:sha256:618dc158780f4f06d98b3381dfea423e43c19160e3736eb828fd5cb2c5d2cff5",
        )

    def test_fixed_criterion_vector(self):
        self.assertEqual(
            self.criterion.criterion_id,
            "aiweb.capability-acceptance-criterion:sha256:c2f9fa586ddc53035f99c7835e6c997defac514e3cb540a6454113d875f7686b",
        )

    def test_fixed_requirement_vector(self):
        requirement = self.create()
        self.assertEqual(
            requirement.metadata.content_hash,
            "e76690e8b55576bf4ab1bc1b6fcf5a3771e46a48e54ece6972c2dde51fb74958",
        )
        self.assertEqual(
            requirement.metadata.contract_id,
            "aiweb.contract:sha256:ebaf6ca262d8efe08672f476bf8536b7aa5fb023cfabf4076195c3a20541fb09",
        )

    def test_side_effect_selection_is_exact(self):
        requirement = self.create()
        self.assertEqual(
            requirement.side_effect_selection_id,
            "aiweb.candidate-selection:sha256:362ece729c78221a4baf8cdaf3712b693c0dff0b4fdd661d925b19953c12cf9a",
        )
        self.assertEqual(
            requirement.side_effect_class,
            "read_only",
        )

    def test_count_vectors(self):
        requirement = self.create()
        self.assertEqual(
            len(requirement.input_requirements),
            1,
        )
        self.assertEqual(
            len(requirement.output_requirements),
            1,
        )
        self.assertEqual(
            len(requirement.acceptance_criteria),
            1,
        )

    def test_authority_is_none(self):
        requirement = self.create()
        self.assertEqual(
            requirement.metadata.authority_status,
            AuthorityStatus.NONE,
        )
        self.assertEqual(
            requirement.metadata.declared_effects,
            (),
        )

    def test_round_trip(self):
        requirement = self.create()
        serialized = canonical_json(
            requirement.to_dict()
        )
        restored = capability_requirement_from_dict(
            json.loads(serialized),
            request_contract=self.request_contract,
            context_manifest=self.context_manifest,
        )
        self.assertEqual(restored, requirement)
        self.assertEqual(
            canonical_json(restored.to_dict()),
            serialized,
        )

    def test_requirement_is_immutable(self):
        requirement = self.create()
        with self.assertRaises(FrozenInstanceError):
            requirement.requirement_code = "changed"

    def test_data_requirement_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.input_requirement.code = "changed"

    def test_criterion_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.criterion.code = "changed"

    def test_input_order_is_canonical(self):
        second = create_capability_data_requirement(
            direction=CapabilityDataDirection.INPUT,
            code="context_manifest_source",
            description="Exact ContextManifest input.",
            media_type=(
                "application/vnd.aiweb."
                "context-manifest+json"
            ),
            schema_uri=None,
            required=True,
            source_statement_ids=[
                self.goal.statement_id
            ],
        )
        self.assertEqual(
            self.create(
                input_requirements=[
                    self.input_requirement,
                    second,
                ]
            ),
            self.create(
                input_requirements=[
                    second,
                    self.input_requirement,
                ]
            ),
        )

    def test_output_order_is_canonical(self):
        second = create_capability_data_requirement(
            direction=CapabilityDataDirection.OUTPUT,
            code="verification_summary",
            description=(
                "Provider-neutral verification summary."
            ),
            media_type="application/json",
            schema_uri=None,
            required=False,
            source_statement_ids=[
                self.desired_result.statement_id
            ],
        )
        self.assertEqual(
            self.create(
                output_requirements=[
                    self.output_requirement,
                    second,
                ]
            ),
            self.create(
                output_requirements=[
                    second,
                    self.output_requirement,
                ]
            ),
        )

    def test_criteria_order_is_canonical(self):
        second = (
            create_capability_acceptance_criterion(
                code="reproducible",
                description=(
                    "The requirement must serialize "
                    "reproducibly."
                ),
                source_statement_ids=[
                    self.desired_result.statement_id
                ],
            )
        )
        self.assertEqual(
            self.create(
                acceptance_criteria=[
                    self.criterion,
                    second,
                ]
            ),
            self.create(
                acceptance_criteria=[
                    second,
                    self.criterion,
                ]
            ),
        )

    def test_property_order_is_canonical(self):
        self.assertEqual(
            self.create(
                required_property_codes=[
                    "reproducible",
                    "provider_neutral",
                    "authority_neutral",
                ]
            ),
            self.create(
                required_property_codes=[
                    "authority_neutral",
                    "provider_neutral",
                    "reproducible",
                ]
            ),
        )

    def test_uncertainty_order_is_canonical(self):
        self.assertEqual(
            self.create(
                uncertainty_codes=[
                    "tool_availability_unknown",
                    "provider_resolution_pending",
                ]
            ),
            self.create(
                uncertainty_codes=[
                    "provider_resolution_pending",
                    "tool_availability_unknown",
                ]
            ),
        )

    def test_output_is_required(self):
        with self.assertRaises(
            ContractValidationError
        ) as context:
            self.create(output_requirements=[])
        self.assertEqual(
            context.exception.code,
            "output_requirement_required",
        )

    def test_acceptance_criterion_required(self):
        with self.assertRaises(
            ContractValidationError
        ) as context:
            self.create(acceptance_criteria=[])
        self.assertEqual(
            context.exception.code,
            "acceptance_criterion_required",
        )

    def test_behavior_statement_required(self):
        with self.assertRaises(
            ContractValidationError
        ) as context:
            self.create(behavior_statement_ids=[])
        self.assertEqual(
            context.exception.code,
            "statement_reference_required",
        )

    def test_data_statement_required(self):
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_capability_data_requirement(
                direction=CapabilityDataDirection.INPUT,
                code="missing_source",
                description="Missing source.",
                media_type="application/json",
                schema_uri=None,
                required=True,
                source_statement_ids=[],
            )
        self.assertEqual(
            context.exception.code,
            "statement_reference_required",
        )

    def test_criterion_statement_required(self):
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_capability_acceptance_criterion(
                code="missing_source",
                description="Missing source.",
                source_statement_ids=[],
            )
        self.assertEqual(
            context.exception.code,
            "statement_reference_required",
        )

    def test_unknown_behavior_statement(self):
        unknown = (
            "aiweb.request-statement:sha256:"
            + ("0" * 64)
        )
        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            self.create(
                behavior_statement_ids=[unknown]
            )
        self.assertEqual(
            context.exception.code,
            "unknown_request_statement_reference",
        )

    def test_unknown_data_statement(self):
        unknown = (
            "aiweb.request-statement:sha256:"
            + ("1" * 64)
        )
        requirement = create_capability_data_requirement(
            direction=CapabilityDataDirection.INPUT,
            code="unknown_source",
            description="Input with unknown source.",
            media_type="application/json",
            schema_uri=None,
            required=True,
            source_statement_ids=[unknown],
        )
        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            self.create(
                input_requirements=[requirement]
            )
        self.assertEqual(
            context.exception.code,
            "unknown_request_statement_reference",
        )

    def test_unknown_criterion_statement(self):
        unknown = (
            "aiweb.request-statement:sha256:"
            + ("2" * 64)
        )
        criterion = (
            create_capability_acceptance_criterion(
                code="unknown_source",
                description=(
                    "Criterion with unknown source."
                ),
                source_statement_ids=[unknown],
            )
        )
        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            self.create(
                acceptance_criteria=[criterion]
            )
        self.assertEqual(
            context.exception.code,
            "unknown_request_statement_reference",
        )

    def test_request_reference_is_exact(self):
        requirement = self.create()
        self.assertEqual(
            requirement.request_contract,
            self.request_contract.metadata.to_reference(),
        )

    def test_context_reference_is_exact(self):
        requirement = self.create()
        self.assertEqual(
            requirement.context_manifest,
            self.context_manifest.metadata.to_reference(),
        )

    def test_wrong_request_contract_rejected(self):
        requirement = self.create()
        other = build_reference_fixture(
            request_producer=(
                "forge2.request-contract."
                "other-fixture.v1"
            ),
            context_step=(
                "step.other_capability_requirement"
            ),
            context_producer=(
                "forge2.context-manifest."
                "other-fixture.v1"
            ),
        )
        with self.assertRaises(
            ContractIntegrityError
        ):
            verify_capability_requirement(
                requirement,
                request_contract=(
                    other["request_contract"]
                ),
                context_manifest=(
                    other["context_manifest"]
                ),
            )

    def test_wrong_context_manifest_rejected(self):
        requirement = self.create()
        repository = create_repository_snapshot(
            repository_uri=(
                "git+https://github.com/"
                "BogaertN/forge2.git"
            ),
            commit_sha=PARENT_COMMIT,
        )
        budget = create_context_budget(
            max_items=1,
            max_total_bytes=1024,
            max_item_bytes=1024,
        )
        item = create_context_item(
            kind=ContextItemKind.POLICY,
            source_uri=f"gdoc://{ROADMAP_ID}",
            source_revision="revision-2",
            locator="section:11.3",
            content={
                "rule": "provider_neutral"
            },
            admission_basis_codes=[
                "controlling_build_bible"
            ],
        )
        other_context = create_context_manifest(
            request_contract=self.request_contract,
            step_id="step.other_context",
            repository=repository,
            budget=budget,
            producer_id=(
                "forge2.context-manifest."
                "other-context.v1"
            ),
            admitted_items=[item],
            excluded_items=[],
            created_at=datetime(
                2026,
                7,
                31,
                14,
                31,
                tzinfo=timezone.utc,
            ),
        )
        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            verify_capability_requirement(
                requirement,
                request_contract=self.request_contract,
                context_manifest=other_context,
            )
        self.assertEqual(
            context.exception.code,
            "capability_context_manifest_mismatch",
        )

    def test_request_uncertainty_preserved(self):
        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            self.create(uncertainty_codes=[])
        self.assertEqual(
            context.exception.code,
            "request_uncertainty_not_preserved",
        )

    def test_duplicate_input_item(self):
        with self.assertRaises(
            ContractValidationError
        ) as context:
            self.create(
                input_requirements=[
                    self.input_requirement,
                    self.input_requirement,
                ]
            )
        self.assertEqual(
            context.exception.code,
            "duplicate_data_requirement",
        )

    def test_duplicate_cross_direction_code(self):
        output = create_capability_data_requirement(
            direction=CapabilityDataDirection.OUTPUT,
            code=self.input_requirement.code,
            description="Output with duplicate code.",
            media_type="application/json",
            schema_uri=None,
            required=True,
            source_statement_ids=[
                self.desired_result.statement_id
            ],
        )
        with self.assertRaises(
            ContractValidationError
        ) as context:
            self.create(output_requirements=[output])
        self.assertEqual(
            context.exception.code,
            "duplicate_cross_direction_data_code",
        )

    def test_invalid_media_type(self):
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_capability_data_requirement(
                direction=CapabilityDataDirection.INPUT,
                code="invalid_media",
                description="Invalid media type.",
                media_type="not a media type",
                schema_uri=None,
                required=True,
                source_statement_ids=[
                    self.goal.statement_id
                ],
            )
        self.assertEqual(
            context.exception.code,
            "invalid_media_type",
        )

    def test_invalid_schema_uri(self):
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_capability_data_requirement(
                direction=CapabilityDataDirection.INPUT,
                code="invalid_schema",
                description="Invalid schema URI.",
                media_type="application/json",
                schema_uri="not a uri",
                required=True,
                source_statement_ids=[
                    self.goal.statement_id
                ],
            )
        self.assertEqual(
            context.exception.code,
            "invalid_schema_uri",
        )

    def test_hidden_top_level_field(self):
        value = self.create().to_dict()
        value["hidden"] = True
        with self.assertRaises(
            ContractValidationError
        ):
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )

    def test_hidden_body_field(self):
        value = self.create().to_dict()
        value["body"]["hidden"] = True
        with self.assertRaises(
            ContractValidationError
        ):
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )

    def test_hidden_input_field(self):
        value = self.create().to_dict()
        value["body"][
            "input_requirements"
        ][0]["hidden"] = True
        with self.assertRaises(
            ContractValidationError
        ):
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )

    def test_hidden_output_field(self):
        value = self.create().to_dict()
        value["body"][
            "output_requirements"
        ][0]["hidden"] = True
        with self.assertRaises(
            ContractValidationError
        ):
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )

    def test_hidden_criterion_field(self):
        value = self.create().to_dict()
        value["body"][
            "acceptance_criteria"
        ][0]["hidden"] = True
        with self.assertRaises(
            ContractValidationError
        ):
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )

    def test_unknown_direction(self):
        value = self.create().to_dict()
        value["body"][
            "input_requirements"
        ][0]["direction"] = "unknown"
        with self.assertRaises(
            ContractValidationError
        ) as context:
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )
        self.assertEqual(
            context.exception.code,
            "invalid_data_direction",
        )

    def test_provider_field_is_rejected(self):
        value = self.create().to_dict()
        value["body"]["provider_id"] = (
            "provider:not-allowed"
        )
        with self.assertRaises(
            ContractValidationError
        ):
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )

    def test_changed_body_rejected(self):
        value = self.create().to_dict()
        value["body"][
            "behavior_description"
        ] = "Changed behavior."
        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )
        self.assertEqual(
            context.exception.code,
            "content_hash_mismatch",
        )

    def test_input_count_tamper(self):
        value = self.create().to_dict()
        value["body"][
            "input_requirement_count"
        ] = 99
        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )
        self.assertEqual(
            context.exception.code,
            "recorded_count_mismatch",
        )

    def test_output_count_tamper(self):
        value = self.create().to_dict()
        value["body"][
            "output_requirement_count"
        ] = 99
        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )
        self.assertEqual(
            context.exception.code,
            "recorded_count_mismatch",
        )

    def test_criterion_count_tamper(self):
        value = self.create().to_dict()
        value["body"][
            "acceptance_criterion_count"
        ] = 99
        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )
        self.assertEqual(
            context.exception.code,
            "recorded_count_mismatch",
        )

    def test_authority_is_forbidden(self):
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
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )

    def test_effects_are_forbidden(self):
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
            capability_requirement_from_dict(
                value,
                request_contract=self.request_contract,
                context_manifest=self.context_manifest,
            )

    def test_serialized_body_has_no_provider(self):
        body = self.create().to_dict()["body"]
        for field in (
            "provider_id",
            "provider_name",
            "package_name",
            "tool_name",
            "version",
            "command",
            "endpoint",
            "executable",
            "adapter",
        ):
            with self.subTest(field=field):
                self.assertNotIn(field, body)

    def test_no_provider_or_runtime_api(self):
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
            with self.subTest(name=name):
                self.assertFalse(
                    hasattr(module, name)
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
