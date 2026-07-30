"""Invariant tests for append-only successor laws."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import (
    datetime,
    timedelta,
    timezone,
)
import unittest

from forge2.contracts import (
    AuthorityStatus,
    ContractIntegrityError,
    ContractValidationError,
    DeclaredEffect,
    EffectKind,
    LifecycleState,
    SchemaVersion,
    SuccessorKind,
    SuccessorReceipt,
    create_contract_metadata,
    create_successor,
    verify_successor,
)


class SuccessorLawTests(unittest.TestCase):
    def setUp(self) -> None:
        self.body = {
            "raw_input": "hello",
            "conversation_context": [],
        }
        self.next_body = {
            "raw_input": "hello again",
            "conversation_context": [],
        }
        self.created_at = datetime(
            2026,
            7,
            30,
            20,
            15,
            tzinfo=timezone.utc,
        )
        self.next_time = (
            self.created_at
            + timedelta(minutes=1)
        )
        self.predecessor = (
            create_contract_metadata(
                schema_version="1.0.0",
                contract_type="InputEvent",
                body=self.body,
                created_at=self.created_at,
            )
        )

    def body_revision(self):
        return create_successor(
            predecessor=self.predecessor,
            predecessor_body=self.body,
            successor_body=self.next_body,
            created_at=self.next_time,
        )

    def test_fixed_body_revision_vector(
        self,
    ) -> None:
        transition = self.body_revision()

        self.assertEqual(
            transition.metadata.content_hash,
            (
                "061ac9bb26cd4e062dd0d194b526722d"
                "feee93444e4f73cc4628f4189a3aefb3"
            ),
        )
        self.assertEqual(
            transition.metadata.contract_id,
            (
                "aiweb.contract:sha256:"
                "e376a287b2624dcb84b0ebadb2743d41"
                "4d557e59ff9c68bf650b0814f9d8f963"
            ),
        )
        self.assertEqual(
            transition.receipt.receipt_id,
            (
                "aiweb.successor:sha256:"
                "b642c2e56c5df8513aa00314940a4852"
                "7874e6ea1fc94431ced4696af30384a0"
            ),
        )
        self.assertEqual(
            transition.receipt.kind,
            SuccessorKind.BODY_REVISION,
        )
        self.assertEqual(
            transition.receipt.rule_id,
            "successor.body_revision.v1",
        )
        self.assertEqual(
            transition.receipt.changed_fields,
            ("body",),
        )

    def test_parent_is_exact_predecessor(
        self,
    ) -> None:
        transition = self.body_revision()

        self.assertEqual(
            transition.metadata.parent,
            self.predecessor.to_reference(),
        )
        self.assertEqual(
            transition.receipt.predecessor,
            self.predecessor.to_reference(),
        )
        self.assertEqual(
            transition.receipt.successor,
            transition.metadata.to_reference(),
        )

    def test_creation_is_deterministic(
        self,
    ) -> None:
        first = self.body_revision()
        second = self.body_revision()

        self.assertEqual(first, second)

    def test_predecessor_is_not_mutated(
        self,
    ) -> None:
        original = self.predecessor

        self.body_revision()

        self.assertEqual(
            self.predecessor,
            original,
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            self.predecessor.contract_type = (
                "Changed"
            )

    def test_no_op_successor_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_successor(
                predecessor=self.predecessor,
                predecessor_body=self.body,
                successor_body=self.body,
                created_at=self.next_time,
            )

        self.assertEqual(
            context.exception.code,
            "no_successor_change",
        )

    def test_backdated_successor_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_successor(
                predecessor=self.predecessor,
                predecessor_body=self.body,
                successor_body=self.next_body,
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "successor_time_not_increasing",
        )

    def test_candidate_may_be_accepted(
        self,
    ) -> None:
        transition = create_successor(
            predecessor=self.predecessor,
            predecessor_body=self.body,
            successor_body=self.body,
            created_at=self.next_time,
            lifecycle_state=(
                LifecycleState.ACCEPTED
            ),
        )

        self.assertEqual(
            transition.receipt.kind,
            (
                SuccessorKind
                .LIFECYCLE_TRANSITION
            ),
        )
        self.assertEqual(
            transition.receipt.rule_id,
            (
                "successor.lifecycle_candidate_"
                "to_accepted.v1"
            ),
        )

    def test_invalid_lifecycle_reversal(
        self,
    ) -> None:
        accepted = create_successor(
            predecessor=self.predecessor,
            predecessor_body=self.body,
            successor_body=self.body,
            created_at=self.next_time,
            lifecycle_state=(
                LifecycleState.ACCEPTED
            ),
        )

        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_successor(
                predecessor=accepted.metadata,
                predecessor_body=self.body,
                successor_body=self.body,
                created_at=(
                    self.next_time
                    + timedelta(minutes=1)
                ),
                lifecycle_state=(
                    LifecycleState.CANDIDATE
                ),
            )

        self.assertEqual(
            context.exception.code,
            "invalid_lifecycle_transition",
        )

    def test_authority_request_then_authorize(
        self,
    ) -> None:
        requested = create_successor(
            predecessor=self.predecessor,
            predecessor_body=self.body,
            successor_body=self.body,
            created_at=self.next_time,
            authority_status=(
                AuthorityStatus.REQUESTED
            ),
        )
        authorized = create_successor(
            predecessor=requested.metadata,
            predecessor_body=self.body,
            successor_body=self.body,
            created_at=(
                self.next_time
                + timedelta(minutes=1)
            ),
            authority_status=(
                AuthorityStatus.AUTHORIZED
            ),
        )

        self.assertEqual(
            requested.receipt.kind,
            (
                SuccessorKind
                .AUTHORITY_TRANSITION
            ),
        )
        self.assertEqual(
            authorized.metadata.authority_status,
            AuthorityStatus.AUTHORIZED,
        )

    def test_none_to_authorized_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_successor(
                predecessor=self.predecessor,
                predecessor_body=self.body,
                successor_body=self.body,
                created_at=self.next_time,
                authority_status=(
                    AuthorityStatus.AUTHORIZED
                ),
            )

        self.assertEqual(
            context.exception.code,
            "invalid_authority_transition",
        )

    def test_effect_revision_is_canonical(
        self,
    ) -> None:
        transition = create_successor(
            predecessor=self.predecessor,
            predecessor_body=self.body,
            successor_body=self.body,
            created_at=self.next_time,
            declared_effects=[
                DeclaredEffect(
                    EffectKind.WRITE,
                    "workspace:/receipt",
                ),
                DeclaredEffect(
                    EffectKind.READ,
                    "workspace:/repository",
                ),
            ],
        )

        self.assertEqual(
            transition.receipt.kind,
            SuccessorKind.EFFECTS_REVISION,
        )
        self.assertEqual(
            tuple(
                effect.kind
                for effect
                in transition.metadata.declared_effects
            ),
            (
                EffectKind.READ,
                EffectKind.WRITE,
            ),
        )

    def test_patch_schema_step(
        self,
    ) -> None:
        transition = create_successor(
            predecessor=self.predecessor,
            predecessor_body=self.body,
            successor_body=self.body,
            created_at=self.next_time,
            schema_version="1.0.1",
        )

        self.assertEqual(
            transition.metadata.schema_version,
            SchemaVersion(1, 0, 1),
        )
        self.assertEqual(
            transition.receipt.kind,
            SuccessorKind.SCHEMA_REVISION,
        )
        self.assertEqual(
            transition.receipt.rule_id,
            "successor.schema_patch.v1",
        )

    def test_schema_and_body_may_change_together(
        self,
    ) -> None:
        transition = create_successor(
            predecessor=self.predecessor,
            predecessor_body=self.body,
            successor_body=self.next_body,
            created_at=self.next_time,
            schema_version="1.1.0",
        )

        self.assertEqual(
            transition.receipt.changed_fields,
            (
                "body",
                "schema_version",
            ),
        )
        self.assertEqual(
            transition.receipt.rule_id,
            "successor.schema_minor.v1",
        )

    def test_schema_skip_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_successor(
                predecessor=self.predecessor,
                predecessor_body=self.body,
                successor_body=self.body,
                created_at=self.next_time,
                schema_version="1.0.2",
            )

        self.assertEqual(
            context.exception.code,
            "invalid_schema_successor_step",
        )

    def test_mixed_body_and_lifecycle_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_successor(
                predecessor=self.predecessor,
                predecessor_body=self.body,
                successor_body=self.next_body,
                created_at=self.next_time,
                lifecycle_state=(
                    LifecycleState.ACCEPTED
                ),
            )

        self.assertEqual(
            context.exception.code,
            "mixed_successor_dimensions",
        )

    def test_accepted_body_revision_rejected(
        self,
    ) -> None:
        accepted = create_successor(
            predecessor=self.predecessor,
            predecessor_body=self.body,
            successor_body=self.body,
            created_at=self.next_time,
            lifecycle_state=(
                LifecycleState.ACCEPTED
            ),
        )

        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_successor(
                predecessor=accepted.metadata,
                predecessor_body=self.body,
                successor_body=self.next_body,
                created_at=(
                    self.next_time
                    + timedelta(minutes=1)
                ),
            )

        self.assertEqual(
            context.exception.code,
            "body_revision_state_forbidden",
        )

    def test_verify_successor_passes(
        self,
    ) -> None:
        transition = self.body_revision()

        verify_successor(
            predecessor=self.predecessor,
            predecessor_body=self.body,
            successor=transition.metadata,
            successor_body=self.next_body,
            receipt=transition.receipt,
        )

    def test_wrong_successor_body_rejected(
        self,
    ) -> None:
        transition = self.body_revision()

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            verify_successor(
                predecessor=self.predecessor,
                predecessor_body=self.body,
                successor=transition.metadata,
                successor_body={
                    "wrong": True
                },
                receipt=transition.receipt,
            )

        self.assertEqual(
            context.exception.code,
            "content_hash_mismatch",
        )

    def test_tampered_receipt_id_rejected(
        self,
    ) -> None:
        transition = self.body_revision()
        receipt = transition.receipt

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            SuccessorReceipt(
                receipt_id=(
                    "aiweb.successor:sha256:"
                    + ("0" * 64)
                ),
                predecessor=receipt.predecessor,
                successor=receipt.successor,
                kind=receipt.kind,
                rule_id=receipt.rule_id,
                changed_fields=(
                    receipt.changed_fields
                ),
                observed_at=receipt.observed_at,
                predecessor_state_hash=(
                    receipt.predecessor_state_hash
                ),
                successor_state_hash=(
                    receipt.successor_state_hash
                ),
            )

        self.assertEqual(
            context.exception.code,
            "successor_receipt_id_mismatch",
        )

    def test_receipt_is_immutable(
        self,
    ) -> None:
        receipt = self.body_revision().receipt

        with self.assertRaises(
            FrozenInstanceError
        ):
            receipt.rule_id = "changed"


if __name__ == "__main__":
    unittest.main(verbosity=2)
