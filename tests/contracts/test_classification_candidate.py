"""ClassificationCandidateSet invariant tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import json
import unittest

import forge2.contracts.classification_candidate as module
from forge2.contracts import (
    AuthorityStatus,
    CandidateDimension,
    CandidateOrigin,
    ContractIntegrityError,
    ContractValidationError,
    EffectKind,
    canonical_json,
    classification_candidate_set_from_dict,
    create_classification_candidate,
    create_classification_candidate_set,
    create_feature_evidence,
    create_input_event,
    verify_classification_candidate_set,
)


class ClassificationCandidateSetTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.event = create_input_event(
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
        self.evidence = (
            create_feature_evidence(
                source_pointer="/raw_input",
                feature_name=(
                    "lexical_request_verb"
                ),
                observed_value="hello",
                span_start=0,
                span_end=5,
            )
        )
        self.candidate = (
            create_classification_candidate(
                dimension=(
                    CandidateDimension
                    .REQUEST_KIND
                ),
                label="conversation",
                origin=CandidateOrigin.RULE,
                producer_id=(
                    "forge2.rule.lexical.v1"
                ),
                confidence_basis_points=9000,
                evidence=[self.evidence],
            )
        )
        self.created_at = datetime(
            2026,
            7,
            30,
            21,
            1,
            tzinfo=timezone.utc,
        )

    def create(self):
        return (
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[self.candidate],
                created_at=self.created_at,
            )
        )

    def test_dimension_vocabulary(
        self,
    ) -> None:
        self.assertEqual(
            tuple(
                item.value
                for item
                in CandidateDimension
            ),
            (
                "request_kind",
                "domain",
                "expected_result",
                "side_effect_class",
                "freshness_requirement",
                "capability",
                (
                    "code_explanation_"
                    "distinction"
                ),
                (
                    "tool_discovery_"
                    "requirement"
                ),
                "simulation_requirement",
                (
                    "clarification_"
                    "requirement"
                ),
                "risk_candidate",
            ),
        )

    def test_origin_vocabulary(
        self,
    ) -> None:
        self.assertEqual(
            tuple(
                item.value
                for item
                in CandidateOrigin
            ),
            (
                "rule",
                "model",
            ),
        )

    def test_fixed_evidence_identity(
        self,
    ) -> None:
        self.assertEqual(
            self.evidence.evidence_id,
            (
                "aiweb.feature-evidence:sha256:"
                "c1cf02dc8c86d7c9b5eda8829ae2842c"
                "668f4604723cb4b93731dd09a320e42c"
            ),
        )

    def test_fixed_candidate_identity(
        self,
    ) -> None:
        self.assertEqual(
            self.candidate.candidate_id,
            (
                "aiweb.classification-candidate:"
                "sha256:"
                "a3a5a303683777075afb8c61989dfbcf"
                "489fc03054aa934061ca426e3596fa9e"
            ),
        )

    def test_fixed_candidate_set_vector(
        self,
    ) -> None:
        result = self.create()

        self.assertEqual(
            result.metadata.content_hash,
            (
                "a930d2b717a8b5b636fa6553c7b383fc"
                "c387a18a3fdc63890799aa0d65e7d5df"
            ),
        )
        self.assertEqual(
            result.metadata.contract_id,
            (
                "aiweb.contract:sha256:"
                "0a8e16ab65ce40e4fc59862b0b85bbe2"
                "aaa3fecba26a18846e934afe43fca74d"
            ),
        )

    def test_metadata_boundaries(
        self,
    ) -> None:
        result = self.create()

        self.assertEqual(
            result.metadata.authority_status,
            AuthorityStatus.NONE,
        )
        self.assertEqual(
            result.metadata.declared_effects,
            (),
        )
        self.assertIsNone(
            result.metadata.parent
        )

    def test_round_trip(self) -> None:
        result = self.create()
        serialized = canonical_json(
            result.to_dict()
        )
        restored = (
            classification_candidate_set_from_dict(
                json.loads(serialized),
                input_event=self.event,
            )
        )

        self.assertEqual(
            restored,
            result,
        )
        self.assertEqual(
            canonical_json(
                restored.to_dict()
            ),
            serialized,
        )

    def test_set_is_immutable(self) -> None:
        result = self.create()

        with self.assertRaises(
            FrozenInstanceError
        ):
            result.candidates = ()

    def test_candidate_is_immutable(
        self,
    ) -> None:
        with self.assertRaises(
            FrozenInstanceError
        ):
            self.candidate.label = "changed"

    def test_evidence_is_immutable(
        self,
    ) -> None:
        with self.assertRaises(
            FrozenInstanceError
        ):
            self.evidence.feature_name = (
                "changed"
            )

    def test_structured_pointer_evidence(
        self,
    ) -> None:
        evidence = create_feature_evidence(
            source_pointer=(
                "/identity_context/actor_id"
            ),
            feature_name="actor_identity",
            observed_value="user:nic",
        )
        candidate = (
            create_classification_candidate(
                dimension=(
                    CandidateDimension.DOMAIN
                ),
                label="aiweb_project",
                origin=CandidateOrigin.RULE,
                producer_id=(
                    "forge2.rule.entity.v1"
                ),
                confidence_basis_points=8000,
                evidence=[evidence],
            )
        )
        result = (
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[candidate],
                created_at=self.created_at,
            )
        )

        verify_classification_candidate_set(
            result,
            input_event=self.event,
        )

    def test_list_pointer_evidence(
        self,
    ) -> None:
        event = create_input_event(
            raw_input="hello",
            conversation_context=[
                {
                    "role": "user",
                }
            ],
            identity_context={},
            session_metadata={},
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
            source_pointer=(
                "/conversation_context/0/role"
            ),
            feature_name="context_role",
            observed_value="user",
        )
        candidate = (
            create_classification_candidate(
                dimension=(
                    CandidateDimension.DOMAIN
                ),
                label="conversation",
                origin=CandidateOrigin.RULE,
                producer_id=(
                    "forge2.rule.context.v1"
                ),
                confidence_basis_points=7000,
                evidence=[evidence],
            )
        )

        create_classification_candidate_set(
            input_event=event,
            candidates=[candidate],
            created_at=self.created_at,
        )

    def test_wrong_text_span_rejected(
        self,
    ) -> None:
        evidence = create_feature_evidence(
            source_pointer="/raw_input",
            feature_name=(
                "lexical_request_verb"
            ),
            observed_value="hell",
            span_start=0,
            span_end=5,
        )
        candidate = (
            create_classification_candidate(
                dimension=(
                    CandidateDimension
                    .REQUEST_KIND
                ),
                label="conversation",
                origin=CandidateOrigin.RULE,
                producer_id=(
                    "forge2.rule.lexical.v1"
                ),
                confidence_basis_points=9000,
                evidence=[evidence],
            )
        )

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[candidate],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "feature_evidence_mismatch",
        )

    def test_out_of_range_span_rejected(
        self,
    ) -> None:
        evidence = create_feature_evidence(
            source_pointer="/raw_input",
            feature_name=(
                "lexical_request_verb"
            ),
            observed_value="hello",
            span_start=0,
            span_end=99,
        )
        candidate = (
            create_classification_candidate(
                dimension=(
                    CandidateDimension
                    .REQUEST_KIND
                ),
                label="conversation",
                origin=CandidateOrigin.RULE,
                producer_id=(
                    "forge2.rule.lexical.v1"
                ),
                confidence_basis_points=9000,
                evidence=[evidence],
            )
        )

        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[candidate],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "text_span_out_of_range",
        )

    def test_unknown_pointer_root_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_feature_evidence(
                source_pointer="/unknown",
                feature_name="feature",
                observed_value=True,
            )

        self.assertEqual(
            context.exception.code,
            (
                "invalid_source_"
                "pointer_root"
            ),
        )

    def test_missing_pointer_value_rejected(
        self,
    ) -> None:
        evidence = create_feature_evidence(
            source_pointer=(
                "/identity_context/missing"
            ),
            feature_name="missing_feature",
            observed_value="value",
        )
        candidate = (
            create_classification_candidate(
                dimension=(
                    CandidateDimension.DOMAIN
                ),
                label="unknown",
                origin=CandidateOrigin.RULE,
                producer_id=(
                    "forge2.rule.entity.v1"
                ),
                confidence_basis_points=1000,
                evidence=[evidence],
            )
        )

        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[candidate],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "source_pointer_not_found",
        )

    def test_confidence_bounds(self) -> None:
        for value in (
            -1,
            10001,
            True,
        ):
            with self.subTest(value=value):
                with self.assertRaises(
                    ContractValidationError
                ):
                    create_classification_candidate(
                        dimension=(
                            CandidateDimension
                            .DOMAIN
                        ),
                        label="domain",
                        origin=(
                            CandidateOrigin.MODEL
                        ),
                        producer_id=(
                            "model.test.v1"
                        ),
                        confidence_basis_points=(
                            value
                        ),
                        evidence=[
                            self.evidence
                        ],
                    )

    def test_candidate_requires_evidence(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_classification_candidate(
                dimension=(
                    CandidateDimension.DOMAIN
                ),
                label="domain",
                origin=CandidateOrigin.RULE,
                producer_id=(
                    "forge2.rule.test.v1"
                ),
                confidence_basis_points=5000,
                evidence=[],
            )

        self.assertEqual(
            context.exception.code,
            "candidate_evidence_required",
        )

    def test_empty_set_requires_clarification(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            (
                "classification_candidates_"
                "required"
            ),
        )

    def test_empty_clarification_set_allowed(
        self,
    ) -> None:
        result = (
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[],
                uncertainty_codes=[
                    (
                        "insufficient_"
                        "language_evidence"
                    )
                ],
                clarification_recommended=True,
                clarification_reason_codes=[
                    "request_kind_ambiguous"
                ],
                created_at=self.created_at,
            )
        )

        self.assertEqual(
            result.candidates,
            (),
        )
        self.assertTrue(
            result
            .clarification_recommended
        )

    def test_clarification_requires_reason(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[self.candidate],
                clarification_recommended=True,
                clarification_reason_codes=[],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "clarification_reason_required",
        )

    def test_reason_without_recommendation(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[self.candidate],
                clarification_reason_codes=[
                    "request_kind_ambiguous"
                ],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            (
                "clarification_reason_"
                "without_recommendation"
            ),
        )

    def test_candidate_order_is_canonical(
        self,
    ) -> None:
        evidence = create_feature_evidence(
            source_pointer=(
                "/session_metadata/channel"
            ),
            feature_name="channel_feature",
            observed_value="terminal",
        )
        second = (
            create_classification_candidate(
                dimension=(
                    CandidateDimension
                    .EXPECTED_RESULT
                ),
                label=(
                    "human_readable_response"
                ),
                origin=CandidateOrigin.RULE,
                producer_id=(
                    "forge2.rule.result.v1"
                ),
                confidence_basis_points=7000,
                evidence=[evidence],
            )
        )

        first_set = (
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[
                    self.candidate,
                    second,
                ],
                created_at=self.created_at,
            )
        )
        second_set = (
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[
                    second,
                    self.candidate,
                ],
                created_at=self.created_at,
            )
        )

        self.assertEqual(
            first_set,
            second_set,
        )

    def test_duplicate_candidate_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[
                    self.candidate,
                    self.candidate,
                ],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            (
                "duplicate_classification_"
                "candidate"
            ),
        )

    def test_duplicate_uncertainty_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_classification_candidate_set(
                input_event=self.event,
                candidates=[self.candidate],
                uncertainty_codes=[
                    "ambiguous",
                    "ambiguous",
                ],
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "duplicate_code",
        )

    def test_hidden_top_level_field(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["hidden"] = True

        with self.assertRaises(
            ContractValidationError
        ):
            classification_candidate_set_from_dict(
                value,
                input_event=self.event,
            )

    def test_hidden_body_field(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"]["hidden"] = True

        with self.assertRaises(
            ContractValidationError
        ):
            classification_candidate_set_from_dict(
                value,
                input_event=self.event,
            )

    def test_hidden_candidate_field(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"]["candidates"][0][
            "hidden"
        ] = True

        with self.assertRaises(
            ContractValidationError
        ):
            classification_candidate_set_from_dict(
                value,
                input_event=self.event,
            )

    def test_hidden_evidence_field(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"]["candidates"][0][
            "evidence"
        ][0]["hidden"] = True

        with self.assertRaises(
            ContractValidationError
        ):
            classification_candidate_set_from_dict(
                value,
                input_event=self.event,
            )

    def test_unknown_dimension_rejected(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"]["candidates"][0][
            "dimension"
        ] = "unknown"

        with self.assertRaises(
            ContractValidationError
        ) as context:
            classification_candidate_set_from_dict(
                value,
                input_event=self.event,
            )

        self.assertEqual(
            context.exception.code,
            "invalid_candidate_dimension",
        )

    def test_unknown_origin_rejected(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"]["candidates"][0][
            "origin"
        ] = "unknown"

        with self.assertRaises(
            ContractValidationError
        ) as context:
            classification_candidate_set_from_dict(
                value,
                input_event=self.event,
            )

        self.assertEqual(
            context.exception.code,
            "invalid_candidate_origin",
        )

    def test_changed_body_fails_binding(
        self,
    ) -> None:
        value = self.create().to_dict()
        value["body"][
            "uncertainty_codes"
        ] = ["changed"]

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            classification_candidate_set_from_dict(
                value,
                input_event=self.event,
            )

        self.assertEqual(
            context.exception.code,
            "content_hash_mismatch",
        )

    def test_wrong_input_event_rejected(
        self,
    ) -> None:
        result = self.create()
        other = create_input_event(
            raw_input="other",
            conversation_context=[],
            identity_context={},
            session_metadata={},
            created_at=datetime(
                2026,
                7,
                30,
                21,
                2,
                tzinfo=timezone.utc,
            ),
        )

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            verify_classification_candidate_set(
                result,
                input_event=other,
            )

        self.assertEqual(
            context.exception.code,
            (
                "classification_input_"
                "event_mismatch"
            ),
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
            classification_candidate_set_from_dict(
                value,
                input_event=self.event,
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
            classification_candidate_set_from_dict(
                value,
                input_event=self.event,
            )

    def test_no_selection_or_execution_api(
        self,
    ) -> None:
        for name in (
            "select_candidate",
            "selected_candidate",
            "authorize_candidate",
            "execute_candidate",
            (
                "classification_to_"
                "request_contract"
            ),
        ):
            with self.subTest(name=name):
                self.assertFalse(
                    hasattr(module, name)
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
