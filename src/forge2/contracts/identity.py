"""Immutable contract identity metadata for Forge 2."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import re
from typing import Any, Final

from .canonical import (
    canonical_sha256,
    canonicalize,
    stable_identifier,
)


SCHEMA_COMPONENT_MAX: Final[int] = (2**31) - 1
CONTRACT_ID_NAMESPACE: Final[str] = "aiweb.contract"

_SCHEMA_VERSION_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)$"
)
_CONTRACT_TYPE_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^[A-Z][A-Za-z0-9]{0,63}$"
)
_SHA256_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^[0-9a-f]{64}$"
)
_CONTRACT_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.contract:sha256:[0-9a-f]{64}$"
)

_EFFECT_TARGET_MAX_LENGTH: Final[int] = 512
_EFFECT_DESCRIPTION_MAX_LENGTH: Final[int] = 1024


class ContractIdentityError(ValueError):
    """Base error with stable code and field identity."""

    def __init__(
        self,
        code: str,
        field: str,
        message: str,
    ) -> None:
        self.code = code
        self.field = field
        self.message = message

        super().__init__(
            f"{code} [{field}]: {message}"
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "field": self.field,
            "message": self.message,
        }


class ContractValidationError(
    ContractIdentityError
):
    """Raised when identity input violates its schema."""


class ContractIntegrityError(
    ContractIdentityError
):
    """Raised when identity does not match content."""


class LifecycleState(StrEnum):
    """Generic immutable contract lifecycle states."""

    DRAFT = "draft"
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class AuthorityStatus(StrEnum):
    """Recorded disposition, not an authority grant."""

    NONE = "none"
    ADVISORY = "advisory"
    REQUESTED = "requested"
    AUTHORIZED = "authorized"
    DENIED = "denied"
    REVOKED = "revoked"


class EffectKind(StrEnum):
    """Declared material-effect categories."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    NETWORK = "network"
    INSTALL = "install"
    APPLY = "apply"
    COMMIT = "commit"
    RELEASE = "release"


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


def _normalized_text(
    value: object,
    *,
    field: str,
    maximum_length: int,
    allow_none: bool = False,
) -> str | None:
    if value is None and allow_none:
        return None

    if not isinstance(value, str):
        raise _validation_error(
            "invalid_text_type",
            field,
            "Value must be text.",
        )

    try:
        normalized = canonicalize(value)
    except Exception as error:
        raise _validation_error(
            "invalid_text_encoding",
            field,
            "Text could not be normalized.",
        ) from error

    if not isinstance(normalized, str):
        raise _validation_error(
            "invalid_text_type",
            field,
            "Value must normalize to text.",
        )

    if not normalized:
        raise _validation_error(
            "empty_text",
            field,
            "Value must not be empty.",
        )

    if normalized != normalized.strip():
        raise _validation_error(
            "surrounding_whitespace",
            field,
            (
                "Leading or trailing whitespace "
                "is forbidden."
            ),
        )

    if len(normalized) > maximum_length:
        raise _validation_error(
            "text_too_long",
            field,
            (
                "Value exceeds "
                f"{maximum_length} characters."
            ),
        )

    return normalized


def _normalized_contract_type(
    value: object,
) -> str:
    normalized = _normalized_text(
        value,
        field="contract_type",
        maximum_length=64,
    )

    assert isinstance(normalized, str)

    if not _CONTRACT_TYPE_PATTERN.fullmatch(
        normalized
    ):
        raise _validation_error(
            "invalid_contract_type",
            "contract_type",
            (
                "Contract type must be "
                "PascalCase ASCII text."
            ),
        )

    return normalized


