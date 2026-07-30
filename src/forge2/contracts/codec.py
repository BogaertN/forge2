"""Strict decoding helpers for Forge 2 contracts."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .canonical import canonicalize
from .identity import (
    AuthorityStatus,
    ContractMetadata,
    ContractReference,
    ContractValidationError,
    DeclaredEffect,
    EffectKind,
    LifecycleState,
    SchemaVersion,
)


_METADATA_KEYS = frozenset(
    {
        "schema_version",
        "contract_type",
        "contract_id",
        "content_hash",
        "created_at",
        "lifecycle_state",
        "authority_status",
        "parent",
        "declared_effects",
    }
)
_REFERENCE_KEYS = frozenset(
    {
        "contract_id",
        "content_hash",
        "contract_type",
        "schema_version",
    }
)
_EFFECT_KEYS = frozenset(
    {
        "kind",
        "target",
        "description",
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


def _mapping(
    value: object,
    *,
    field: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error(
            "invalid_mapping_type",
            field,
            "Value must be a mapping.",
        )

    for key in value:
        if not isinstance(key, str):
            raise _error(
                "invalid_mapping_key",
                field,
                "All mapping keys must be text.",
            )

    return value


def _exact_keys(
    value: Mapping[str, Any],
    expected: frozenset[str],
    *,
    field: str,
) -> None:
    observed = frozenset(value.keys())

    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)

        raise _error(
            "mapping_key_mismatch",
            field,
            (
                f"Missing keys: {missing}; "
                f"unexpected keys: {extra}."
            ),
        )


def _text(
    value: object,
    *,
    field: str,
) -> str:
    if not isinstance(value, str):
        raise _error(
            "invalid_text_type",
            field,
            "Value must be text.",
        )

    return value


def _datetime(
    value: object,
    *,
    field: str,
) -> datetime:
    text = _text(
        value,
        field=field,
    )

    if not text.endswith("Z"):
        raise _error(
            "invalid_canonical_datetime",
            field,
            (
                "Datetime must use canonical "
                "UTC Z form."
            ),
        )

    try:
        parsed = datetime.fromisoformat(
            text[:-1] + "+00:00"
        )
    except ValueError as error:
        raise _error(
            "invalid_canonical_datetime",
            field,
            "Datetime could not be parsed.",
        ) from error

    return parsed


def contract_reference_from_dict(
    value: object,
) -> ContractReference:
    record = _mapping(
        value,
        field="parent",
    )
    _exact_keys(
        record,
        _REFERENCE_KEYS,
        field="parent",
    )

    return ContractReference(
        contract_id=_text(
            record["contract_id"],
            field="parent.contract_id",
        ),
        content_hash=_text(
            record["content_hash"],
            field="parent.content_hash",
        ),
        contract_type=_text(
            record["contract_type"],
            field="parent.contract_type",
        ),
        schema_version=SchemaVersion.parse(
            record["schema_version"]
        ),
    )


def declared_effect_from_dict(
    value: object,
    *,
    index: int,
) -> DeclaredEffect:
    field = f"declared_effects[{index}]"
    record = _mapping(
        value,
        field=field,
    )
    _exact_keys(
        record,
        _EFFECT_KEYS,
        field=field,
    )

    try:
        kind = EffectKind(
            record["kind"]
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise _error(
            "invalid_effect_kind",
            f"{field}.kind",
            "Effect kind is unknown.",
        ) from error

    description = record["description"]

    if (
        description is not None
        and not isinstance(description, str)
    ):
        raise _error(
            "invalid_text_type",
            f"{field}.description",
            (
                "Description must be text "
                "or null."
            ),
        )

    return DeclaredEffect(
        kind=kind,
        target=_text(
            record["target"],
            field=f"{field}.target",
        ),
        description=description,
    )


def contract_metadata_from_dict(
    value: object,
) -> ContractMetadata:
    """Decode strict canonical metadata."""

    record = _mapping(
        value,
        field="metadata",
    )
    _exact_keys(
        record,
        _METADATA_KEYS,
        field="metadata",
    )

    parent_value = record["parent"]

    parent = (
        None
        if parent_value is None
        else contract_reference_from_dict(
            parent_value
        )
    )

    effects_value = record[
        "declared_effects"
    ]

    if not isinstance(
        effects_value,
        (list, tuple),
    ):
        raise _error(
            "invalid_effect_collection",
            "declared_effects",
            (
                "Declared effects must be "
                "a sequence."
            ),
        )

    effects = tuple(
        declared_effect_from_dict(
            item,
            index=index,
        )
        for index, item
        in enumerate(effects_value)
    )

    try:
        lifecycle = LifecycleState(
            record["lifecycle_state"]
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise _error(
            "invalid_lifecycle_state",
            "lifecycle_state",
            "Lifecycle state is unknown.",
        ) from error

    try:
        authority = AuthorityStatus(
            record["authority_status"]
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise _error(
            "invalid_authority_status",
            "authority_status",
            "Authority status is unknown.",
        ) from error

    return ContractMetadata(
        schema_version=SchemaVersion.parse(
            record["schema_version"]
        ),
        contract_type=_text(
            record["contract_type"],
            field="contract_type",
        ),
        contract_id=_text(
            record["contract_id"],
            field="contract_id",
        ),
        content_hash=_text(
            record["content_hash"],
            field="content_hash",
        ),
        created_at=_datetime(
            record["created_at"],
            field="created_at",
        ),
        lifecycle_state=lifecycle,
        authority_status=authority,
        parent=parent,
        declared_effects=effects,
    )


def contract_metadata_to_dict(
    metadata: ContractMetadata,
) -> dict[str, Any]:
    """Return strict canonical metadata data."""

    if not isinstance(
        metadata,
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

    value = canonicalize(
        metadata.to_dict()
    )

    if not isinstance(value, dict):
        raise RuntimeError(
            "Canonical metadata did not "
            "produce a mapping."
        )

    return value


__all__ = (
    "contract_metadata_from_dict",
    "contract_metadata_to_dict",
    "contract_reference_from_dict",
    "declared_effect_from_dict",
)
