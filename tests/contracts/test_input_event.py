"""Tests for the immutable InputEvent contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import json
import unittest

from forge2.contracts import (
    AuthorityStatus,
    ContractIntegrityError,
    ContractValidationError,
    INPUT_EVENT_CONTRACT_TYPE,
    INPUT_EVENT_SCHEMA_VERSION,
    LifecycleState,
    canonical_json,
    create_input_event,
    input_event_from_dict,
    thaw_canonical,
    verify_input_event,
)


class InputEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.created_at = datetime(
            2026,
            7,
            30,
            21,
            0,
            tzinfo=timezone.utc,
        )
        self.raw_input = "hello"
        self.conversation_context = []
        self.identity_context = {
            "actor_id": "user:nic",
            "actor_kind": "user",
        }
        self.session_metadata = {
            "channel": "terminal",
            "session_id": "session-001",
        }

    def create(self):
        return create_input_event(
            raw_input=self.raw_input,
            conversation_context=(
                self.conversation_context
            ),
            identity_context=(
                self.identity_context
            ),
            session_metadata=(
                self.session_metadata
            ),
            created_at=self.created_at,
        )

    def test_fixed_vector(self) -> None:
        event = self.create()

        self.assertEqual(
            event.metadata.content_hash,
            (
                "adbd199e314785b7fa34f61dc0eb45f7"
                "b6926b42a231dd2c6f2f10420059a203"
            ),
        )
        self.assertEqual(
            event.metadata.contract_id,
            (
                "aiweb.contract:sha256:"
                "0dd5d9a67c192c391b3dbdc1ded74cff"
                "2e906fc24fe41c492c06ca310e417798"
            ),
        )

    def test_exact_metadata_defaults(
        self,
    ) -> None:
        event = self.create()

        self.assertEqual(
            event.metadata.contract_type,
            INPUT_EVENT_CONTRACT_TYPE,
        )
        self.assertEqual(
            event.metadata.schema_version,
            INPUT_EVENT_SCHEMA_VERSION,
        )
        self.assertEqual(
            event.metadata.lifecycle_state,
            LifecycleState.CANDIDATE,
        )
        self.assertEqual(
            event.metadata.authority_status,
            AuthorityStatus.NONE,
        )
        self.assertIsNone(
            event.metadata.parent
        )
        self.assertEqual(
            event.metadata.declared_effects,
            (),
        )

    def test_exact_four_part_body(
        self,
    ) -> None:
        event = self.create()

        self.assertEqual(
            event.body(),
            {
                "raw_input": "hello",
                "conversation_context": [],
                "identity_context": {
                    "actor_id": "user:nic",
                    "actor_kind": "user",
                },
                "session_metadata": {
                    "channel": "terminal",
                    "session_id": (
                        "session-001"
                    ),
                },
            },
        )

    def test_event_is_immutable(self) -> None:
        event = self.create()

        with self.assertRaises(
            FrozenInstanceError
        ):
            event.raw_input = "changed"

    def test_source_mutation_has_no_effect(
        self,
    ) -> None:
        context = [
            {
                "message": "before",
            }
        ]

        event = create_input_event(
            raw_input="hello",
            conversation_context=context,
            identity_context={},
            session_metadata={},
            created_at=self.created_at,
        )

        context[0]["message"] = "after"
        context.append(
            {
                "message": "new",
            }
        )

        self.assertEqual(
            thaw_canonical(
                event.conversation_context
            ),
            [
                {
                    "message": "before",
                }
            ],
        )

    def test_serialization_round_trip(
        self,
    ) -> None:
        event = self.create()
        serialized = canonical_json(
            event.to_dict()
        )
        decoded = json.loads(serialized)
        restored = input_event_from_dict(
            decoded
        )

        self.assertEqual(
            restored,
            event,
        )
        self.assertEqual(
            canonical_json(
                restored.to_dict()
            ),
            serialized,
        )

    def test_verify_passes(self) -> None:
        verify_input_event(
            self.create()
        )

    def test_hidden_top_level_field_rejected(
        self,
    ) -> None:
        event = self.create()
        value = event.to_dict()
        value["hidden"] = True

        with self.assertRaises(
            ContractValidationError
        ) as context:
            input_event_from_dict(value)

        self.assertEqual(
            context.exception.code,
            "mapping_key_mismatch",
        )

    def test_hidden_body_field_rejected(
        self,
    ) -> None:
        event = self.create()
        value = event.to_dict()
        value["body"]["hidden"] = True

        with self.assertRaises(
            ContractValidationError
        ):
            input_event_from_dict(value)

    def test_missing_body_field_rejected(
        self,
    ) -> None:
        event = self.create()
        value = event.to_dict()

        del value["body"][
            "session_metadata"
        ]

        with self.assertRaises(
            ContractValidationError
        ):
            input_event_from_dict(value)

    def test_input_event_cannot_carry_authority(
        self,
    ) -> None:
        event = self.create()
        value = event.to_dict()

        value["metadata"][
            "authority_status"
        ] = "authorized"

        with self.assertRaises(
            (
                ContractIntegrityError,
                ContractValidationError,
            )
        ):
            input_event_from_dict(value)

    def test_input_event_cannot_declare_effects(
        self,
    ) -> None:
        event = self.create()
        value = event.to_dict()

        value["metadata"][
            "declared_effects"
        ] = [
            {
                "kind": "execute",
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
            input_event_from_dict(value)

    def test_changed_body_fails_hash_binding(
        self,
    ) -> None:
        event = self.create()
        value = event.to_dict()
        value["body"]["raw_input"] = "changed"

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            input_event_from_dict(value)

        self.assertEqual(
            context.exception.code,
            "content_hash_mismatch",
        )

    def test_float_input_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            create_input_event(
                raw_input={
                    "value": 1.5,
                },
                conversation_context=[],
                identity_context={},
                session_metadata={},
                created_at=self.created_at,
            )

        self.assertEqual(
            context.exception.code,
            "invalid_input_event_field",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