def _normalized_datetime(
    value: object,
) -> datetime:
    if not isinstance(value, datetime):
        raise _validation_error(
            "invalid_datetime_type",
            "created_at",
            "Created time must be a datetime.",
        )

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise _validation_error(
            "naive_datetime",
            "created_at",
            (
                "Created time must be "
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
        or not _SHA256_PATTERN.fullmatch(value)
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


def _validate_contract_id(
    value: object,
) -> str:
    if (
        not isinstance(value, str)
        or not _CONTRACT_ID_PATTERN.fullmatch(
            value
        )
    ):
        raise _validation_error(
            "invalid_contract_id",
            "contract_id",
            (
                "Contract ID must use the "
                "aiweb.contract SHA-256 form."
            ),
        )

    return value


@dataclass(
    frozen=True,
    slots=True,
    order=True,
)
class SchemaVersion:
    """Strict three-component schema version."""

    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        for field_name in (
            "major",
            "minor",
            "patch",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):
                raise _validation_error(
                    (
                        "invalid_schema_"
                        "component_type"
                    ),
                    field_name,
                    (
                        "Schema components "
                        "must be integers."
                    ),
                )

            if not (
                0
                <= value
                <= SCHEMA_COMPONENT_MAX
            ):
                raise _validation_error(
                    (
                        "schema_component_"
                        "out_of_range"
                    ),
                    field_name,
                    (
                        "Schema component is outside "
                        "the approved range."
                    ),
                )

    @classmethod
    def parse(
        cls,
        value: object,
    ) -> "SchemaVersion":
        if not isinstance(value, str):
            raise _validation_error(
                "invalid_schema_version_type",
                "schema_version",
                (
                    "Schema version must "
                    "be text."
                ),
            )

        match = (
            _SCHEMA_VERSION_PATTERN.fullmatch(
                value
            )
        )

        if match is None:
            raise _validation_error(
                "invalid_schema_version",
                "schema_version",
                (
                    "Schema version must have "
                    "canonical major.minor.patch "
                    "form."
                ),
            )

        return cls(
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
        )

    def __str__(self) -> str:
        return (
            f"{self.major}."
            f"{self.minor}."
            f"{self.patch}"
        )


@dataclass(frozen=True, slots=True)
class DeclaredEffect:
    """Declared effect; declaration grants no permission."""

    kind: EffectKind
    target: str
    description: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.kind,
            EffectKind,
        ):
            raise _validation_error(
                "invalid_effect_kind",
                "kind",
                (
                    "Effect kind must be "
                    "an EffectKind."
                ),
            )

        target = _normalized_text(
            self.target,
            field="target",
            maximum_length=(
                _EFFECT_TARGET_MAX_LENGTH
            ),
        )
        description = _normalized_text(
            self.description,
            field="description",
            maximum_length=(
                _EFFECT_DESCRIPTION_MAX_LENGTH
            ),
            allow_none=True,
        )

        assert isinstance(target, str)

        object.__setattr__(
            self,
            "target",
            target,
        )
        object.__setattr__(
            self,
            "description",
            description,
        )

    def to_dict(
        self,
    ) -> dict[str, str | None]:
        return {
            "kind": self.kind.value,
            "target": self.target,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class ContractReference:
    """Stable reference to a materialized contract."""

    contract_id: str
    content_hash: str
    contract_type: str
    schema_version: SchemaVersion

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "contract_id",
            _validate_contract_id(
                self.contract_id
            ),
        )
        object.__setattr__(
            self,
            "content_hash",
            _validate_sha256(
                self.content_hash,
                field="content_hash",
            ),
        )
        object.__setattr__(
            self,
            "contract_type",
            _normalized_contract_type(
                self.contract_type
            ),
        )

        if not isinstance(
            self.schema_version,
            SchemaVersion,
        ):
            raise _validation_error(
                (
                    "invalid_schema_"
                    "version_object"
                ),
                "schema_version",
                (
                    "Schema version must be "
                    "SchemaVersion."
                ),
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "contract_id": self.contract_id,
            "content_hash": self.content_hash,
            "contract_type": self.contract_type,
            "schema_version": str(
                self.schema_version
            ),
        }


def _effect_sort_key(
    effect: DeclaredEffect,
) -> tuple[str, str, str]:
    return (
        effect.kind.value,
        effect.target,
        effect.description or "",
    )


def _normalize_effects(
    values: Iterable[DeclaredEffect],
) -> tuple[DeclaredEffect, ...]:
    if isinstance(values, (str, bytes)):
        raise _validation_error(
            "invalid_effect_collection",
            "declared_effects",
            (
                "Effects must be an iterable "
                "of DeclaredEffect."
            ),
        )

    try:
        effects = tuple(values)
    except TypeError as error:
        raise _validation_error(
            "invalid_effect_collection",
            "declared_effects",
            "Effects must be iterable.",
        ) from error

    for effect in effects:
        if not isinstance(
            effect,
            DeclaredEffect,
        ):
            raise _validation_error(
                "invalid_effect",
                "declared_effects",
                (
                    "Every effect must be "
                    "DeclaredEffect."
                ),
            )

    ordered = tuple(
        sorted(
            effects,
            key=_effect_sort_key,
        )
    )

    seen: set[tuple[str, str]] = set()

    for effect in ordered:
        identity = (
            effect.kind.value,
            effect.target,
        )

        if identity in seen:
            raise _validation_error(
                "duplicate_declared_effect",
                "declared_effects",
                (
                    "Effect kind and target "
                    "must be unique."
                ),
            )

        seen.add(identity)

    return ordered


def _identity_material(
    *,
    schema_version: SchemaVersion,
    contract_type: str,
    content_hash: str,
    created_at: datetime,
    lifecycle_state: LifecycleState,
    authority_status: AuthorityStatus,
    parent: ContractReference | None,
    declared_effects: tuple[
        DeclaredEffect,
        ...,
    ],
) -> dict[str, Any]:
    return {
        "authority_status": (
            authority_status.value
        ),
        "body_sha256": content_hash,
        "contract_type": contract_type,
        "created_at": created_at,
        "declared_effects": [
            effect.to_dict()
            for effect in declared_effects
        ],
        "lifecycle_state": (
            lifecycle_state.value
        ),
        "parent": (
            parent.to_dict()
            if parent is not None
            else None
        ),
        "schema_version": str(
            schema_version
        ),
    }


def _expected_contract_id(
    *,
    schema_version: SchemaVersion,
    contract_type: str,
    content_hash: str,
    created_at: datetime,
    lifecycle_state: LifecycleState,
    authority_status: AuthorityStatus,
    parent: ContractReference | None,
    declared_effects: tuple[
        DeclaredEffect,
        ...,
    ],
) -> str:
    return stable_identifier(
        CONTRACT_ID_NAMESPACE,
        _identity_material(
            schema_version=schema_version,
            contract_type=contract_type,
            content_hash=content_hash,
            created_at=created_at,
            lifecycle_state=lifecycle_state,
            authority_status=authority_status,
            parent=parent,
            declared_effects=(
                declared_effects
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class ContractMetadata:
    """Immutable identity and lineage metadata."""

    schema_version: SchemaVersion
    contract_type: str
    contract_id: str
    content_hash: str
    created_at: datetime
    lifecycle_state: LifecycleState
    authority_status: AuthorityStatus
    parent: ContractReference | None = None
    declared_effects: tuple[
        DeclaredEffect,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.schema_version,
            SchemaVersion,
        ):
            raise _validation_error(
                (
                    "invalid_schema_"
                    "version_object"
                ),
                "schema_version",
                (
                    "Schema version must be "
                    "SchemaVersion."
                ),
            )

        contract_type = (
            _normalized_contract_type(
                self.contract_type
            )
        )
        contract_id = _validate_contract_id(
            self.contract_id
        )
        content_hash = _validate_sha256(
            self.content_hash,
            field="content_hash",
        )
        created_at = _normalized_datetime(
            self.created_at
        )

        if not isinstance(
            self.lifecycle_state,
            LifecycleState,
        ):
            raise _validation_error(
                "invalid_lifecycle_state",
                "lifecycle_state",
                (
                    "Lifecycle state must be "
                    "LifecycleState."
                ),
            )

        if not isinstance(
            self.authority_status,
            AuthorityStatus,
        ):
            raise _validation_error(
                "invalid_authority_status",
                "authority_status",
                (
                    "Authority status must be "
                    "AuthorityStatus."
                ),
            )

        if (
            self.parent is not None
            and not isinstance(
                self.parent,
                ContractReference,
            )
        ):
            raise _validation_error(
                "invalid_parent_reference",
                "parent",
                (
                    "Parent must be "
                    "ContractReference or None."
                ),
            )

        if not isinstance(
            self.declared_effects,
            tuple,
        ):
            raise _validation_error(
                "effects_not_immutable",
                "declared_effects",
                (
                    "Stored declared effects "
                    "must be a tuple."
                ),
            )

        normalized_effects = (
            _normalize_effects(
                self.declared_effects
            )
        )

        if (
            normalized_effects
            != self.declared_effects
        ):
            raise _validation_error(
                "effects_not_canonical_order",
                "declared_effects",
                (
                    "Stored effects must use "
                    "canonical order."
                ),
            )

        expected_id = _expected_contract_id(
            schema_version=(
                self.schema_version
            ),
            contract_type=contract_type,
            content_hash=content_hash,
            created_at=created_at,
            lifecycle_state=(
                self.lifecycle_state
            ),
            authority_status=(
                self.authority_status
            ),
            parent=self.parent,
            declared_effects=(
                normalized_effects
            ),
        )

        if contract_id != expected_id:
            raise ContractIntegrityError(
                "contract_id_mismatch",
                "contract_id",
                (
                    "Contract ID does not match "
                    "identity material."
                ),
            )

        object.__setattr__(
            self,
            "contract_type",
            contract_type,
        )
        object.__setattr__(
            self,
            "contract_id",
            contract_id,
        )
        object.__setattr__(
            self,
            "content_hash",
            content_hash,
        )
        object.__setattr__(
            self,
            "created_at",
            created_at,
        )
        object.__setattr__(
            self,
            "declared_effects",
            normalized_effects,
        )

    def to_reference(
        self,
    ) -> ContractReference:
        return ContractReference(
            contract_id=self.contract_id,
            content_hash=self.content_hash,
            contract_type=(
                self.contract_type
            ),
            schema_version=(
                self.schema_version
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "schema_version": str(
                self.schema_version
            ),
            "contract_type": (
                self.contract_type
            ),
            "contract_id": self.contract_id,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
            "lifecycle_state": (
                self.lifecycle_state.value
            ),
            "authority_status": (
                self.authority_status.value
            ),
            "parent": (
                self.parent.to_dict()
                if self.parent is not None
                else None
            ),
            "declared_effects": [
                effect.to_dict()
                for effect in (
                    self.declared_effects
                )
            ],
        }

    def verify_body(
        self,
        body: Any,
    ) -> None:
        observed_hash = canonical_sha256(
            body
        )

        if observed_hash != self.content_hash:
            raise ContractIntegrityError(
                "content_hash_mismatch",
                "content_hash",
                (
                    "Body does not match the "
                    "recorded content hash."
                ),
            )


def create_contract_metadata(
    *,
    schema_version: SchemaVersion | str,
    contract_type: str,
    body: Any,
    created_at: datetime,
    lifecycle_state: LifecycleState = (
        LifecycleState.CANDIDATE
    ),
    authority_status: AuthorityStatus = (
        AuthorityStatus.NONE
    ),
    parent: ContractReference | None = None,
    declared_effects: Iterable[
        DeclaredEffect
    ] = (),
) -> ContractMetadata:
    """Create validated immutable metadata for a body."""

    version = (
        schema_version
        if isinstance(
            schema_version,
            SchemaVersion,
        )
        else SchemaVersion.parse(
            schema_version
        )
    )
    normalized_type = (
        _normalized_contract_type(
            contract_type
        )
    )
    normalized_time = (
        _normalized_datetime(
            created_at
        )
    )

    if not isinstance(
        lifecycle_state,
        LifecycleState,
    ):
        raise _validation_error(
            "invalid_lifecycle_state",
            "lifecycle_state",
            (
                "Lifecycle state must be "
                "LifecycleState."
            ),
        )

    if not isinstance(
        authority_status,
        AuthorityStatus,
    ):
        raise _validation_error(
            "invalid_authority_status",
            "authority_status",
            (
                "Authority status must be "
                "AuthorityStatus."
            ),
        )

    if (
        parent is not None
        and not isinstance(
            parent,
            ContractReference,
        )
    ):
        raise _validation_error(
            "invalid_parent_reference",
            "parent",
            (
                "Parent must be "
                "ContractReference or None."
            ),
        )

    effects = _normalize_effects(
        declared_effects
    )
    content_hash = canonical_sha256(
        body
    )
    contract_id = _expected_contract_id(
        schema_version=version,
        contract_type=normalized_type,
        content_hash=content_hash,
        created_at=normalized_time,
        lifecycle_state=lifecycle_state,
        authority_status=authority_status,
        parent=parent,
        declared_effects=effects,
    )

    metadata = ContractMetadata(
        schema_version=version,
        contract_type=normalized_type,
        contract_id=contract_id,
        content_hash=content_hash,
        created_at=normalized_time,
        lifecycle_state=lifecycle_state,
        authority_status=authority_status,
        parent=parent,
        declared_effects=effects,
    )
    metadata.verify_body(body)
    return metadata


def verify_contract_metadata(
    metadata: ContractMetadata,
    body: Any,
) -> None:
    """Verify metadata structure, identity, and body."""

    if not isinstance(
        metadata,
        ContractMetadata,
    ):
        raise _validation_error(
            "invalid_metadata_type",
            "metadata",
            (
                "Metadata must be "
                "ContractMetadata."
            ),
        )

    metadata.verify_body(body)


__all__ = (
    "AuthorityStatus",
    "CONTRACT_ID_NAMESPACE",
    "ContractIdentityError",
    "ContractIntegrityError",
    "ContractMetadata",
    "ContractReference",
    "ContractValidationError",
    "DeclaredEffect",
    "EffectKind",
    "LifecycleState",
    "SCHEMA_COMPONENT_MAX",
    "SchemaVersion",
    "create_contract_metadata",
    "verify_contract_metadata",
)
