"""Exact request-lifecycle state identities.

This module defines state vocabulary and identity only.
It intentionally defines no transition permissions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Any, Final

from .canonical import stable_identifier
from .identity import (
    ContractIntegrityError,
    ContractValidationError,
    SchemaVersion,
)


REQUEST_STATE_ID_NAMESPACE: Final[str] = (
    "aiweb.request-state"
)
REQUEST_STATE_REGISTRY_NAMESPACE: Final[str] = (
    "aiweb.request-state-registry"
)
REQUEST_STATE_SCHEMA_VERSION: Final[
    SchemaVersion
] = SchemaVersion(1, 0, 0)

_STATE_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.request-state:sha256:"
    r"[0-9a-f]{64}$"
)
_REGISTRY_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.request-state-registry:sha256:"
    r"[0-9a-f]{64}$"
)
_STATE_CODE_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^request\.state\.[a-z0-9_]+\.v1$"
)


class RequestState(StrEnum):
    """Exact request states named by the roadmap."""

    RECEIVED = "RECEIVED"
    CUSTODIED = "CUSTODIED"
    INTERPRETATION_CANDIDATES_READY = (
        "INTERPRETATION_CANDIDATES_READY"
    )
    CLARIFICATION_REQUIRED = (
        "CLARIFICATION_REQUIRED"
    )
    REQUEST_CONTRACT_READY = (
        "REQUEST_CONTRACT_READY"
    )
    CONTEXT_READY = "CONTEXT_READY"
    CAPABILITY_REQUIREMENTS_READY = (
        "CAPABILITY_REQUIREMENTS_READY"
    )
    CAPABILITY_RESOLVED = (
        "CAPABILITY_RESOLVED"
    )
    PLAN_READY = "PLAN_READY"
    AWAITING_AUTHORITY = (
        "AWAITING_AUTHORITY"
    )
    AUTHORIZED = "AUTHORIZED"
    EXECUTING = "EXECUTING"
    EXECUTION_COMPLETE = (
        "EXECUTION_COMPLETE"
    )
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    HELD = "HELD"
    CANCELLED = "CANCELLED"
    RESULT_READY = "RESULT_READY"
    DELIVERED = "DELIVERED"
    APPLY_PENDING = "APPLY_PENDING"
    APPLIED = "APPLIED"
    COMMITTED = "COMMITTED"
    RELEASED = "RELEASED"
    ARCHIVED = "ARCHIVED"


REQUEST_STATE_SEQUENCE: Final[
    tuple[RequestState, ...]
] = (
    RequestState.RECEIVED,
    RequestState.CUSTODIED,
    (
        RequestState
        .INTERPRETATION_CANDIDATES_READY
    ),
    RequestState.CLARIFICATION_REQUIRED,
    RequestState.REQUEST_CONTRACT_READY,
    RequestState.CONTEXT_READY,
    (
        RequestState
        .CAPABILITY_REQUIREMENTS_READY
    ),
    RequestState.CAPABILITY_RESOLVED,
    RequestState.PLAN_READY,
    RequestState.AWAITING_AUTHORITY,
    RequestState.AUTHORIZED,
    RequestState.EXECUTING,
    RequestState.EXECUTION_COMPLETE,
    RequestState.VERIFYING,
    RequestState.VERIFIED,
    RequestState.FAILED,
    RequestState.HELD,
    RequestState.CANCELLED,
    RequestState.RESULT_READY,
    RequestState.DELIVERED,
    RequestState.APPLY_PENDING,
    RequestState.APPLIED,
    RequestState.COMMITTED,
    RequestState.RELEASED,
    RequestState.ARCHIVED,
)

_STATE_ORDINAL: Final[
    dict[RequestState, int]
] = {
    state: ordinal
    for ordinal, state
    in enumerate(REQUEST_STATE_SEQUENCE)
}


def _validation_error(
    code: str,
    field: str,
    message: str,
) -> ContractValidationError:
    return ContractValidationError(
        code,
        field,
        message,
    )


def request_state_from_value(
    value: object,
) -> RequestState:
    """Parse only an exact roadmap state value."""

    if not isinstance(value, str):
        raise _validation_error(
            "invalid_request_state_type",
            "state",
            "Request state must be text.",
        )

    try:
        return RequestState(value)
    except ValueError as error:
        raise _validation_error(
            "unknown_request_state",
            "state",
            (
                "Value is not an exact "
                "roadmap request state."
            ),
        ) from error


def _expected_state_code(
    state: RequestState,
) -> str:
    return (
        "request.state."
        f"{state.value.lower()}.v1"
    )


def _state_material(
    *,
    state: RequestState,
    ordinal: int,
    state_code: str,
    schema_version: SchemaVersion,
) -> dict[str, Any]:
    return {
        "ordinal": ordinal,
        "schema_version": str(
            schema_version
        ),
        "state": state.value,
        "state_code": state_code,
    }


def _expected_state_id(
    *,
    state: RequestState,
    ordinal: int,
    state_code: str,
    schema_version: SchemaVersion,
) -> str:
    return stable_identifier(
        REQUEST_STATE_ID_NAMESPACE,
        _state_material(
            state=state,
            ordinal=ordinal,
            state_code=state_code,
            schema_version=schema_version,
        ),
    )


@dataclass(frozen=True, slots=True)
class RequestStateIdentity:
    """Immutable identity for one exact state."""

    state: RequestState
    ordinal: int
    state_code: str
    schema_version: SchemaVersion
    state_id: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.state,
            RequestState,
        ):
            raise _validation_error(
                "invalid_request_state",
                "state",
                (
                    "State must be "
                    "RequestState."
                ),
            )

        if (
            isinstance(self.ordinal, bool)
            or not isinstance(
                self.ordinal,
                int,
            )
        ):
            raise _validation_error(
                "invalid_state_ordinal_type",
                "ordinal",
                "Ordinal must be an integer.",
            )

        expected_ordinal = _STATE_ORDINAL[
            self.state
        ]

        if self.ordinal != expected_ordinal:
            raise _validation_error(
                "state_ordinal_mismatch",
                "ordinal",
                (
                    "Ordinal does not match "
                    "the roadmap sequence."
                ),
            )

        expected_code = (
            _expected_state_code(
                self.state
            )
        )

        if (
            not isinstance(
                self.state_code,
                str,
            )
            or not _STATE_CODE_PATTERN.fullmatch(
                self.state_code
            )
            or self.state_code
            != expected_code
        ):
            raise _validation_error(
                "state_code_mismatch",
                "state_code",
                (
                    "State code does not match "
                    "the state identity."
                ),
            )

        if (
            not isinstance(
                self.schema_version,
                SchemaVersion,
            )
            or self.schema_version
            != REQUEST_STATE_SCHEMA_VERSION
        ):
            raise _validation_error(
                (
                    "request_state_schema_"
                    "version_mismatch"
                ),
                "schema_version",
                (
                    "State identity must use "
                    "schema version 1.0.0."
                ),
            )

        if (
            not isinstance(
                self.state_id,
                str,
            )
            or not _STATE_ID_PATTERN.fullmatch(
                self.state_id
            )
        ):
            raise _validation_error(
                "invalid_request_state_id",
                "state_id",
                (
                    "State ID must use the "
                    "aiweb.request-state "
                    "SHA-256 form."
                ),
            )

        expected_id = _expected_state_id(
            state=self.state,
            ordinal=self.ordinal,
            state_code=self.state_code,
            schema_version=(
                self.schema_version
            ),
        )

        if self.state_id != expected_id:
            raise ContractIntegrityError(
                "request_state_id_mismatch",
                "state_id",
                (
                    "State ID does not match "
                    "its identity material."
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "ordinal": self.ordinal,
            "state_code": self.state_code,
            "schema_version": str(
                self.schema_version
            ),
            "state_id": self.state_id,
        }


def request_state_identity(
    value: RequestState | str,
) -> RequestStateIdentity:
    """Construct an exact immutable state identity."""

    state = (
        value
        if isinstance(value, RequestState)
        else request_state_from_value(value)
    )
    ordinal = _STATE_ORDINAL[state]
    state_code = _expected_state_code(
        state
    )
    state_id = _expected_state_id(
        state=state,
        ordinal=ordinal,
        state_code=state_code,
        schema_version=(
            REQUEST_STATE_SCHEMA_VERSION
        ),
    )

    return RequestStateIdentity(
        state=state,
        ordinal=ordinal,
        state_code=state_code,
        schema_version=(
            REQUEST_STATE_SCHEMA_VERSION
        ),
        state_id=state_id,
    )


def _registry_material(
    *,
    schema_version: SchemaVersion,
    states: tuple[
        RequestStateIdentity,
        ...,
    ],
    transition_policy_defined: bool,
) -> dict[str, Any]:
    return {
        "schema_version": str(
            schema_version
        ),
        "states": [
            identity.to_dict()
            for identity in states
        ],
        "transition_policy_defined": (
            transition_policy_defined
        ),
    }


def _expected_registry_id(
    *,
    schema_version: SchemaVersion,
    states: tuple[
        RequestStateIdentity,
        ...,
    ],
    transition_policy_defined: bool,
) -> str:
    return stable_identifier(
        REQUEST_STATE_REGISTRY_NAMESPACE,
        _registry_material(
            schema_version=schema_version,
            states=states,
            transition_policy_defined=(
                transition_policy_defined
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class RequestStateRegistry:
    """Exact registry with transition policy held."""

    schema_version: SchemaVersion
    states: tuple[
        RequestStateIdentity,
        ...,
    ]
    transition_policy_defined: bool
    registry_id: str

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.schema_version,
                SchemaVersion,
            )
            or self.schema_version
            != REQUEST_STATE_SCHEMA_VERSION
        ):
            raise _validation_error(
                (
                    "request_state_registry_"
                    "schema_mismatch"
                ),
                "schema_version",
                (
                    "Registry must use "
                    "schema version 1.0.0."
                ),
            )

        if not isinstance(
            self.states,
            tuple,
        ):
            raise _validation_error(
                "registry_states_not_immutable",
                "states",
                (
                    "Registry states must be "
                    "stored as a tuple."
                ),
            )

        expected_states = tuple(
            request_state_identity(state)
            for state
            in REQUEST_STATE_SEQUENCE
        )

        if self.states != expected_states:
            raise _validation_error(
                (
                    "registry_state_"
                    "sequence_mismatch"
                ),
                "states",
                (
                    "Registry states must match "
                    "the exact roadmap sequence."
                ),
            )

        if (
            self.transition_policy_defined
            is not False
        ):
            raise _validation_error(
                (
                    "transition_policy_"
                    "prematurely_defined"
                ),
                "transition_policy_defined",
                (
                    "Build 005A must not define "
                    "transition permissions."
                ),
            )

        if (
            not isinstance(
                self.registry_id,
                str,
            )
            or not _REGISTRY_ID_PATTERN.fullmatch(
                self.registry_id
            )
        ):
            raise _validation_error(
                "invalid_request_state_registry_id",
                "registry_id",
                (
                    "Registry ID must use the "
                    "approved SHA-256 form."
                ),
            )

        expected_id = _expected_registry_id(
            schema_version=(
                self.schema_version
            ),
            states=self.states,
            transition_policy_defined=False,
        )

        if self.registry_id != expected_id:
            raise ContractIntegrityError(
                (
                    "request_state_registry_"
                    "id_mismatch"
                ),
                "registry_id",
                (
                    "Registry ID does not match "
                    "its exact state material."
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": str(
                self.schema_version
            ),
            "states": [
                identity.to_dict()
                for identity in self.states
            ],
            "transition_policy_defined": (
                self.transition_policy_defined
            ),
            "registry_id": self.registry_id,
        }


def create_request_state_registry(
) -> RequestStateRegistry:
    """Create the exact held-policy registry."""

    states = tuple(
        request_state_identity(state)
        for state in REQUEST_STATE_SEQUENCE
    )
    registry_id = _expected_registry_id(
        schema_version=(
            REQUEST_STATE_SCHEMA_VERSION
        ),
        states=states,
        transition_policy_defined=False,
    )

    return RequestStateRegistry(
        schema_version=(
            REQUEST_STATE_SCHEMA_VERSION
        ),
        states=states,
        transition_policy_defined=False,
        registry_id=registry_id,
    )


REQUEST_STATE_REGISTRY: Final[
    RequestStateRegistry
] = create_request_state_registry()


__all__ = (
    "REQUEST_STATE_ID_NAMESPACE",
    "REQUEST_STATE_REGISTRY",
    "REQUEST_STATE_REGISTRY_NAMESPACE",
    "REQUEST_STATE_SCHEMA_VERSION",
    "REQUEST_STATE_SEQUENCE",
    "RequestState",
    "RequestStateIdentity",
    "RequestStateRegistry",
    "create_request_state_registry",
    "request_state_from_value",
    "request_state_identity",
)
