"""Invariant tests for immutable contract identity."""

from __future__ import annotations

from dataclasses import (
    FrozenInstanceError,
)
from datetime import (
    datetime,
    timedelta,
    timezone,
)
import unittest

from forge2.contracts import (
    AuthorityStatus,
    ContractIntegrityError,
    ContractMetadata,
    ContractReference,
    ContractValidationError,
    DeclaredEffect,
    EffectKind,
    LifecycleState,
    SchemaVersion,
    create_contract_metadata,
    verify_contract_metadata,
)


class ContractIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.body = {
            "raw_input": "hello",
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

    def create(
        self,
        **overrides: object,
    ) -> ContractMetadata:
        values: dict[str, object] = {
            "schema_version": "1.0.0",
            "contract_type": "InputEvent",
            "body": self.body,
            "created_at": self.created_at,
        }
        values.update(overrides)

        return create_contract_metadata(
            **values,
        )

    def test_fixed_identity_vector(self) -> None:
        metadata = self.create()

        self.assertEqual(
            metadata.content_hash,
            (
                "42d05d320c302a6fb5c5657f12d1f47f"
                "f4c5394a04b5ede825ed880d92ad9e31"
            ),
        )
        self.assertEqual(
            metadata.contract_id,
            (
                "aiweb.contract:sha256:"
                "511d7a8fae0fa5279524c6f2042347c7"
                "d8c22fe80a8589cbfd13bf6b65607140"
            ),
        )
        self.assertEqual(
            metadata.schema_version,
            SchemaVersion(1, 0, 0),
        )
        self.assertEqual(
            metadata.lifecycle_state,
            LifecycleState.CANDIDATE,
        )
        self.assertEqual(
            metadata.authority_status,
            AuthorityStatus.NONE,
        )

    def test_mapping_order_is_invariant(
        self,
    ) -> None:
        first = self.create(
            body={
                "beta": 2,
                "alpha": 1,
            }
        )
        second = self.create(
            body={
                "alpha": 1,
                "beta": 2,
            }
        )

        self.assertEqual(first, second)

    def test_timezone_is_normalized_to_utc(
        self,
    ) -> None:
        offset = timezone(
            -timedelta(hours=4)
        )

        first = self.create(
            created_at=datetime(
                2026,
                7,
                30,
                16,
                15,
                tzinfo=offset,
            )
        )
        second = self.create()

        self.assertEqual(first, second)
        self.assertEqual(
            first.created_at,
            self.created_at,
        )

    def test_body_change_changes_identity(
        self,
    ) -> None:
        first = self.create()
        second = self.create(
            body={
                "raw_input": "changed",
                "conversation_context": [],
            }
        )

        self.assertNotEqual(
            first.content_hash,
            second.content_hash,
        )
        self.assertNotEqual(
            first.contract_id,
            second.contract_id,
        )

    def test_lifecycle_changes_identity(
        self,
    ) -> None:
        candidate = self.create()
        accepted = self.create(
            lifecycle_state=(
                LifecycleState.ACCEPTED
            )
        )

        self.assertNotEqual(
            candidate.contract_id,
            accepted.contract_id,
        )

    def test_authority_changes_identity(
        self,
    ) -> None:
        none = self.create()
        requested = self.create(
            authority_status=(
                AuthorityStatus.REQUESTED
            )
        )

        self.assertNotEqual(
            none.contract_id,
            requested.contract_id,
        )

    def test_effect_input_order_is_canonical(
        self,
    ) -> None:
        write_effect = DeclaredEffect(
            EffectKind.WRITE,
            "workspace:/receipt",
        )
        read_effect = DeclaredEffect(
            EffectKind.READ,
            "workspace:/repository",
        )

        first = self.create(
            authority_status=(
                AuthorityStatus.REQUESTED
            ),
            declared_effects=[
                write_effect,
                read_effect,
            ],
        )
        second = self.create(
            authority_status=(
                AuthorityStatus.REQUESTED
            ),
            declared_effects=[
                read_effect,
                write_effect,
            ],
        )

        self.assertEqual(first, second)
        self.assertEqual(
            tuple(
                effect.kind
                for effect
                in first.declared_effects
            ),
            (
                EffectKind.READ,
                EffectKind.WRITE,
            ),
        )

    def test_effect_change_changes_identity(
        self,
    ) -> None:
        first = self.create(
            declared_effects=[
                DeclaredEffect(
                    EffectKind.READ,
                    "workspace:/one",
                )
            ]
        )
        second = self.create(
            declared_effects=[
                DeclaredEffect(
                    EffectKind.READ,
                    "workspace:/two",
                )
            ]
        )

        self.assertNotEqual(
            first.contract_id,
            second.contract_id,
        )

    def test_duplicate_effect_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            self.create(
                declared_effects=[
                    DeclaredEffect(
                        EffectKind.READ,
                        "workspace:/same",
                        "First description",
                    ),
                    DeclaredEffect(
                        EffectKind.READ,
                        "workspace:/same",
                        "Second description",
                    ),
                ]
            )

        self.assertEqual(
            context.exception.code,
            "duplicate_declared_effect",
        )

