"""Strict canonical serialization for Forge 2 contracts.

This module defines a deliberately narrow JSON-compatible
profile. Unsupported or ambiguous values are rejected
instead of being converted implicitly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Any, Final, TypeAlias
import unicodedata


MAX_SAFE_INTEGER: Final[int] = (2**53) - 1
MIN_SAFE_INTEGER: Final[int] = -MAX_SAFE_INTEGER

_NAMESPACE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-z][a-z0-9_.-]{0,95}$"
)

CanonicalScalar: TypeAlias = None | bool | int | str
CanonicalJsonValue: TypeAlias = (
    CanonicalScalar
    | list["CanonicalJsonValue"]
    | dict[str, "CanonicalJsonValue"]
)


class CanonicalizationError(ValueError):
    """Base error for rejected canonical input."""


class UnsupportedCanonicalTypeError(
    CanonicalizationError
):
    """Raised when a value has no approved encoding."""


class CanonicalizationCycleError(
    CanonicalizationError
):
    """Raised when recursive container ancestry is found."""


class CanonicalKeyCollisionError(
    CanonicalizationError
):
    """Raised when normalized mapping keys collide."""


class MutableDataclassError(
    CanonicalizationError
):
    """Raised when a mutable dataclass is presented."""


class InvalidStableNamespaceError(
    CanonicalizationError
):
    """Raised when a stable-ID namespace is invalid."""


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)

    try:
        normalized.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise CanonicalizationError(
            "Text contains an invalid Unicode surrogate."
        ) from error

    return normalized


def _enter(
    value: object,
    active: set[int],
) -> int:
    identity = id(value)

    if identity in active:
        raise CanonicalizationCycleError(
            "Recursive container ancestry is forbidden."
        )

    active.add(identity)
    return identity


def _canonicalize(
    value: Any,
    active: set[int],
) -> CanonicalJsonValue:
    if value is None:
        return None

    if isinstance(value, Enum):
        return _canonicalize(value.value, active)

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        if not (
            MIN_SAFE_INTEGER
            <= value
            <= MAX_SAFE_INTEGER
        ):
            raise CanonicalizationError(
                "Integer is outside the interoperable "
                "JSON safe range."
            )

        return value

    if isinstance(value, str):
        return _normalize_text(value)

    if isinstance(value, float):
        raise UnsupportedCanonicalTypeError(
            "Floating-point values are forbidden."
        )

    if isinstance(value, datetime):
        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise CanonicalizationError(
                "Datetime values must be timezone-aware."
            )

        return (
            value.astimezone(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )

    if isinstance(value, date):
        return value.isoformat()

    if (
        is_dataclass(value)
        and not isinstance(value, type)
    ):
        parameters = getattr(
            type(value),
            "__dataclass_params__",
            None,
        )

        if (
            parameters is None
            or parameters.frozen is not True
        ):
            raise MutableDataclassError(
                "Only frozen dataclass instances "
                "may be canonicalized."
            )

        identity = _enter(value, active)

        try:
            record = {
                field.name: getattr(
                    value,
                    field.name,
                )
                for field in fields(value)
            }
            return _canonicalize(record, active)
        finally:
            active.remove(identity)

    if isinstance(value, Mapping):
        identity = _enter(value, active)

        try:
            normalized: dict[
                str,
                CanonicalJsonValue,
            ] = {}

            for key, item in value.items():
                if not isinstance(key, str):
                    raise UnsupportedCanonicalTypeError(
                        "Canonical mapping keys "
                        "must be strings."
                    )

                normalized_key = _normalize_text(key)

                if normalized_key in normalized:
                    raise CanonicalKeyCollisionError(
                        "Mapping keys collide after "
                        "Unicode normalization."
                    )

                normalized[normalized_key] = (
                    _canonicalize(item, active)
                )

            return {
                key: normalized[key]
                for key in sorted(normalized)
            }
        finally:
            active.remove(identity)

    if isinstance(value, (list, tuple)):
        identity = _enter(value, active)

        try:
            return [
                _canonicalize(item, active)
                for item in value
            ]
        finally:
            active.remove(identity)

    raise UnsupportedCanonicalTypeError(
        "Unsupported canonical type: "
        f"{type(value).__module__}."
        f"{type(value).__qualname__}"
    )


def canonicalize(
    value: Any,
) -> CanonicalJsonValue:
    """Return a strict JSON-compatible normalized value."""

    return _canonicalize(value, set())


def canonical_json(value: Any) -> str:
    """Return compact deterministic canonical JSON text."""

    normalized = canonicalize(value)

    return json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_bytes(value: Any) -> bytes:
    """Return canonical JSON encoded as strict UTF-8."""

    return canonical_json(value).encode(
        "utf-8",
        errors="strict",
    )


def canonical_sha256(value: Any) -> str:
    """Return the lowercase SHA-256 content digest."""

    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def stable_identifier(
    namespace: str,
    value: Any,
) -> str:
    """Return a namespaced content-addressed identifier."""

    normalized_namespace = _normalize_text(
        namespace
    )

    if not _NAMESPACE_PATTERN.fullmatch(
        normalized_namespace
    ):
        raise InvalidStableNamespaceError(
            "Namespace must begin with a lowercase "
            "ASCII letter and contain only lowercase "
            "letters, digits, dots, underscores, "
            "or hyphens."
        )

    return (
        f"{normalized_namespace}:sha256:"
        f"{canonical_sha256(value)}"
    )


__all__ = (
    "CanonicalJsonValue",
    "CanonicalKeyCollisionError",
    "CanonicalizationCycleError",
    "CanonicalizationError",
    "InvalidStableNamespaceError",
    "MAX_SAFE_INTEGER",
    "MIN_SAFE_INTEGER",
    "MutableDataclassError",
    "UnsupportedCanonicalTypeError",
    "canonical_bytes",
    "canonical_json",
    "canonical_sha256",
    "canonicalize",
    "stable_identifier",
)
