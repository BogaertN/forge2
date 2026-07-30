"""Immutable InputEvent contract for Forge 2."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from .canonical import (
    CanonicalizationError,
    canonicalize,
)
from .codec import (
    contract_metadata_from_dict,
    contract_metadata_to_dict,
)
from .frozen_value import (
    FrozenCanonicalValue,
    freeze_canonical,
    is_frozen_canonical,
    thaw_canonical,
)
from .identity import (
    AuthorityStatus,
    ContractMetadata,
    ContractValidationError,
    LifecycleState,
    SchemaVersion,
    create_contract_metadata,
    verify_contract_metadata,
)


INPUT_EVENT_CONTRACT_TYPE: Final[str] = (
    "InputEvent"
)
INPUT_EVENT_SCHEMA_VERSION: Final[
    SchemaVersion
] = SchemaVersion(1, 0, 0)

_TOP_LEVEL_KEYS: Final[
    frozenset[str]
] = frozenset(
    {
        "metadata",
        "body",
    }
)
_BODY_KEYS: Final[
    frozenset[str]
] = frozenset(
    {
        "raw_input",
        "conversation_context",
        "identity_context",
        "session_metadata",
    }
)


def _error(
    code: str,
    field: str,
    message: str,
) -> ContractValidationError:
    return ContractValidationError(
        code,
        field,
        message,
    )


def _freeze_field(
    value: Any,
    *,
    field: str,
) -> FrozenCanonicalValue:
    try:
        return freeze_canonical(value)
    except (
        CanonicalizationError,
        TypeError,
        ValueError,
    ) as error:
        raise _error(
            "invalid_input_event_field",
            field,
            (
                "Field is not an approved "
                "canonical value."
            ),
        ) from error


def _exact_mapping(
    value: object,
    expected: frozenset[str],
    *,
    field: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error(
            "invalid_mapping_type",
            field,
            "Value must be a mapping.",
        )

    observed = frozenset(
        value.keys()
    )

    if (
        any(
            not isinstance(key, str)
            for key in observed
        )
        or observed != expected
    ):
        missing = sorted(
            expected - {
                key
                for key in observed
                if isinstance(key, str)
            }
        )
        extra = sorted(
            str(key)
            for key in observed
            if key not in expected
        )

        raise _error(
            "mapping_key_mismatch",
            field,
            (
                f"Missing keys: {missing}; "
                f"unexpected keys: {extra}."
            ),
        )

    return value


@dataclass(frozen=True, slots=True)
class InputEvent:
    """The complete structured input condition."""

    metadata: ContractMetadata
    raw_input: FrozenCanonicalValue
    conversation_context: (
        FrozenCanonicalValue
    )
    identity_context: FrozenCanonicalValue
    session_metadata: FrozenCanonicalValue

    def __post_init__(self) -> None:
        if not isinstance(
            self.metadata,
            ContractMetadata,
        ):
            raise _error(
                "invalid_metadata_type",
                "metadata",
                (
                    "Metadata must be "
                    "ContractMetadata."
                ),
            )

        for field_name in (
            "raw_input",
            "conversation_context",
            "identity_context",
            "session_metadata",
        ):
            value = getattr(
                self,
                field_name,
            )

            if not is_frozen_canonical(
                value
            ):
                raise _error(
                    (
                        "input_event_field_"
                        "not_frozen"
                    ),
                    field_name,
                    (
                        "Stored field must be "
                        "deeply immutable."
                    ),
                )

        if (
            self.metadata.contract_type
            != INPUT_EVENT_CONTRACT_TYPE
        ):
            raise _error(
                "input_event_type_mismatch",
                "contract_type",
                (
                    "InputEvent metadata must "
                    "use contract type InputEvent."
                ),
            )

        if (
            self.metadata.schema_version
            != INPUT_EVENT_SCHEMA_VERSION
        ):
            raise _error(
                (
                    "input_event_schema_"
                    "version_mismatch"
                ),
                "schema_version",
                (
                    "InputEvent must use "
                    "schema version 1.0.0."
                ),
            )

        if (
            self.metadata.authority_status
            != AuthorityStatus.NONE
        ):
            raise _error(
                (
                    "input_event_authority_"
                    "forbidden"
                ),
                "authority_status",
                (
                    "InputEvent cannot carry "
                    "authority."
                ),
            )

        if self.metadata.declared_effects:
            raise _error(
                (
                    "input_event_effects_"
                    "forbidden"
                ),
                "declared_effects",
                (
                    "InputEvent cannot declare "
                    "material side effects."
                ),
            )

        if (
            self.metadata.parent is not None
            and (
                self.metadata
                .parent
                .contract_type
                != INPUT_EVENT_CONTRACT_TYPE
            )
        ):
            raise _error(
                "input_event_parent_type_mismatch",
                "parent",
                (
                    "An InputEvent parent must "
                    "also reference InputEvent."
                ),
            )

        verify_contract_metadata(
            self.metadata,
            self.body(),
        )

    def body(self) -> dict[str, Any]:
        return {
            "raw_input": thaw_canonical(
                self.raw_input
            ),
            "conversation_context": (
                thaw_canonical(
                    self.conversation_context
                )
            ),
            "identity_context": (
                thaw_canonical(
                    self.identity_context
                )
            ),
            "session_metadata": (
                thaw_canonical(
                    self.session_metadata
                )
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        value = canonicalize(
            {
                "metadata": (
                    contract_metadata_to_dict(
                        self.metadata
                    )
                ),
                "body": self.body(),
            }
        )

        if not isinstance(value, dict):
            raise RuntimeError(
                "InputEvent did not serialize "
                "to a mapping."
            )

        return value


def create_input_event(
    *,
    raw_input: Any,
    conversation_context: Any,
    identity_context: Any,
    session_metadata: Any,
    created_at: datetime,
) -> InputEvent:
    """Create one immutable, non-authoritative event."""

    frozen_raw = _freeze_field(
        raw_input,
        field="raw_input",
    )
    frozen_conversation = _freeze_field(
        conversation_context,
        field="conversation_context",
    )
    frozen_identity = _freeze_field(
        identity_context,
        field="identity_context",
    )
    frozen_session = _freeze_field(
        session_metadata,
        field="session_metadata",
    )

    body = {
        "raw_input": thaw_canonical(
            frozen_raw
        ),
        "conversation_context": (
            thaw_canonical(
                frozen_conversation
            )
        ),
        "identity_context": (
            thaw_canonical(
                frozen_identity
            )
        ),
        "session_metadata": (
            thaw_canonical(
                frozen_session
            )
        ),
    }

    metadata = create_contract_metadata(
        schema_version=(
            INPUT_EVENT_SCHEMA_VERSION
        ),
        contract_type=(
            INPUT_EVENT_CONTRACT_TYPE
        ),
        body=body,
        created_at=created_at,
        lifecycle_state=(
            LifecycleState.CANDIDATE
        ),
        authority_status=(
            AuthorityStatus.NONE
        ),
        parent=None,
        declared_effects=(),
    )

    return InputEvent(
        metadata=metadata,
        raw_input=frozen_raw,
        conversation_context=(
            frozen_conversation
        ),
        identity_context=frozen_identity,
        session_metadata=frozen_session,
    )


def input_event_from_dict(
    value: object,
) -> InputEvent:
    """Decode an exact serialized InputEvent."""

    record = _exact_mapping(
        value,
        _TOP_LEVEL_KEYS,
        field="input_event",
    )
    body = _exact_mapping(
        record["body"],
        _BODY_KEYS,
        field="body",
    )

    return InputEvent(
        metadata=contract_metadata_from_dict(
            record["metadata"]
        ),
        raw_input=_freeze_field(
            body["raw_input"],
            field="raw_input",
        ),
        conversation_context=_freeze_field(
            body["conversation_context"],
            field="conversation_context",
        ),
        identity_context=_freeze_field(
            body["identity_context"],
            field="identity_context",
        ),
        session_metadata=_freeze_field(
            body["session_metadata"],
            field="session_metadata",
        ),
    )


def verify_input_event(
    event: InputEvent,
) -> None:
    """Verify the complete InputEvent contract."""

    if not isinstance(event, InputEvent):
        raise _error(
            "invalid_input_event_type",
            "event",
            "Value must be InputEvent.",
        )

    verify_contract_metadata(
        event.metadata,
        event.body(),
    )


__all__ = (
    "INPUT_EVENT_CONTRACT_TYPE",
    "INPUT_EVENT_SCHEMA_VERSION",
    "InputEvent",
    "create_input_event",
    "input_event_from_dict",
    "verify_input_event",
)