    def test_invalid_effect_target_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ):
            DeclaredEffect(
                EffectKind.READ,
                " workspace:/repository",
            )

    def test_parent_changes_identity(self) -> None:
        parent = self.create()
        successor = self.create(
            parent=parent.to_reference(),
        )

        self.assertNotEqual(
            parent.contract_id,
            successor.contract_id,
        )
        self.assertEqual(
            successor.parent,
            parent.to_reference(),
        )

    def test_reference_round_trip(self) -> None:
        metadata = self.create()
        reference = metadata.to_reference()

        self.assertEqual(
            reference,
            ContractReference(
                contract_id=(
                    metadata.contract_id
                ),
                content_hash=(
                    metadata.content_hash
                ),
                contract_type=(
                    metadata.contract_type
                ),
                schema_version=(
                    metadata.schema_version
                ),
            ),
        )

    def test_forged_contract_id_is_rejected(
        self,
    ) -> None:
        metadata = self.create()

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            ContractMetadata(
                schema_version=(
                    metadata.schema_version
                ),
                contract_type=(
                    metadata.contract_type
                ),
                contract_id=(
                    "aiweb.contract:sha256:"
                    + ("0" * 64)
                ),
                content_hash=(
                    metadata.content_hash
                ),
                created_at=(
                    metadata.created_at
                ),
                lifecycle_state=(
                    metadata.lifecycle_state
                ),
                authority_status=(
                    metadata.authority_status
                ),
            )

        self.assertEqual(
            context.exception.code,
            "contract_id_mismatch",
        )

    def test_body_mismatch_is_rejected(
        self,
    ) -> None:
        metadata = self.create()

        verify_contract_metadata(
            metadata,
            self.body,
        )

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            verify_contract_metadata(
                metadata,
                {"different": True},
            )

        self.assertEqual(
            context.exception.code,
            "content_hash_mismatch",
        )

    def test_metadata_is_immutable(
        self,
    ) -> None:
        metadata = self.create()

        with self.assertRaises(
            FrozenInstanceError
        ):
            metadata.contract_type = "Changed"

    def test_stored_effects_must_be_tuple(
        self,
    ) -> None:
        metadata = self.create()

        with self.assertRaises(
            ContractValidationError
        ) as context:
            ContractMetadata(
                schema_version=(
                    metadata.schema_version
                ),
                contract_type=(
                    metadata.contract_type
                ),
                contract_id=(
                    metadata.contract_id
                ),
                content_hash=(
                    metadata.content_hash
                ),
                created_at=(
                    metadata.created_at
                ),
                lifecycle_state=(
                    metadata.lifecycle_state
                ),
                authority_status=(
                    metadata.authority_status
                ),
                declared_effects=[],
            )

        self.assertEqual(
            context.exception.code,
            "effects_not_immutable",
        )

    def test_schema_version_parsing(
        self,
    ) -> None:
        version = SchemaVersion.parse(
            "12.34.56"
        )

        self.assertEqual(
            version,
            SchemaVersion(12, 34, 56),
        )
        self.assertEqual(
            str(version),
            "12.34.56",
        )

    def test_schema_version_ordering(
        self,
    ) -> None:
        self.assertLess(
            SchemaVersion(1, 0, 0),
            SchemaVersion(1, 1, 0),
        )
        self.assertLess(
            SchemaVersion(1, 1, 0),
            SchemaVersion(2, 0, 0),
        )

    def test_invalid_schema_strings(
        self,
    ) -> None:
        for value in (
            "",
            "1",
            "1.0",
            "01.0.0",
            "1.00.0",
            "1.0.00",
            "-1.0.0",
            "1.0.0.0",
        ):
            with self.subTest(value=value):
                with self.assertRaises(
                    ContractValidationError
                ):
                    SchemaVersion.parse(
                        value
                    )

    def test_invalid_schema_components(
        self,
    ) -> None:
        for values in (
            (True, 0, 0),
            (-1, 0, 0),
            (0, -1, 0),
            (0, 0, -1),
        ):
            with self.subTest(values=values):
                with self.assertRaises(
                    ContractValidationError
                ):
                    SchemaVersion(*values)

    def test_contract_type_validation(
        self,
    ) -> None:
        for value in (
            "",
            "inputEvent",
            "Input_Event",
            " InputEvent",
            "InputEvent ",
            "Input/Event",
        ):
            with self.subTest(value=value):
                with self.assertRaises(
                    ContractValidationError
                ):
                    self.create(
                        contract_type=value
                    )

    def test_invalid_reference_hash(
        self,
    ) -> None:
        metadata = self.create()

        with self.assertRaises(
            ContractValidationError
        ) as context:
            ContractReference(
                contract_id=(
                    metadata.contract_id
                ),
                content_hash="ABC",
                contract_type="InputEvent",
                schema_version=(
                    SchemaVersion(1, 0, 0)
                ),
            )

        self.assertEqual(
            context.exception.code,
            "invalid_sha256",
        )

    def test_error_has_structured_payload(
        self,
    ) -> None:
        try:
            SchemaVersion.parse(
                "01.0.0"
            )
        except ContractValidationError as error:
            self.assertEqual(
                error.to_dict(),
                {
                    "code": (
                        "invalid_schema_version"
                    ),
                    "field": "schema_version",
                    "message": (
                        "Schema version must have "
                        "canonical major.minor.patch "
                        "form."
                    ),
                },
            )
        else:
            self.fail(
                "Expected validation failure."
            )

    def test_state_vocabularies_are_exact(
        self,
    ) -> None:
        self.assertEqual(
            tuple(
                value.value
                for value in LifecycleState
            ),
            (
                "draft",
                "candidate",
                "accepted",
                "superseded",
                "rejected",
                "archived",
            ),
        )
        self.assertEqual(
            tuple(
                value.value
                for value in AuthorityStatus
            ),
            (
                "none",
                "advisory",
                "requested",
                "authorized",
                "denied",
                "revoked",
            ),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
