"""Invariant tests for immutable RequestContract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import json
import unittest

import forge2.contracts.request_contract as module
from forge2.contracts import (
    AuthorityStatus,
    CandidateDimension,
    CandidateOrigin,
    CandidateSelection,
    ContractIntegrityError,
    ContractValidationError,
    EffectKind,
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
    stable_identifier,
    verify_request_contract,
)


class RequestContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.input_event = create_input_event(
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

        self.request_evidence = (
            create_feature_evidence(
                source_pointer="/raw_input",
                feature_name=(
                    "request_kind_phrase"
                ),
                observed_value="Explain",
                span_start=0,
                span_end=7,
            )
        )
        self.result_evidence = (
            create_feature_evidence(
                source_pointer="/raw_input",
                feature_name=(
                    "expected_result_phrase"
                ),
                observed_value="repository",
                span_start=12,
                span_end=22,
            )
        )
        self.constraint_evidence = (
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

        self.request_candidate = (
            create_classification_candidate(
                dimension=(
                    CandidateDimension
                    .REQUEST_KIND
                ),
                label=(
                    "repository_explanation"
                ),
                origin=CandidateOrigin.RULE,
                producer_id=(
                    "forge2.rule.request.v1"
                ),
                confidence_basis_points=9800,
                evidence=[
                    self.request_evidence
                ],
            )
        )
        self.result_candidate = (
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
                evidence=[
                    self.result_evidence
                ],
            )
        )
        self.effect_candidate = (
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
                evidence=[
                    self.constraint_evidence
                ],
            )
        )

        self.candidate_set = (
            create_classification_candidate_set(
                input_event=self.input_event,
                candidates=[
                    self.request_candidate,
                    self.result_candidate,
                    self.effect_candidate,
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

        self.request_selection = (
            create_candidate_selection(
                candidate=(
                    self.request_candidate
                ),
                basis_codes=[
                    "exact_request_phrase"
                ],
            )
        )
        self.result_selection = (
            create_candidate_selection(
                candidate=(
                    self.result_candidate
                ),
                basis_codes=[
                    "exact_result_phrase"
                ],
            )
        )
        self.effect_selection = (
            create_candidate_selection(
                candidate=(
                    self.effect_candidate
                ),
                basis_codes=[
                    (
                        "explicit_preservation_"
                        "constraint"
                    )
                ],
            )
        )

        self.goal = (
            create_request_statement(
                kind=(
                    RequestStatementKind.GOAL
                ),
                code="explain_repository",
                text=(
                    "Explain the repository."
                ),
                evidence_ids=[
                    (
                        self.request_evidence
                        .evidence_id
                    ),
                    (
                        self.result_evidence
                        .evidence_id
                    ),
                ],
            )
        )
        self.constraint = (
            create_request_statement(
                kind=(
                    RequestStatementKind
                    .CONSTRAINT
                ),
                code="preserve_files",
                text="Do not change files.",
                evidence_ids=[
                    (
                        self
                        .constraint_evidence
                        .evidence_id
                    )
                ],
            )
        )
        self.desired_result = (
            create_request_statement(
                kind=(
                    RequestStatementKind
                    .DESIRED_RESULT
                ),
                code=(
                    "human_readable_explanation"
                ),
                text=(
                    "A human-readable "
                    "repository explanation."
                ),
                evidence_ids=[
                    (
                        self.result_evidence
                        .evidence_id
                    )
                ],
            )
        )

        self.created_at = datetime(
            2026,
            7,
            30,
            22,
            0,
            2,
            tzinfo=timezone.utc,
        )

    def create(self):
        return create_request_contract(
            input_event=self.input_event,
            classification_candidate_set=(
                self.candidate_set
            ),
            producer_id=(
                "forge2.request-contract."
                "fixture.v1"
            ),
            selected_candidates=[
                self.request_selection,
                self.result_selection,
                self.effect_selection,
            ],
            goals=[self.goal],
            constraints=[self.constraint],
            desired_result=(
                self.desired_result
            ),
            uncertainty_codes=[],
            created_at=self.created_at,
        )

    def test_fixed_source_contracts(
        self,
    ) -> None:
        self.assertEqual(
            self.input_event
            .metadata
            .content_hash,
            (
                "411ea0770af587aa2ebe3b2c0a44978b"
                "50bb803cff80ecce9d2ee7c8c42113cc"
            ),
        )
        self.assertEqual(
            self.input_event
            .metadata
            .contract_id,
            (
                "aiweb.contract:sha256:"
                "b7427c374c1567c048034f262ba4a2f4"
                "7ddf2222dcff923ea43d9717795ea1c7"
            ),
        )
        self.assertEqual(
            self.candidate_set
            .metadata
            .content_hash,
            (
                "827f61ad25a3bac1c52ea421716d1d11"
                "9d3bedb7815d4e638095d81439f87011"
            ),
        )
        self.assertEqual(
            self.candidate_set
            .metadata
            .contract_id,
            (
                "aiweb.contract:sha256:"
                "0c690f7b61cf88e2870fa860fc678bca"
                "ebe4ffbd506b6191d64d55474f071a57"
            ),
        )

    def test_fixed_selection_identities(
        self,
    ) -> None:
        self.assertEqual(
            self.request_selection
            .selection_id,
            (
                "aiweb.candidate-selection:"
                "sha256:"
                "cfb2c2d172a50740ba859ab0016bcc60"
                "f679c12e52389e884b28e134eea6a86e"
            ),
        )
        self.assertEqual(
            self.result_selection
            .selection_id,
            (
                "aiweb.candidate-selection:"
                "sha256:"
                "309113d866ee169ad902bee4aae6b113"
                "7d54ca1c2bed1691e780ec9417a35995"
            ),
        )
        self.assertEqual(
            self.effect_selection
            .selection_id,
            (
                "aiweb.candidate-selection:"
                "sha256:"
                "aa295f298090570cc19d0938e3c77049"
                "1d629a2c02b475ab7ea00f010c454075"
            ),
        )

    def test_fixed_statement_identities(
        self,
    ) -> None:
        self.assertEqual(
            self.goal.statement_id,
            (
                "aiweb.request-statement:sha256:"
                "efc4708ed4b99073e4f82c3c454ae9a"
                "86b2fe095395bc0159deb3ce92b80b120"
            ),
        )
        self.assertEqual(
            self.constraint.statement_id,
            (
                "aiweb.request-statement:sha256:"
                "8374b67259a77a1bd2157221530e5145"
                "7d0af77da578bdfdd9d158c2b2279da2"
            ),
        )
        self.assertEqual(
            self.desired_result
            .statement_id,
            (
                "aiweb.request-statement:sha256:"
                "f490e629a3308a74cd8847bfa3253dee"
                "d4d5dae2bc95de2edefcb6b1f8d1697e"
            ),
        )

    def test_fixed_request_contract_vector(
        self,
    ) -> None:
        request = self.create()

        self.assertEqual(
            request.metadata.content_hash,
            (
                "527b122ea8a909e22651e0f0bf86d5a2"
                "fb725fee4e2071e9a86f2df0e9b5e560"
            ),
        )
        self.assertEqual(
            request.metadata.contract_id,
            (
                "aiweb.contract:sha256:"
                "0ed80df9842671f7804cd165ab11bd82"
                "d480e578992c05decd16cd4e503f521f"
            ),
        )

    def test_metadata_is_authority_neutral(
        self,
    ) -> None:
        request = self.create()

        self.assertEqual(
            request
            .metadata
            .authority_status,
            AuthorityStatus.NONE,
        )
        self.assertEqual(
            request
            .metadata
            .declared_effects,
            (),
        )
        self.assertIsNone(
            request.metadata.parent
        )

    def test_round_trip(self) -> None:
        request = self.create()
        serialized = canonical_json(
            request.to_dict()
        )
        restored = request_contract_from_dict(
            json.loads(serialized),
            input_event=self.input_event,
            classification_candidate_set=(
                self.candidate_set
            ),
        )

        self.assertEqual(
            restored,
            request,
        )
        self.assertEqual(
            canonical_json(
                restored.to_dict()
            ),
            serialized,
        )

    def test_request_is_immutable(
        self,
    ) -> None:
        request = self.create()

        with self.assertRaises(
            FrozenInstanceError
        ):
            request.producer_id = "changed"

    def test_selection_is_immutable(
        self,
    ) -> None:
        with self.assertRaises(
            FrozenInstanceError
        ):
            self.request_selection.label = (
                "changed"
            )

    def test_statement_is_immutable(
        self,
    ) -> None:
        with self.assertRaises(
            FrozenInstanceError
        ):
            self.goal.text = "changed"

    def test_selection_order_is_canonical(
        self,
    ) -> None:
        first = create_request_contract(
            input_event=self.input_event,
            classification_candidate_set=(
                self.candidate_set
            ),
            producer_id=(
                "forge2.request-contract."
                "fixture.v1"
            ),
            selected_candidates=[
                self.request_selection,
                self.result_selection,
                self.effect_selection,
            ],
            goals=[self.goal],
            constraints=[self.constraint],
            desired_result=(
                self.desired_result
            ),
            uncertainty_codes=[],
            created_at=self.created_at,
        )
        second = create_request_contract(
            input_event=self.input_event,
            classification_candidate_set=(
                self.candidate_set
            ),
            producer_id=(
                "forge2.request-contract."
                "fixture.v1"
            ),
            selected_candidates=[
                self.effect_selection,
                self.request_selection,
                self.result_selection,
            ],
            goals=[self.goal],
            constraints=[self.constraint],
            desired_result=(
                self.desired_result
            ),
            uncertainty_codes=[],
            created_at=self.created_at,
        )

        self.assertEqual(first, second)

    def test_required_dimensions(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_request_contract(
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
                ),
                producer_id=(
                    "forge2.request-contract."
                    "fixture.v1"
                ),
                selected_candidates=[
                    self.request_selection,
                    self.result_selection,
                ],
                goals=[self.goal],
                constraints=[
                    self.constraint
                ],
                desired_result=(
                    self.desired_result
                ),
                uncertainty_codes=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            (
                "required_candidate_"
                "dimension_missing"
            ),
        )

    def test_duplicate_dimension_rejected(
        self,
    ) -> None:
        duplicate = CandidateSelection(
            selection_id=stable_identifier(
                (
                    "aiweb."
                    "candidate-selection"
                ),
                {
                    "basis_codes": [
                        "alternate_basis"
                    ],
                    "candidate_id": (
                        self
                        .result_candidate
                        .candidate_id
                    ),
                    "dimension": (
                        CandidateDimension
                        .REQUEST_KIND
                        .value
                    ),
                    "label": (
                        self
                        .result_candidate
                        .label
                    ),
                },
            ),
            candidate_id=(
                self
                .result_candidate
                .candidate_id
            ),
            dimension=(
                CandidateDimension.REQUEST_KIND
            ),
            label=(
                self.result_candidate.label
            ),
            basis_codes=(
                "alternate_basis",
            ),
        )

        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_request_contract(
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
                ),
                producer_id=(
                    "forge2.request-contract."
                    "fixture.v1"
                ),
                selected_candidates=[
                    self.request_selection,
                    duplicate,
                    self.effect_selection,
                ],
                goals=[self.goal],
                constraints=[
                    self.constraint
                ],
                desired_result=(
                    self.desired_result
                ),
                uncertainty_codes=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "duplicate_selected_dimension",
        )

    def test_selection_requires_basis(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_candidate_selection(
                candidate=(
                    self.request_candidate
                ),
                basis_codes=[],
            )

        self.assertEqual(
            context.exception.code,
            "code_required",
        )

    def test_goal_is_required(self) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_request_contract(
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
                ),
                producer_id=(
                    "forge2.request-contract."
                    "fixture.v1"
                ),
                selected_candidates=[
                    self.request_selection,
                    self.result_selection,
                    self.effect_selection,
                ],
                goals=[],
                constraints=[
                    self.constraint
                ],
                desired_result=(
                    self.desired_result
                ),
                uncertainty_codes=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "request_statement_required",
        )

    def test_desired_result_kind(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_request_contract(
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
                ),
                producer_id=(
                    "forge2.request-contract."
                    "fixture.v1"
                ),
                selected_candidates=[
                    self.request_selection,
                    self.result_selection,
                    self.effect_selection,
                ],
                goals=[self.goal],
                constraints=[
                    self.constraint
                ],
                desired_result=self.goal,
                uncertainty_codes=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "desired_result_kind_mismatch",
        )

    def test_statement_requires_evidence(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_request_statement(
                kind=(
                    RequestStatementKind.GOAL
                ),
                code="goal",
                text="Goal.",
                evidence_ids=[],
            )

        self.assertEqual(
            context.exception.code,
            "statement_evidence_required",
        )

    def test_unselected_evidence_rejected(
        self,
    ) -> None:
        extra_evidence = (
            create_feature_evidence(
                source_pointer=(
                    "/identity_context/actor_id"
                ),
                feature_name="actor_identity",
                observed_value="user:nic",
            )
        )
        extra_candidate = (
            create_classification_candidate(
                dimension=(
                    CandidateDimension.DOMAIN
                ),
                label="aiweb_project",
                origin=CandidateOrigin.RULE,
                producer_id=(
                    "forge2.rule.domain.v1"
                ),
                confidence_basis_points=8000,
                evidence=[extra_evidence],
            )
        )
        candidate_set = (
            create_classification_candidate_set(
                input_event=self.input_event,
                candidates=[
                    self.request_candidate,
                    self.result_candidate,
                    self.effect_candidate,
                    extra_candidate,
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
        bad_goal = (
            create_request_statement(
                kind=(
                    RequestStatementKind.GOAL
                ),
                code="explain_repository",
                text=(
                    "Explain the repository."
                ),
                evidence_ids=[
                    extra_evidence.evidence_id
                ],
            )
        )

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            create_request_contract(
                input_event=self.input_event,
                classification_candidate_set=(
                    candidate_set
                ),
                producer_id=(
                    "forge2.request-contract."
                    "fixture.v1"
                ),
                selected_candidates=[
                    self.request_selection,
                    self.result_selection,
                    self.effect_selection,
                ],
                goals=[bad_goal],
                constraints=[
                    self.constraint
                ],
                desired_result=(
                    self.desired_result
                ),
                uncertainty_codes=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            (
                "request_statement_"
                "evidence_not_selected"
            ),
        )

    def test_selected_candidate_must_exist(
        self,
    ) -> None:
        extra_evidence = (
            create_feature_evidence(
                source_pointer=(
                    "/identity_context/actor_id"
                ),
                feature_name="actor_identity",
                observed_value="user:nic",
            )
        )
        extra_candidate = (
            create_classification_candidate(
                dimension=(
                    CandidateDimension.DOMAIN
                ),
                label="aiweb_project",
                origin=CandidateOrigin.RULE,
                producer_id=(
                    "forge2.rule.domain.v1"
                ),
                confidence_basis_points=8000,
                evidence=[extra_evidence],
            )
        )
        extra_selection = (
            create_candidate_selection(
                candidate=extra_candidate,
                basis_codes=[
                    "exact_actor_identity"
                ],
            )
        )

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            create_request_contract(
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
                ),
                producer_id=(
                    "forge2.request-contract."
                    "fixture.v1"
                ),
                selected_candidates=[
                    self.request_selection,
                    self.result_selection,
                    self.effect_selection,
                    extra_selection,
                ],
                goals=[self.goal],
                constraints=[
                    self.constraint
                ],
                desired_result=(
                    self.desired_result
                ),
                uncertainty_codes=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "selected_candidate_not_found",
        )

    def test_desired_result_matches_candidate(
        self,
    ) -> None:
        wrong_result = (
            create_request_statement(
                kind=(
                    RequestStatementKind
                    .DESIRED_RESULT
                ),
                code="different_result",
                text="A different result.",
                evidence_ids=[
                    (
                        self.result_evidence
                        .evidence_id
                    )
                ],
            )
        )

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            create_request_contract(
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
                ),
                producer_id=(
                    "forge2.request-contract."
                    "fixture.v1"
                ),
                selected_candidates=[
                    self.request_selection,
                    self.result_selection,
                    self.effect_selection,
                ],
                goals=[self.goal],
                constraints=[
                    self.constraint
                ],
                desired_result=wrong_result,
                uncertainty_codes=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            (
                "desired_result_"
                "candidate_mismatch"
            ),
        )

    def test_uncertainty_is_preserved(
        self,
    ) -> None:
        candidate_set = (
            create_classification_candidate_set(
                input_event=self.input_event,
                candidates=[
                    self.request_candidate,
                    self.result_candidate,
                    self.effect_candidate,
                ],
                uncertainty_codes=[
                    "residual_scope_uncertainty"
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

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            create_request_contract(
                input_event=self.input_event,
                classification_candidate_set=(
                    candidate_set
                ),
                producer_id=(
                    "forge2.request-contract."
                    "fixture.v1"
                ),
                selected_candidates=[
                    self.request_selection,
                    self.result_selection,
                    self.effect_selection,
                ],
                goals=[self.goal],
                constraints=[
                    self.constraint
                ],
                desired_result=(
                    self.desired_result
                ),
                uncertainty_codes=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "request_uncertainty_mismatch",
        )

    def test_clarification_set_rejected(
        self,
    ) -> None:
        candidate_set = (
            create_classification_candidate_set(
                input_event=self.input_event,
                candidates=[
                    self.request_candidate,
                    self.result_candidate,
                    self.effect_candidate,
                ],
                clarification_recommended=True,
                clarification_reason_codes=[
                    "scope_ambiguous"
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

        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_request_contract(
                input_event=self.input_event,
                classification_candidate_set=(
                    candidate_set
                ),
                producer_id=(
                    "forge2.request-contract."
                    "fixture.v1"
                ),
                selected_candidates=[
                    self.request_selection,
                    self.result_selection,
                    self.effect_selection,
                ],
                goals=[self.goal],
                constraints=[
                    self.constraint
                ],
                desired_result=(
                    self.desired_result
                ),
                uncertainty_codes=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            (
                "classification_requires_"
                "clarification"
            ),
        )

    def test_hidden_top_level_field(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["hidden"] = True

        with self.assertRaises(
            ContractValidationError
        ):
            request_contract_from_dict(
                value,
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
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
            request_contract_from_dict(
                value,
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
                ),
            )

    def test_hidden_selection_field(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"][
            "selected_candidates"
        ][0]["hidden"] = True

        with self.assertRaises(
            ContractValidationError
        ):
            request_contract_from_dict(
                value,
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
                ),
            )

    def test_hidden_statement_field(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"]["goals"][0][
            "hidden"
        ] = True

        with self.assertRaises(
            ContractValidationError
        ):
            request_contract_from_dict(
                value,
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
                ),
            )

    def test_changed_body_fails_binding(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"][
            "producer_id"
        ] = "forge2.changed.v1"

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            request_contract_from_dict(
                value,
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
                ),
            )

        self.assertEqual(
            context.exception.code,
            "content_hash_mismatch",
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
            request_contract_from_dict(
                value,
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
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
                "kind": (
                    EffectKind
                    .EXECUTE
                    .value
                ),
                "target": "terminal",
                "description": None,
            }
        ]

        with self.assertRaises(
            (
                ContractIntegrityError,
                ContractValidationError,
            )
        ):
            request_contract_from_dict(
                value,
                input_event=self.input_event,
                classification_candidate_set=(
                    self.candidate_set
                ),
            )

    def test_wrong_input_event_rejected(
        self,
    ) -> None:
        request = self.create()
        other = create_input_event(
            raw_input="Other request.",
            conversation_context=[],
            identity_context={},
            session_metadata={},
            created_at=datetime(
                2026,
                7,
                30,
                22,
                1,
                tzinfo=timezone.utc,
            ),
        )

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            verify_request_contract(
                request,
                input_event=other,
                classification_candidate_set=(
                    self.candidate_set
                ),
            )

        self.assertEqual(
            context.exception.code,
            "request_input_event_mismatch",
        )

    def test_no_compiler_or_execution_api(
        self,
    ) -> None:
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
            with self.subTest(name=name):
                self.assertFalse(
                    hasattr(module, name)
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
