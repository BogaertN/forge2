"""Tests for exact request-state identities."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

import forge2.contracts.request_state as module
from forge2.contracts import (
    ContractIntegrityError,
    ContractValidationError,
    REQUEST_STATE_REGISTRY,
    REQUEST_STATE_SCHEMA_VERSION,
    REQUEST_STATE_SEQUENCE,
    RequestState,
    RequestStateIdentity,
    RequestStateRegistry,
    SchemaVersion,
    create_request_state_registry,
    request_state_from_value,
    request_state_identity,
)


EXPECTED_VALUES = (
    "RECEIVED",
    "CUSTODIED",
    "INTERPRETATION_CANDIDATES_READY",
    "CLARIFICATION_REQUIRED",
    "REQUEST_CONTRACT_READY",
    "CONTEXT_READY",
    "CAPABILITY_REQUIREMENTS_READY",
    "CAPABILITY_RESOLVED",
    "PLAN_READY",
    "AWAITING_AUTHORITY",
    "AUTHORIZED",
    "EXECUTING",
    "EXECUTION_COMPLETE",
    "VERIFYING",
    "VERIFIED",
    "FAILED",
    "HELD",
    "CANCELLED",
    "RESULT_READY",
    "DELIVERED",
    "APPLY_PENDING",
    "APPLIED",
    "COMMITTED",
    "RELEASED",
    "ARCHIVED",
)


class RequestStateIdentityTests(
    unittest.TestCase
):
    def test_exact_state_values(self) -> None:
        self.assertEqual(
            tuple(
                state.value
                for state
                in REQUEST_STATE_SEQUENCE
            ),
            EXPECTED_VALUES,
        )
        self.assertEqual(
            tuple(
                state.value
                for state in RequestState
            ),
            EXPECTED_VALUES,
        )

    def test_exact_state_count(self) -> None:
        self.assertEqual(
            len(REQUEST_STATE_SEQUENCE),
            25,
        )
        self.assertEqual(
            len(set(REQUEST_STATE_SEQUENCE)),
            25,
        )

    def test_received_fixed_identity(
        self,
    ) -> None:
        identity = request_state_identity(
            RequestState.RECEIVED
        )

        self.assertEqual(
            identity.ordinal,
            0,
        )
        self.assertEqual(
            identity.state_code,
            "request.state.received.v1",
        )
        self.assertEqual(
            identity.state_id,
            (
                "aiweb.request-state:sha256:"
                "60472d4866543431ce0836292deb9d62"
                "ae9157ba88a4eb433b82076db0a80c1d"
            ),
        )

    def test_archived_fixed_identity(
        self,
    ) -> None:
        identity = request_state_identity(
            RequestState.ARCHIVED
        )

        self.assertEqual(
            identity.ordinal,
            24,
        )
        self.assertEqual(
            identity.state_code,
            "request.state.archived.v1",
        )
        self.assertEqual(
            identity.state_id,
            (
                "aiweb.request-state:sha256:"
                "c269691823c6c3b0c9f315df49eb5e48"
                "fb2114d2622534b4ece669963481ff25"
            ),
        )

    def test_registry_fixed_identity(
        self,
    ) -> None:
        registry = (
            create_request_state_registry()
        )

        self.assertEqual(
            registry.registry_id,
            (
                "aiweb.request-state-registry:"
                "sha256:"
                "2abe0345a66300db59928e416dd358f8"
                "36dc05c8017cdfd8f75dd9b376b16e5b"
            ),
        )
        self.assertEqual(
            registry,
            REQUEST_STATE_REGISTRY,
        )

    def test_registry_policy_is_held(
        self,
    ) -> None:
        self.assertIs(
            REQUEST_STATE_REGISTRY
            .transition_policy_defined,
            False,
        )

    def test_exact_string_parse(self) -> None:
        self.assertIs(
            request_state_from_value(
                "PLAN_READY"
            ),
            RequestState.PLAN_READY,
        )

    def test_lowercase_is_rejected(self) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            request_state_from_value(
                "plan_ready"
            )

        self.assertEqual(
            context.exception.code,
            "unknown_request_state",
        )

    def test_unknown_state_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ):
            request_state_from_value(
                "READY"
            )

    def test_non_text_state_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            request_state_from_value(1)

        self.assertEqual(
            context.exception.code,
            "invalid_request_state_type",
        )

    def test_every_ordinal_is_exact(
        self,
    ) -> None:
        for ordinal, state in enumerate(
            REQUEST_STATE_SEQUENCE
        ):
            with self.subTest(state=state):
                identity = (
                    request_state_identity(
                        state
                    )
                )
                self.assertEqual(
                    identity.ordinal,
                    ordinal,
                )

    def test_every_code_is_exact(
        self,
    ) -> None:
        for state in REQUEST_STATE_SEQUENCE:
            with self.subTest(state=state):
                identity = (
                    request_state_identity(
                        state
                    )
                )
                self.assertEqual(
                    identity.state_code,
                    (
                        "request.state."
                        f"{state.value.lower()}.v1"
                    ),
                )

    def test_state_identity_is_immutable(
        self,
    ) -> None:
        identity = request_state_identity(
            RequestState.RECEIVED
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            identity.ordinal = 99

    def test_registry_is_immutable(self) -> None:
        with self.assertRaises(
            FrozenInstanceError
        ):
            (
                REQUEST_STATE_REGISTRY
                .transition_policy_defined
            ) = True

    def test_forged_state_id_rejected(
        self,
    ) -> None:
        identity = request_state_identity(
            RequestState.RECEIVED
        )

        with self.assertRaises(
            ContractIntegrityError
        ) as context:
            RequestStateIdentity(
                state=identity.state,
                ordinal=identity.ordinal,
                state_code=(
                    identity.state_code
                ),
                schema_version=(
                    identity.schema_version
                ),
                state_id=(
                    "aiweb.request-state:sha256:"
                    + ("0" * 64)
                ),
            )

        self.assertEqual(
            context.exception.code,
            "request_state_id_mismatch",
        )

    def test_wrong_ordinal_rejected(
        self,
    ) -> None:
        identity = request_state_identity(
            RequestState.RECEIVED
        )

        with self.assertRaises(
            ContractValidationError
        ) as context:
            RequestStateIdentity(
                state=identity.state,
                ordinal=1,
                state_code=(
                    identity.state_code
                ),
                schema_version=(
                    identity.schema_version
                ),
                state_id=identity.state_id,
            )

        self.assertEqual(
            context.exception.code,
            "state_ordinal_mismatch",
        )

    def test_wrong_state_code_rejected(
        self,
    ) -> None:
        identity = request_state_identity(
            RequestState.RECEIVED
        )

        with self.assertRaises(
            ContractValidationError
        ) as context:
            RequestStateIdentity(
                state=identity.state,
                ordinal=identity.ordinal,
                state_code=(
                    "request.state.wrong.v1"
                ),
                schema_version=(
                    identity.schema_version
                ),
                state_id=identity.state_id,
            )

        self.assertEqual(
            context.exception.code,
            "state_code_mismatch",
        )

    def test_wrong_schema_rejected(
        self,
    ) -> None:
        identity = request_state_identity(
            RequestState.RECEIVED
        )

        with self.assertRaises(
            ContractValidationError
        ):
            RequestStateIdentity(
                state=identity.state,
                ordinal=identity.ordinal,
                state_code=(
                    identity.state_code
                ),
                schema_version=(
                    SchemaVersion(1, 0, 1)
                ),
                state_id=identity.state_id,
            )

    def test_reordered_registry_rejected(
        self,
    ) -> None:
        states = tuple(
            reversed(
                REQUEST_STATE_REGISTRY.states
            )
        )

        with self.assertRaises(
            ContractValidationError
        ) as context:
            RequestStateRegistry(
                schema_version=(
                    REQUEST_STATE_SCHEMA_VERSION
                ),
                states=states,
                transition_policy_defined=False,
                registry_id=(
                    REQUEST_STATE_REGISTRY
                    .registry_id
                ),
            )

        self.assertEqual(
            context.exception.code,
            (
                "registry_state_"
                "sequence_mismatch"
            ),
        )

    def test_premature_policy_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ContractValidationError
        ) as context:
            RequestStateRegistry(
                schema_version=(
                    REQUEST_STATE_SCHEMA_VERSION
                ),
                states=(
                    REQUEST_STATE_REGISTRY
                    .states
                ),
                transition_policy_defined=True,
                registry_id=(
                    REQUEST_STATE_REGISTRY
                    .registry_id
                ),
            )

        self.assertEqual(
            context.exception.code,
            (
                "transition_policy_"
                "prematurely_defined"
            ),
        )

    def test_no_transition_api_exists(
        self,
    ) -> None:
        forbidden = (
            "allowed_request_transitions",
            "create_request_transition",
            "request_transition_allowed",
            "RequestStateTransitionReceipt",
        )

        for name in forbidden:
            with self.subTest(name=name):
                self.assertFalse(
                    hasattr(module, name)
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
