"""Append-only successor laws for Forge 2 contracts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import re
from typing import Any, Final

from .canonical import (
    canonical_sha256,
    stable_identifier,
)
from .identity import (
    AuthorityStatus,
    ContractIntegrityError,
    ContractMetadata,
    ContractReference,
    ContractValidationError,
    DeclaredEffect,
    LifecycleState,
    SchemaVersion,
    create_contract_metadata,
    verify_contract_metadata,
)


SUCCESSOR_ID_NAMESPACE: Final[str] = (
    "aiweb.successor"
)

_UNSET: Final[object] = object()

_SHA256_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^[0-9a-f]{64}$"
)
_SUCCESSOR_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.successor:sha256:"
    r"[0-9a-f]{64}$"
)
_RULE_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^successor\.[a-z0-9_]+\.v1$"
)

_CHANGED_FIELD_ORDER: Final[
    tuple[str, ...]
] = (
    "body",
    "schema_version",
    "lifecycle_state",
    "authority_status",
    "declared_effects",
)

_EDITABLE_LIFECYCLE_STATES: Final[
    frozenset[LifecycleState]
] = frozenset(
    {
        LifecycleState.DRAFT,
        LifecycleState.CANDIDATE,
    }
)

_LIFECYCLE_TRANSITIONS: Final[
    dict[
        LifecycleState,
        frozenset[LifecycleState],
    ]
] = {
    LifecycleState.DRAFT: frozenset(
        {
            LifecycleState.CANDIDATE,
            LifecycleState.REJECTED,
            LifecycleState.ARCHIVED,
        }
    ),
    LifecycleState.CANDIDATE: frozenset(
        {
            LifecycleState.ACCEPTED,
            LifecycleState.REJECTED,
            LifecycleState.ARCHIVED,
        }
    ),
    LifecycleState.ACCEPTED: frozenset(
        {
            LifecycleState.SUPERSEDED,
            LifecycleState.ARCHIVED,
        }
    ),
    LifecycleState.SUPERSEDED: frozenset(
        {
            LifecycleState.ARCHIVED,
        }
    ),
    LifecycleState.REJECTED: frozenset(
        {
            LifecycleState.ARCHIVED,
        }
    ),
    LifecycleState.ARCHIVED: frozenset(),
}

_AUTHORITY_TRANSITIONS: Final[
    dict[
        AuthorityStatus,
        frozenset[AuthorityStatus],
    ]
] = {
    AuthorityStatus.NONE: frozenset(
        {
            AuthorityStatus.ADVISORY,
            AuthorityStatus.REQUESTED,
        }
    ),
    AuthorityStatus.ADVISORY: frozenset(
        {
            AuthorityStatus.NONE,
            AuthorityStatus.REQUESTED,
        }
    ),
    AuthorityStatus.REQUESTED: frozenset(
        {
            AuthorityStatus.AUTHORIZED,
            AuthorityStatus.DENIED,
            AuthorityStatus.REVOKED,
        }
    ),
    AuthorityStatus.AUTHORIZED: frozenset(
        {
            AuthorityStatus.REVOKED,
        }
    ),
    AuthorityStatus.DENIED: frozenset(
        {
            AuthorityStatus.REQUESTED,
        }
    ),
    AuthorityStatus.REVOKED: frozenset(
        {
            AuthorityStatus.REQUESTED,
        }
    ),
}


class SuccessorKind(StrEnum):
    """The single primary law applied to a successor."""

    BODY_REVISION = "body_revision"
    SCHEMA_REVISION = "schema_revision"
    LIFECYCLE_TRANSITION = (
        "lifecycle_transition"
    )
    AUTHORITY_TRANSITION = (
        "authority_transition"
    )
    EFFECTS_REVISION = "effects_revision"


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


def _normalize_time(
    value: object,
    *,
    field: str,
) -> datetime:
    if not isinstance(value, datetime):
        raise _validation_error(
            "invalid_datetime_type",
            field,
            "Value must be a datetime.",
        )

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise _validation_error(
            "naive_datetime",
            field,
            (
                "Value must be "
                "timezone-aware."
            ),
        )

    return value.astimezone(timezone.utc)


def _validate_sha256(
    value: object,
    *,
    field: str,
) -> str:
    if (
        not isinstance(value, str)
        or not _SHA256_PATTERN.fullmatch(
            value
        )
    ):
        raise _validation_error(
            "invalid_sha256",
            field,
            (
                "Value must be 64 lowercase "
                "hexadecimal characters."
            ),
        )

    return value


def _validate_rule_id(
    value: object,
) -> str:
    if (
        not isinstance(value, str)
        or not _RULE_ID_PATTERN.fullmatch(
            value
        )
    ):
        raise _validation_error(
            "invalid_successor_rule_id",
            "rule_id",
            "Successor rule ID is invalid.",
        )

    return value


def _validate_changed_fields(
    value: object,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise _validation_error(
            "changed_fields_not_immutable",
            "changed_fields",
            (
                "Changed fields must be "
                "stored as a tuple."
            ),
        )

    if not value:
        raise _validation_error(
            "empty_changed_fields",
            "changed_fields",
            (
                "At least one changed field "
                "is required."
            ),
        )

    if (
        len(set(value)) != len(value)
        or any(
            field
            not in _CHANGED_FIELD_ORDER
            for field in value
        )
    ):
        raise _validation_error(
            "invalid_changed_fields",
            "changed_fields",
            (
                "Changed fields contain an "
                "invalid or duplicate value."
            ),
        )

    expected = tuple(
        field
        for field in _CHANGED_FIELD_ORDER
        if field in value
    )

    if value != expected:
        raise _validation_error(
            "changed_fields_not_canonical",
            "changed_fields",
            (
                "Changed fields must use "
                "canonical order."
            ),
        )

    return value


def _state_material(
    metadata: ContractMetadata,
) -> dict[str, Any]:
    return {
        "contract_id": metadata.contract_id,
        "content_hash": metadata.content_hash,
        "schema_version": str(
            metadata.schema_version
        ),
        "lifecycle_state": (
            metadata.lifecycle_state.value
        ),
        "authority_status": (
            metadata.authority_status.value
        ),
        "declared_effects": [
            effect.to_dict()
            for effect in (
                metadata.declared_effects
            )
        ],
    }


def _state_hash(
    metadata: ContractMetadata,
) -> str:
    return canonical_sha256(
        _state_material(metadata)
    )


def _receipt_material(
    *,
    predecessor: ContractReference,
    successor: ContractReference,
    kind: SuccessorKind,
    rule_id: str,
    changed_fields: tuple[str, ...],
    observed_at: datetime,
    predecessor_state_hash: str,
    successor_state_hash: str,
) -> dict[str, Any]:
    return {
        "changed_fields": list(
            changed_fields
        ),
        "kind": kind.value,
        "observed_at": observed_at,
        "predecessor": (
            predecessor.to_dict()
        ),
        "predecessor_state_hash": (
            predecessor_state_hash
        ),
        "rule_id": rule_id,
        "successor": successor.to_dict(),
        "successor_state_hash": (
            successor_state_hash
        ),
    }


def _expected_receipt_id(
    *,
    predecessor: ContractReference,
    successor: ContractReference,
    kind: SuccessorKind,
    rule_id: str,
    changed_fields: tuple[str, ...],
    observed_at: datetime,
    predecessor_state_hash: str,
    successor_state_hash: str,
) -> str:
    return stable_identifier(
        SUCCESSOR_ID_NAMESPACE,
        _receipt_material(
            predecessor=predecessor,
            successor=successor,
            kind=kind,
            rule_id=rule_id,
            changed_fields=changed_fields,
            observed_at=observed_at,
            predecessor_state_hash=(
                predecessor_state_hash
            ),
            successor_state_hash=(
                successor_state_hash
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class SuccessorReceipt:
    """Deterministic proof of one successor law."""

    receipt_id: str
    predecessor: ContractReference
    successor: ContractReference
    kind: SuccessorKind
    rule_id: str
    changed_fields: tuple[str, ...]
    observed_at: datetime
    predecessor_state_hash: str
    successor_state_hash: str

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.receipt_id,
                str,
            )
            or not _SUCCESSOR_ID_PATTERN.fullmatch(
                self.receipt_id
            )
        ):
            raise _validation_error(
                "invalid_successor_receipt_id",
                "receipt_id",
                (
                    "Receipt ID must use the "
                    "aiweb.successor SHA-256 form."
                ),
            )

        if not isinstance(
            self.predecessor,
            ContractReference,
        ):
            raise _validation_error(
                "invalid_predecessor_reference",
                "predecessor",
                (
                    "Predecessor must be "
                    "ContractReference."
                ),
            )

        if not isinstance(
            self.successor,
            ContractReference,
        ):
            raise _validation_error(
                "invalid_successor_reference",
                "successor",
                (
                    "Successor must be "
                    "ContractReference."
                ),
            )

        if (
            self.predecessor.contract_id
            == self.successor.contract_id
        ):
            raise _validation_error(
                "identical_successor_reference",
                "successor",
                (
                    "Successor must have a "
                    "different contract ID."
                ),
            )

        if not isinstance(
            self.kind,
            SuccessorKind,
        ):
            raise _validation_error(
                "invalid_successor_kind",
                "kind",
                (
                    "Kind must be "
                    "SuccessorKind."
                ),
            )

        rule_id = _validate_rule_id(
            self.rule_id
        )
        changed_fields = (
            _validate_changed_fields(
                self.changed_fields
            )
        )
        observed_at = _normalize_time(
            self.observed_at,
            field="observed_at",
        )
        predecessor_state_hash = (
            _validate_sha256(
                self.predecessor_state_hash,
                field=(
                    "predecessor_state_hash"
                ),
            )
        )
        successor_state_hash = (
            _validate_sha256(
                self.successor_state_hash,
                field="successor_state_hash",
            )
        )

        expected_id = _expected_receipt_id(
            predecessor=self.predecessor,
            successor=self.successor,
            kind=self.kind,
            rule_id=rule_id,
            changed_fields=changed_fields,
            observed_at=observed_at,
            predecessor_state_hash=(
                predecessor_state_hash
            ),
            successor_state_hash=(
                successor_state_hash
            ),
        )

        if self.receipt_id != expected_id:
            raise ContractIntegrityError(
                "successor_receipt_id_mismatch",
                "receipt_id",
                (
                    "Receipt ID does not match "
                    "its material."
                ),
            )

        object.__setattr__(
            self,
            "rule_id",
            rule_id,
        )
        object.__setattr__(
            self,
            "changed_fields",
            changed_fields,
        )
        object.__setattr__(
            self,
            "observed_at",
            observed_at,
        )
        object.__setattr__(
            self,
            "predecessor_state_hash",
            predecessor_state_hash,
        )
        object.__setattr__(
            self,
            "successor_state_hash",
            successor_state_hash,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "predecessor": (
                self.predecessor.to_dict()
            ),
            "successor": (
                self.successor.to_dict()
            ),
            "kind": self.kind.value,
            "rule_id": self.rule_id,
            "changed_fields": list(
                self.changed_fields
            ),
            "observed_at": (
                self.observed_at
            ),
            "predecessor_state_hash": (
                self.predecessor_state_hash
            ),
            "successor_state_hash": (
                self.successor_state_hash
            ),
        }


@dataclass(frozen=True, slots=True)
class SuccessorTransition:
    """A successor snapshot and its proof receipt."""

    metadata: ContractMetadata
    receipt: SuccessorReceipt

    def __post_init__(self) -> None:
        if not isinstance(
            self.metadata,
            ContractMetadata,
        ):
            raise _validation_error(
                "invalid_successor_metadata",
                "metadata",
                (
                    "Metadata must be "
                    "ContractMetadata."
                ),
            )

        if not isinstance(
            self.receipt,
            SuccessorReceipt,
        ):
            raise _validation_error(
                "invalid_successor_receipt",
                "receipt",
                (
                    "Receipt must be "
                    "SuccessorReceipt."
                ),
            )

        if (
            self.receipt.successor
            != self.metadata.to_reference()
        ):
            raise ContractIntegrityError(
                (
                    "successor_receipt_"
                    "reference_mismatch"
                ),
                "receipt",
                (
                    "Receipt successor does not "
                    "match successor metadata."
                ),
            )


def _schema_step(
    predecessor: SchemaVersion,
    successor: SchemaVersion,
) -> str:
    if (
        successor.major == predecessor.major
        and successor.minor
        == predecessor.minor
        and successor.patch
        == predecessor.patch + 1
    ):
        return "patch"

    if (
        successor.major == predecessor.major
        and successor.minor
        == predecessor.minor + 1
        and successor.patch == 0
    ):
        return "minor"

    if (
        successor.major
        == predecessor.major + 1
        and successor.minor == 0
        and successor.patch == 0
    ):
        return "major"

    raise _validation_error(
        "invalid_schema_successor_step",
        "schema_version",
        (
            "Schema successor must be the next "
            "patch, minor, or major version."
        ),
    )


def _classify_transition(
    predecessor: ContractMetadata,
    successor: ContractMetadata,
) -> tuple[
    SuccessorKind,
    str,
    tuple[str, ...],
]:
    body_changed = (
        predecessor.content_hash
        != successor.content_hash
    )
    schema_changed = (
        predecessor.schema_version
        != successor.schema_version
    )
    lifecycle_changed = (
        predecessor.lifecycle_state
        != successor.lifecycle_state
    )
    authority_changed = (
        predecessor.authority_status
        != successor.authority_status
    )
    effects_changed = (
        predecessor.declared_effects
        != successor.declared_effects
    )

    changed = tuple(
        field
        for field, status in (
            ("body", body_changed),
            (
                "schema_version",
                schema_changed,
            ),
            (
                "lifecycle_state",
                lifecycle_changed,
            ),
            (
                "authority_status",
                authority_changed,
            ),
            (
                "declared_effects",
                effects_changed,
            ),
        )
        if status
    )

    if not changed:
        raise _validation_error(
            "no_successor_change",
            "successor",
            (
                "A successor must change at "
                "least one material dimension."
            ),
        )

    if schema_changed:
        if (
            lifecycle_changed
            or authority_changed
            or effects_changed
        ):
            raise _validation_error(
                "mixed_successor_dimensions",
                "successor",
                (
                    "Schema revision may only "
                    "combine with a body change."
                ),
            )

        if (
            predecessor.lifecycle_state
            not in _EDITABLE_LIFECYCLE_STATES
        ):
            raise _validation_error(
                (
                    "schema_revision_"
                    "state_forbidden"
                ),
                "lifecycle_state",
                (
                    "Schema revision is only "
                    "allowed for draft or "
                    "candidate contracts."
                ),
            )

        step = _schema_step(
            predecessor.schema_version,
            successor.schema_version,
        )

        return (
            SuccessorKind.SCHEMA_REVISION,
            f"successor.schema_{step}.v1",
            changed,
        )

    if body_changed:
        if (
            lifecycle_changed
            or authority_changed
            or effects_changed
        ):
            raise _validation_error(
                "mixed_successor_dimensions",
                "successor",
                (
                    "Body revision cannot be "
                    "combined with another "
                    "metadata transition."
                ),
            )

        if (
            predecessor.lifecycle_state
            not in _EDITABLE_LIFECYCLE_STATES
        ):
            raise _validation_error(
                (
                    "body_revision_"
                    "state_forbidden"
                ),
                "lifecycle_state",
                (
                    "Body revision is only "
                    "allowed for draft or "
                    "candidate contracts."
                ),
            )

        return (
            SuccessorKind.BODY_REVISION,
            "successor.body_revision.v1",
            changed,
        )

    if lifecycle_changed:
        if authority_changed or effects_changed:
            raise _validation_error(
                "mixed_successor_dimensions",
                "successor",
                (
                    "Lifecycle transition must "
                    "be isolated."
                ),
            )

        allowed = _LIFECYCLE_TRANSITIONS[
            predecessor.lifecycle_state
        ]

        if (
            successor.lifecycle_state
            not in allowed
        ):
            raise _validation_error(
                (
                    "invalid_lifecycle_"
                    "transition"
                ),
                "lifecycle_state",
                (
                    "Lifecycle transition is "
                    "not allowed."
                ),
            )

        return (
            (
                SuccessorKind
                .LIFECYCLE_TRANSITION
            ),
            (
                "successor.lifecycle_"
                f"{predecessor.lifecycle_state.value}_"
                f"to_{successor.lifecycle_state.value}.v1"
            ),
            changed,
        )

    if authority_changed:
        if effects_changed:
            raise _validation_error(
                "mixed_successor_dimensions",
                "successor",
                (
                    "Authority transition must "
                    "be isolated."
                ),
            )

        allowed = _AUTHORITY_TRANSITIONS[
            predecessor.authority_status
        ]

        if (
            successor.authority_status
            not in allowed
        ):
            raise _validation_error(
                (
                    "invalid_authority_"
                    "transition"
                ),
                "authority_status",
                (
                    "Authority disposition "
                    "transition is not allowed."
                ),
            )

        return (
            (
                SuccessorKind
                .AUTHORITY_TRANSITION
            ),
            (
                "successor.authority_"
                f"{predecessor.authority_status.value}_"
                f"to_{successor.authority_status.value}.v1"
            ),
            changed,
        )

    if effects_changed:
        if (
            predecessor.lifecycle_state
            not in _EDITABLE_LIFECYCLE_STATES
        ):
            raise _validation_error(
                (
                    "effects_revision_"
                    "state_forbidden"
                ),
                "lifecycle_state",
                (
                    "Effect revision is only "
                    "allowed for draft or "
                    "candidate contracts."
                ),
            )

        return (
            SuccessorKind.EFFECTS_REVISION,
            "successor.effects_revision.v1",
            changed,
        )

    raise _validation_error(
        "unclassified_successor",
        "successor",
        (
            "Successor could not be "
            "classified."
        ),
    )


def _verify_structural_laws(
    predecessor: ContractMetadata,
    successor: ContractMetadata,
) -> None:
    if (
        successor.contract_type
        != predecessor.contract_type
    ):
        raise _validation_error(
            "contract_type_changed",
            "contract_type",
            (
                "Successor contract type "
                "must not change."
            ),
        )

    if (
        successor.parent
        != predecessor.to_reference()
    ):
        raise ContractIntegrityError(
            "successor_parent_mismatch",
            "parent",
            (
                "Successor parent must exactly "
                "reference its predecessor."
            ),
        )

    if (
        successor.created_at
        <= predecessor.created_at
    ):
        raise _validation_error(
            "successor_time_not_increasing",
            "created_at",
            (
                "Successor creation time must "
                "be later than predecessor time."
            ),
        )


def create_successor(
    *,
    predecessor: ContractMetadata,
    predecessor_body: Any,
    successor_body: Any,
    created_at: datetime,
    schema_version: (
        SchemaVersion | str | None
    ) = None,
    lifecycle_state: (
        LifecycleState | None
    ) = None,
    authority_status: (
        AuthorityStatus | None
    ) = None,
    declared_effects: (
        Iterable[DeclaredEffect] | object
    ) = _UNSET,
) -> SuccessorTransition:
    """Create one validated append-only successor."""

    if not isinstance(
        predecessor,
        ContractMetadata,
    ):
        raise _validation_error(
            "invalid_predecessor_metadata",
            "predecessor",
            (
                "Predecessor must be "
                "ContractMetadata."
            ),
        )

    verify_contract_metadata(
        predecessor,
        predecessor_body,
    )

    target_version = (
        predecessor.schema_version
        if schema_version is None
        else (
            schema_version
            if isinstance(
                schema_version,
                SchemaVersion,
            )
            else SchemaVersion.parse(
                schema_version
            )
        )
    )
    target_lifecycle = (
        predecessor.lifecycle_state
        if lifecycle_state is None
        else lifecycle_state
    )
    target_authority = (
        predecessor.authority_status
        if authority_status is None
        else authority_status
    )
    target_effects = (
        predecessor.declared_effects
        if declared_effects is _UNSET
        else declared_effects
    )

    successor = create_contract_metadata(
        schema_version=target_version,
        contract_type=(
            predecessor.contract_type
        ),
        body=successor_body,
        created_at=created_at,
        lifecycle_state=target_lifecycle,
        authority_status=target_authority,
        parent=predecessor.to_reference(),
        declared_effects=target_effects,
    )

    _verify_structural_laws(
        predecessor,
        successor,
    )

    kind, rule_id, changed_fields = (
        _classify_transition(
            predecessor,
            successor,
        )
    )

    predecessor_state_hash = _state_hash(
        predecessor
    )
    successor_state_hash = _state_hash(
        successor
    )
    observed_at = successor.created_at

    receipt_id = _expected_receipt_id(
        predecessor=(
            predecessor.to_reference()
        ),
        successor=successor.to_reference(),
        kind=kind,
        rule_id=rule_id,
        changed_fields=changed_fields,
        observed_at=observed_at,
        predecessor_state_hash=(
            predecessor_state_hash
        ),
        successor_state_hash=(
            successor_state_hash
        ),
    )

    receipt = SuccessorReceipt(
        receipt_id=receipt_id,
        predecessor=(
            predecessor.to_reference()
        ),
        successor=successor.to_reference(),
        kind=kind,
        rule_id=rule_id,
        changed_fields=changed_fields,
        observed_at=observed_at,
        predecessor_state_hash=(
            predecessor_state_hash
        ),
        successor_state_hash=(
            successor_state_hash
        ),
    )

    transition = SuccessorTransition(
        metadata=successor,
        receipt=receipt,
    )

    verify_successor(
        predecessor=predecessor,
        predecessor_body=predecessor_body,
        successor=successor,
        successor_body=successor_body,
        receipt=receipt,
    )

    return transition


def verify_successor(
    *,
    predecessor: ContractMetadata,
    predecessor_body: Any,
    successor: ContractMetadata,
    successor_body: Any,
    receipt: SuccessorReceipt,
) -> None:
    """Verify structure, bodies, law, and receipt."""

    if not isinstance(
        predecessor,
        ContractMetadata,
    ):
        raise _validation_error(
            "invalid_predecessor_metadata",
            "predecessor",
            (
                "Predecessor must be "
                "ContractMetadata."
            ),
        )

    if not isinstance(
        successor,
        ContractMetadata,
    ):
        raise _validation_error(
            "invalid_successor_metadata",
            "successor",
            (
                "Successor must be "
                "ContractMetadata."
            ),
        )

    if not isinstance(
        receipt,
        SuccessorReceipt,
    ):
        raise _validation_error(
            "invalid_successor_receipt",
            "receipt",
            (
                "Receipt must be "
                "SuccessorReceipt."
            ),
        )

    verify_contract_metadata(
        predecessor,
        predecessor_body,
    )
    verify_contract_metadata(
        successor,
        successor_body,
    )

    _verify_structural_laws(
        predecessor,
        successor,
    )

    kind, rule_id, changed_fields = (
        _classify_transition(
            predecessor,
            successor,
        )
    )

    expected_predecessor_hash = (
        _state_hash(predecessor)
    )
    expected_successor_hash = (
        _state_hash(successor)
    )

    expected_receipt_id = (
        _expected_receipt_id(
            predecessor=(
                predecessor.to_reference()
            ),
            successor=(
                successor.to_reference()
            ),
            kind=kind,
            rule_id=rule_id,
            changed_fields=changed_fields,
            observed_at=(
                successor.created_at
            ),
            predecessor_state_hash=(
                expected_predecessor_hash
            ),
            successor_state_hash=(
                expected_successor_hash
            ),
        )
    )

    expected_values = (
        predecessor.to_reference(),
        successor.to_reference(),
        kind,
        rule_id,
        changed_fields,
        successor.created_at,
        expected_predecessor_hash,
        expected_successor_hash,
        expected_receipt_id,
    )
    observed_values = (
        receipt.predecessor,
        receipt.successor,
        receipt.kind,
        receipt.rule_id,
        receipt.changed_fields,
        receipt.observed_at,
        receipt.predecessor_state_hash,
        receipt.successor_state_hash,
        receipt.receipt_id,
    )

    if observed_values != expected_values:
        raise ContractIntegrityError(
            "successor_receipt_mismatch",
            "receipt",
            (
                "Successor receipt does not "
                "match the verified transition."
            ),
        )


__all__ = (
    "SUCCESSOR_ID_NAMESPACE",
    "SuccessorKind",
    "SuccessorReceipt",
    "SuccessorTransition",
    "create_successor",
    "verify_successor",
)
