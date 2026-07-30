"""Immutable contract-kernel primitives for Forge 2."""

from .canonical import (
    CanonicalJsonValue,
    CanonicalKeyCollisionError,
    CanonicalizationCycleError,
    CanonicalizationError,
    InvalidStableNamespaceError,
    MAX_SAFE_INTEGER,
    MIN_SAFE_INTEGER,
    MutableDataclassError,
    UnsupportedCanonicalTypeError,
    canonical_bytes,
    canonical_json,
    canonical_sha256,
    canonicalize,
    stable_identifier,
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
