"""Immutable bounded ContextManifest contracts.

This module records context already admitted or
explicitly excluded for one task step.

It does not retrieve, rank, select, infer, promote,
authorize, plan, or execute.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import re
from typing import Any, Final

from .canonical import (
    canonical_bytes,
    canonical_sha256,
    canonicalize,
    stable_identifier,
)
from .codec import (
    contract_metadata_from_dict,
    contract_metadata_to_dict,
    contract_reference_from_dict,
)
from .frozen_value import (
    FrozenCanonicalValue,
    freeze_canonical,
    is_frozen_canonical,
    thaw_canonical,
)
from .identity import (
    AuthorityStatus,
    ContractIntegrityError,
    ContractMetadata,
    ContractReference,
    ContractValidationError,
    LifecycleState,
    SchemaVersion,
    create_contract_metadata,
    verify_contract_metadata,
)
from .request_contract import (
    RequestContract,
)


CONTEXT_MANIFEST_TYPE: Final[str] = (
    "ContextManifest"
)
CONTEXT_MANIFEST_SCHEMA_VERSION: Final[
    SchemaVersion
] = SchemaVersion(1, 0, 0)

REPOSITORY_SNAPSHOT_ID_NAMESPACE: Final[
    str
] = "aiweb.repository-snapshot"
CONTEXT_ITEM_ID_NAMESPACE: Final[
    str
] = "aiweb.context-item"
EXCLUDED_CONTEXT_ITEM_ID_NAMESPACE: Final[
    str
] = "aiweb.excluded-context-item"

_REPOSITORY_SNAPSHOT_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.repository-snapshot:sha256:"
    r"[0-9a-f]{64}$"
)
_CONTEXT_ITEM_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.context-item:sha256:"
    r"[0-9a-f]{64}$"
)
_EXCLUDED_ITEM_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.excluded-context-item:sha256:"
    r"[0-9a-f]{64}$"
)
_SHA256_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^[0-9a-f]{64}$"
)
_GIT_COMMIT_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^[0-9a-f]{40}$"
)
_CODE_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^[a-z][a-z0-9_.-]{0,127}$"
)
_PRODUCER_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^[a-z][a-z0-9_.:-]{0,127}$"
)
_SOURCE_URI_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^[a-z][a-z0-9+.-]{0,31}:"
    r"[^\s]{1,2016}$"
)

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
        "request_contract",
        "step_id",
        "repository",
        "budget",
        "producer_id",
        "admitted_items",
        "excluded_items",
        "admitted_item_count",
        "excluded_item_count",
        "admitted_total_bytes",
    }
)
_REPOSITORY_KEYS: Final[
    frozenset[str]
] = frozenset(
    {
        "snapshot_id",
        "repository_uri",
        "commit_sha",
    }
)
_BUDGET_KEYS: Final[
    frozenset[str]
] = frozenset(
    {
        "max_items",
        "max_total_bytes",
        "max_item_bytes",
    }
)
_CONTEXT_ITEM_KEYS: Final[
    frozenset[str]
] = frozenset(
    {
        "item_id",
        "kind",
        "source_uri",
        "source_revision",
        "locator",
        "content_hash",
        "byte_count",
        "content",
        "admission_basis_codes",
    }
)
_EXCLUDED_ITEM_KEYS: Final[
    frozenset[str]
] = frozenset(
    {
        "exclusion_id",
        "kind",
        "source_uri",
        "source_revision",
        "locator",
        "content_hash",
        "byte_count",
        "reason_code",
        "reason_text",
    }
)


class ContextItemKind(StrEnum):
    """Exact categories required by the Build Bible."""

    FILE_SLICE = "file_slice"
    SYMBOL_REFERENCE = "symbol_reference"
    TEST_OUTPUT = "test_output"
    POLICY = "policy"
    DOCUMENTATION = "documentation"
    CAPABILITY_DESCRIPTION = (
        "capability_description"
    )
    MEMORY_CANDIDATE = "memory_candidate"
    PRIOR_TASK_RESULT = "prior_task_result"


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


def _normalized_text(
    value: object,
    *,
    field: str,
    maximum_length: int,
) -> str:
    if not isinstance(value, str):
        raise _error(
            "invalid_text_type",
            field,
            "Value must be text.",
        )

    normalized = canonicalize(value)

    if not isinstance(normalized, str):
        raise _error(
            "invalid_text_type",
            field,
            "Value must normalize to text.",
        )

    if not normalized:
        raise _error(
            "empty_text",
            field,
            "Value must not be empty.",
        )

    if normalized != normalized.strip():
        raise _error(
            "surrounding_whitespace",
            field,
            (
                "Leading or trailing whitespace "
                "is forbidden."
            ),
        )

    if len(normalized) > maximum_length:
        raise _error(
            "text_too_long",
            field,
            (
                f"Value exceeds "
                f"{maximum_length} characters."
            ),
        )

    return normalized


def _normalized_code(
    value: object,
    *,
    field: str,
) -> str:
    normalized = _normalized_text(
        value,
        field=field,
        maximum_length=128,
    )

    if not _CODE_PATTERN.fullmatch(
        normalized
    ):
        raise _error(
            "invalid_code",
            field,
            (
                "Value must use lowercase "
                "stable-code form."
            ),
        )

    return normalized


def _normalized_producer_id(
    value: object,
) -> str:
    normalized = _normalized_text(
        value,
        field="producer_id",
        maximum_length=128,
    )

    if not _PRODUCER_ID_PATTERN.fullmatch(
        normalized
    ):
        raise _error(
            "invalid_producer_id",
            "producer_id",
            (
                "Producer ID is not in "
                "approved stable form."
            ),
        )

    return normalized


def _normalized_source_uri(
    value: object,
    *,
    field: str,
) -> str:
    normalized = _normalized_text(
        value,
        field=field,
        maximum_length=2048,
    )

    if not _SOURCE_URI_PATTERN.fullmatch(
        normalized
    ):
        raise _error(
            "invalid_source_uri",
            field,
            (
                "Source URI must use a stable "
                "scheme and contain no whitespace."
            ),
        )

    return normalized


def _normalized_sha256(
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
        raise _error(
            "invalid_sha256",
            field,
            (
                "Value must be a lowercase "
                "SHA-256 hexadecimal digest."
            ),
        )

    return value


def _normalized_integer(
    value: object,
    *,
    field: str,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
    ):
        raise _error(
            "invalid_integer_type",
            field,
            "Value must be an integer.",
        )

    if value < minimum or value > maximum:
        raise _error(
            "integer_out_of_range",
            field,
            (
                f"Value must be between "
                f"{minimum} and {maximum}."
            ),
        )

    return value


def _normalize_codes(
    values: Iterable[str],
    *,
    field: str,
    allow_empty: bool,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise _error(
            "invalid_code_collection",
            field,
            (
                "Codes must be an iterable "
                "of strings."
            ),
        )

    try:
        observed = tuple(values)
    except TypeError as error:
        raise _error(
            "invalid_code_collection",
            field,
            "Codes must be iterable.",
        ) from error

    normalized = tuple(
        _normalized_code(
            value,
            field=field,
        )
        for value in observed
    )
    ordered = tuple(sorted(normalized))

    if not ordered and not allow_empty:
        raise _error(
            "code_required",
            field,
            (
                "At least one stable code "
                "is required."
            ),
        )

    if len(set(ordered)) != len(ordered):
        raise _error(
            "duplicate_code",
            field,
            "Codes must be unique.",
        )

    return ordered


def _repository_material(
    *,
    repository_uri: str,
    commit_sha: str,
) -> dict[str, Any]:
    return {
        "repository_uri": repository_uri,
        "commit_sha": commit_sha,
    }


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    """One exact repository and Git commit."""

    snapshot_id: str
    repository_uri: str
    commit_sha: str

    def __post_init__(self) -> None:
        repository_uri = (
            _normalized_source_uri(
                self.repository_uri,
                field="repository_uri",
            )
        )

        if (
            not isinstance(
                self.commit_sha,
                str,
            )
            or not _GIT_COMMIT_PATTERN.fullmatch(
                self.commit_sha
            )
        ):
            raise _error(
                "invalid_git_commit",
                "commit_sha",
                (
                    "Commit must be a full "
                    "lowercase 40-character "
                    "Git SHA."
                ),
            )

        if (
            not isinstance(
                self.snapshot_id,
                str,
            )
            or not (
                _REPOSITORY_SNAPSHOT_ID_PATTERN
                .fullmatch(self.snapshot_id)
            )
        ):
            raise _error(
                "invalid_repository_snapshot_id",
                "snapshot_id",
                (
                    "Snapshot ID must use the "
                    "approved SHA-256 form."
                ),
            )

        expected_id = stable_identifier(
            REPOSITORY_SNAPSHOT_ID_NAMESPACE,
            _repository_material(
                repository_uri=repository_uri,
                commit_sha=self.commit_sha,
            ),
        )

        if self.snapshot_id != expected_id:
            raise ContractIntegrityError(
                "repository_snapshot_id_mismatch",
                "snapshot_id",
                (
                    "Repository snapshot ID "
                    "does not match its material."
                ),
            )

        object.__setattr__(
            self,
            "repository_uri",
            repository_uri,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "repository_uri": (
                self.repository_uri
            ),
            "commit_sha": self.commit_sha,
        }


def create_repository_snapshot(
    *,
    repository_uri: str,
    commit_sha: str,
) -> RepositorySnapshot:
    normalized_uri = _normalized_source_uri(
        repository_uri,
        field="repository_uri",
    )

    if (
        not isinstance(commit_sha, str)
        or not _GIT_COMMIT_PATTERN.fullmatch(
            commit_sha
        )
    ):
        raise _error(
            "invalid_git_commit",
            "commit_sha",
            (
                "Commit must be a full "
                "lowercase 40-character Git SHA."
            ),
        )

    snapshot_id = stable_identifier(
        REPOSITORY_SNAPSHOT_ID_NAMESPACE,
        _repository_material(
            repository_uri=normalized_uri,
            commit_sha=commit_sha,
        ),
    )

    return RepositorySnapshot(
        snapshot_id=snapshot_id,
        repository_uri=normalized_uri,
        commit_sha=commit_sha,
    )


@dataclass(frozen=True, slots=True)
class ContextBudget:
    """Hard item and canonical-byte boundaries."""

    max_items: int
    max_total_bytes: int
    max_item_bytes: int

    def __post_init__(self) -> None:
        max_items = _normalized_integer(
            self.max_items,
            field="max_items",
            minimum=1,
            maximum=100_000,
        )
        max_total_bytes = (
            _normalized_integer(
                self.max_total_bytes,
                field="max_total_bytes",
                minimum=1,
                maximum=1_073_741_824,
            )
        )
        max_item_bytes = (
            _normalized_integer(
                self.max_item_bytes,
                field="max_item_bytes",
                minimum=1,
                maximum=1_073_741_824,
            )
        )

        if max_item_bytes > max_total_bytes:
            raise _error(
                "item_budget_exceeds_total",
                "max_item_bytes",
                (
                    "Per-item byte budget cannot "
                    "exceed total byte budget."
                ),
            )

    def to_dict(
        self,
    ) -> dict[str, int]:
        return {
            "max_items": self.max_items,
            "max_total_bytes": (
                self.max_total_bytes
            ),
            "max_item_bytes": (
                self.max_item_bytes
            ),
        }


def create_context_budget(
    *,
    max_items: int,
    max_total_bytes: int,
    max_item_bytes: int,
) -> ContextBudget:
    return ContextBudget(
        max_items=max_items,
        max_total_bytes=max_total_bytes,
        max_item_bytes=max_item_bytes,
    )


def _context_item_material(
    *,
    kind: ContextItemKind,
    source_uri: str,
    source_revision: str,
    locator: str,
    content_hash: str,
    byte_count: int,
    admission_basis_codes: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "kind": kind.value,
        "source_uri": source_uri,
        "source_revision": source_revision,
        "locator": locator,
        "content_hash": content_hash,
        "byte_count": byte_count,
        "admission_basis_codes": list(
            admission_basis_codes
        ),
    }


@dataclass(frozen=True, slots=True)
class ContextItem:
    """One exact piece of admitted task evidence."""

    item_id: str
    kind: ContextItemKind
    source_uri: str
    source_revision: str
    locator: str
    content_hash: str
    byte_count: int
    content: FrozenCanonicalValue
    admission_basis_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.kind,
            ContextItemKind,
        ):
            raise _error(
                "invalid_context_item_kind",
                "kind",
                (
                    "Kind must be "
                    "ContextItemKind."
                ),
            )

        source_uri = _normalized_source_uri(
            self.source_uri,
            field="source_uri",
        )
        source_revision = _normalized_text(
            self.source_revision,
            field="source_revision",
            maximum_length=512,
        )
        locator = _normalized_text(
            self.locator,
            field="locator",
            maximum_length=2048,
        )
        content_hash = _normalized_sha256(
            self.content_hash,
            field="content_hash",
        )
        byte_count = _normalized_integer(
            self.byte_count,
            field="byte_count",
            minimum=1,
            maximum=1_073_741_824,
        )

        if not is_frozen_canonical(
            self.content
        ):
            raise _error(
                "content_not_frozen_canonical",
                "content",
                (
                    "Context content must be "
                    "deeply frozen canonical data."
                ),
            )

        observed_hash = canonical_sha256(
            self.content
        )
        observed_bytes = len(
            canonical_bytes(self.content)
        )

        if content_hash != observed_hash:
            raise ContractIntegrityError(
                "context_item_content_hash_mismatch",
                "content_hash",
                (
                    "Context item content hash "
                    "does not match its content."
                ),
            )

        if byte_count != observed_bytes:
            raise ContractIntegrityError(
                "context_item_byte_count_mismatch",
                "byte_count",
                (
                    "Context item byte count "
                    "does not match canonical "
                    "content bytes."
                ),
            )

        if not isinstance(
            self.admission_basis_codes,
            tuple,
        ):
            raise _error(
                "admission_basis_not_immutable",
                "admission_basis_codes",
                (
                    "Stored admission basis "
                    "codes must be a tuple."
                ),
            )

        basis_codes = _normalize_codes(
            self.admission_basis_codes,
            field="admission_basis_codes",
            allow_empty=False,
        )

        if (
            basis_codes
            != self.admission_basis_codes
        ):
            raise _error(
                "admission_basis_not_canonical",
                "admission_basis_codes",
                (
                    "Admission basis codes must "
                    "use canonical order."
                ),
            )

        if (
            not isinstance(
                self.item_id,
                str,
            )
            or not _CONTEXT_ITEM_ID_PATTERN.fullmatch(
                self.item_id
            )
        ):
            raise _error(
                "invalid_context_item_id",
                "item_id",
                (
                    "Context item ID must use "
                    "the approved SHA-256 form."
                ),
            )

        expected_id = stable_identifier(
            CONTEXT_ITEM_ID_NAMESPACE,
            _context_item_material(
                kind=self.kind,
                source_uri=source_uri,
                source_revision=source_revision,
                locator=locator,
                content_hash=content_hash,
                byte_count=byte_count,
                admission_basis_codes=(
                    basis_codes
                ),
            ),
        )

        if self.item_id != expected_id:
            raise ContractIntegrityError(
                "context_item_id_mismatch",
                "item_id",
                (
                    "Context item ID does not "
                    "match its material."
                ),
            )

        object.__setattr__(
            self,
            "source_uri",
            source_uri,
        )
        object.__setattr__(
            self,
            "source_revision",
            source_revision,
        )
        object.__setattr__(
            self,
            "locator",
            locator,
        )
        object.__setattr__(
            self,
            "content_hash",
            content_hash,
        )
        object.__setattr__(
            self,
            "byte_count",
            byte_count,
        )
        object.__setattr__(
            self,
            "admission_basis_codes",
            basis_codes,
        )

    def material_key(
        self,
    ) -> tuple[str, str, str, str, str]:
        return (
            self.kind.value,
            self.source_uri,
            self.source_revision,
            self.locator,
            self.content_hash,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "kind": self.kind.value,
            "source_uri": self.source_uri,
            "source_revision": (
                self.source_revision
            ),
            "locator": self.locator,
            "content_hash": self.content_hash,
            "byte_count": self.byte_count,
            "content": thaw_canonical(
                self.content
            ),
            "admission_basis_codes": list(
                self.admission_basis_codes
            ),
        }


def create_context_item(
    *,
    kind: ContextItemKind,
    source_uri: str,
    source_revision: str,
    locator: str,
    content: object,
    admission_basis_codes: Iterable[str],
) -> ContextItem:
    if not isinstance(
        kind,
        ContextItemKind,
    ):
        raise _error(
            "invalid_context_item_kind",
            "kind",
            (
                "Kind must be "
                "ContextItemKind."
            ),
        )

    normalized_uri = _normalized_source_uri(
        source_uri,
        field="source_uri",
    )
    normalized_revision = _normalized_text(
        source_revision,
        field="source_revision",
        maximum_length=512,
    )
    normalized_locator = _normalized_text(
        locator,
        field="locator",
        maximum_length=2048,
    )
    frozen_content = freeze_canonical(
        content
    )
    content_hash = canonical_sha256(
        frozen_content
    )
    byte_count = len(
        canonical_bytes(frozen_content)
    )
    basis_codes = _normalize_codes(
        admission_basis_codes,
        field="admission_basis_codes",
        allow_empty=False,
    )

    item_id = stable_identifier(
        CONTEXT_ITEM_ID_NAMESPACE,
        _context_item_material(
            kind=kind,
            source_uri=normalized_uri,
            source_revision=normalized_revision,
            locator=normalized_locator,
            content_hash=content_hash,
            byte_count=byte_count,
            admission_basis_codes=(
                basis_codes
            ),
        ),
    )

    return ContextItem(
        item_id=item_id,
        kind=kind,
        source_uri=normalized_uri,
        source_revision=normalized_revision,
        locator=normalized_locator,
        content_hash=content_hash,
        byte_count=byte_count,
        content=frozen_content,
        admission_basis_codes=(
            basis_codes
        ),
    )


def _excluded_item_material(
    *,
    kind: ContextItemKind,
    source_uri: str,
    source_revision: str,
    locator: str,
    content_hash: str,
    byte_count: int,
    reason_code: str,
    reason_text: str,
) -> dict[str, Any]:
    return {
        "kind": kind.value,
        "source_uri": source_uri,
        "source_revision": source_revision,
        "locator": locator,
        "content_hash": content_hash,
        "byte_count": byte_count,
        "reason_code": reason_code,
        "reason_text": reason_text,
    }


@dataclass(frozen=True, slots=True)
class ExcludedContextItem:
    """Exact material excluded without admitting content."""

    exclusion_id: str
    kind: ContextItemKind
    source_uri: str
    source_revision: str
    locator: str
    content_hash: str
    byte_count: int
    reason_code: str
    reason_text: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.kind,
            ContextItemKind,
        ):
            raise _error(
                "invalid_context_item_kind",
                "kind",
                (
                    "Kind must be "
                    "ContextItemKind."
                ),
            )

        source_uri = _normalized_source_uri(
            self.source_uri,
            field="source_uri",
        )
        source_revision = _normalized_text(
            self.source_revision,
            field="source_revision",
            maximum_length=512,
        )
        locator = _normalized_text(
            self.locator,
            field="locator",
            maximum_length=2048,
        )
        content_hash = _normalized_sha256(
            self.content_hash,
            field="content_hash",
        )
        byte_count = _normalized_integer(
            self.byte_count,
            field="byte_count",
            minimum=1,
            maximum=1_073_741_824,
        )
        reason_code = _normalized_code(
            self.reason_code,
            field="reason_code",
        )
        reason_text = _normalized_text(
            self.reason_text,
            field="reason_text",
            maximum_length=2048,
        )

        if (
            not isinstance(
                self.exclusion_id,
                str,
            )
            or not (
                _EXCLUDED_ITEM_ID_PATTERN
                .fullmatch(self.exclusion_id)
            )
        ):
            raise _error(
                "invalid_excluded_context_item_id",
                "exclusion_id",
                (
                    "Exclusion ID must use the "
                    "approved SHA-256 form."
                ),
            )

        expected_id = stable_identifier(
            EXCLUDED_CONTEXT_ITEM_ID_NAMESPACE,
            _excluded_item_material(
                kind=self.kind,
                source_uri=source_uri,
                source_revision=source_revision,
                locator=locator,
                content_hash=content_hash,
                byte_count=byte_count,
                reason_code=reason_code,
                reason_text=reason_text,
            ),
        )

        if self.exclusion_id != expected_id:
            raise ContractIntegrityError(
                "excluded_context_item_id_mismatch",
                "exclusion_id",
                (
                    "Exclusion ID does not "
                    "match its material."
                ),
            )

        object.__setattr__(
            self,
            "source_uri",
            source_uri,
        )
        object.__setattr__(
            self,
            "source_revision",
            source_revision,
        )
        object.__setattr__(
            self,
            "locator",
            locator,
        )
        object.__setattr__(
            self,
            "content_hash",
            content_hash,
        )
        object.__setattr__(
            self,
            "byte_count",
            byte_count,
        )
        object.__setattr__(
            self,
            "reason_code",
            reason_code,
        )
        object.__setattr__(
            self,
            "reason_text",
            reason_text,
        )

    def material_key(
        self,
    ) -> tuple[str, str, str, str, str]:
        return (
            self.kind.value,
            self.source_uri,
            self.source_revision,
            self.locator,
            self.content_hash,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "exclusion_id": (
                self.exclusion_id
            ),
            "kind": self.kind.value,
            "source_uri": self.source_uri,
            "source_revision": (
                self.source_revision
            ),
            "locator": self.locator,
            "content_hash": self.content_hash,
            "byte_count": self.byte_count,
            "reason_code": self.reason_code,
            "reason_text": self.reason_text,
        }


def create_excluded_context_item(
    *,
    kind: ContextItemKind,
    source_uri: str,
    source_revision: str,
    locator: str,
    content: object,
    reason_code: str,
    reason_text: str,
) -> ExcludedContextItem:
    if not isinstance(
        kind,
        ContextItemKind,
    ):
        raise _error(
            "invalid_context_item_kind",
            "kind",
            (
                "Kind must be "
                "ContextItemKind."
            ),
        )

    normalized_uri = _normalized_source_uri(
        source_uri,
        field="source_uri",
    )
    normalized_revision = _normalized_text(
        source_revision,
        field="source_revision",
        maximum_length=512,
    )
    normalized_locator = _normalized_text(
        locator,
        field="locator",
        maximum_length=2048,
    )
    frozen_content = freeze_canonical(
        content
    )
    content_hash = canonical_sha256(
        frozen_content
    )
    byte_count = len(
        canonical_bytes(frozen_content)
    )
    normalized_reason_code = (
        _normalized_code(
            reason_code,
            field="reason_code",
        )
    )
    normalized_reason_text = (
        _normalized_text(
            reason_text,
            field="reason_text",
            maximum_length=2048,
        )
    )

    exclusion_id = stable_identifier(
        EXCLUDED_CONTEXT_ITEM_ID_NAMESPACE,
        _excluded_item_material(
            kind=kind,
            source_uri=normalized_uri,
            source_revision=normalized_revision,
            locator=normalized_locator,
            content_hash=content_hash,
            byte_count=byte_count,
            reason_code=(
                normalized_reason_code
            ),
            reason_text=(
                normalized_reason_text
            ),
        ),
    )

    return ExcludedContextItem(
        exclusion_id=exclusion_id,
        kind=kind,
        source_uri=normalized_uri,
        source_revision=normalized_revision,
        locator=normalized_locator,
        content_hash=content_hash,
        byte_count=byte_count,
        reason_code=normalized_reason_code,
        reason_text=normalized_reason_text,
    )


def _normalize_admitted_items(
    values: Iterable[ContextItem],
) -> tuple[ContextItem, ...]:
    if isinstance(values, (str, bytes)):
        raise _error(
            "invalid_context_item_collection",
            "admitted_items",
            (
                "Admitted items must be "
                "an iterable."
            ),
        )

    try:
        items = tuple(values)
    except TypeError as error:
        raise _error(
            "invalid_context_item_collection",
            "admitted_items",
            "Admitted items must be iterable.",
        ) from error

    if not items:
        raise _error(
            "admitted_context_required",
            "admitted_items",
            (
                "At least one exact context "
                "item is required."
            ),
        )

    for item in items:
        if not isinstance(
            item,
            ContextItem,
        ):
            raise _error(
                "invalid_context_item",
                "admitted_items",
                (
                    "Every admitted item must "
                    "be ContextItem."
                ),
            )

    ordered = tuple(
        sorted(
            items,
            key=lambda item: item.item_id,
        )
    )

    if (
        len(
            {
                item.item_id
                for item in ordered
            }
        )
        != len(ordered)
    ):
        raise _error(
            "duplicate_context_item",
            "admitted_items",
            (
                "Admitted item IDs must "
                "be unique."
            ),
        )

    return ordered


def _normalize_excluded_items(
    values: Iterable[
        ExcludedContextItem
    ],
) -> tuple[ExcludedContextItem, ...]:
    if isinstance(values, (str, bytes)):
        raise _error(
            "invalid_excluded_item_collection",
            "excluded_items",
            (
                "Excluded items must be "
                "an iterable."
            ),
        )

    try:
        items = tuple(values)
    except TypeError as error:
        raise _error(
            "invalid_excluded_item_collection",
            "excluded_items",
            "Excluded items must be iterable.",
        ) from error

    for item in items:
        if not isinstance(
            item,
            ExcludedContextItem,
        ):
            raise _error(
                "invalid_excluded_context_item",
                "excluded_items",
                (
                    "Every excluded item must "
                    "be ExcludedContextItem."
                ),
            )

    ordered = tuple(
        sorted(
            items,
            key=lambda item: item.exclusion_id,
        )
    )

    if (
        len(
            {
                item.exclusion_id
                for item in ordered
            }
        )
        != len(ordered)
    ):
        raise _error(
            "duplicate_excluded_context_item",
            "excluded_items",
            (
                "Excluded item IDs must "
                "be unique."
            ),
        )

    return ordered


def _context_manifest_body(
    *,
    request_contract: ContractReference,
    step_id: str,
    repository: RepositorySnapshot,
    budget: ContextBudget,
    producer_id: str,
    admitted_items: tuple[
        ContextItem,
        ...,
    ],
    excluded_items: tuple[
        ExcludedContextItem,
        ...,
    ],
) -> dict[str, Any]:
    return {
        "request_contract": (
            request_contract.to_dict()
        ),
        "step_id": step_id,
        "repository": repository.to_dict(),
        "budget": budget.to_dict(),
        "producer_id": producer_id,
        "admitted_items": [
            item.to_dict()
            for item in admitted_items
        ],
        "excluded_items": [
            item.to_dict()
            for item in excluded_items
        ],
        "admitted_item_count": len(
            admitted_items
        ),
        "excluded_item_count": len(
            excluded_items
        ),
        "admitted_total_bytes": sum(
            item.byte_count
            for item in admitted_items
        ),
    }


@dataclass(frozen=True, slots=True)
class ContextManifest:
    """Bounded evidence admitted to one task step."""

    metadata: ContractMetadata
    request_contract: ContractReference
    step_id: str
    repository: RepositorySnapshot
    budget: ContextBudget
    producer_id: str
    admitted_items: tuple[
        ContextItem,
        ...,
    ]
    excluded_items: tuple[
        ExcludedContextItem,
        ...,
    ]

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

        if not isinstance(
            self.request_contract,
            ContractReference,
        ):
            raise _error(
                "invalid_request_contract_reference",
                "request_contract",
                (
                    "Request contract must be "
                    "ContractReference."
                ),
            )

        if (
            self.request_contract.contract_type
            != "RequestContract"
        ):
            raise _error(
                "request_contract_reference_type_mismatch",
                "request_contract",
                (
                    "Source reference must "
                    "identify RequestContract."
                ),
            )

        step_id = _normalized_code(
            self.step_id,
            field="step_id",
        )

        if not isinstance(
            self.repository,
            RepositorySnapshot,
        ):
            raise _error(
                "invalid_repository_snapshot",
                "repository",
                (
                    "Repository must be "
                    "RepositorySnapshot."
                ),
            )

        if not isinstance(
            self.budget,
            ContextBudget,
        ):
            raise _error(
                "invalid_context_budget",
                "budget",
                (
                    "Budget must be "
                    "ContextBudget."
                ),
            )

        producer_id = (
            _normalized_producer_id(
                self.producer_id
            )
        )

        if not isinstance(
            self.admitted_items,
            tuple,
        ):
            raise _error(
                "admitted_items_not_immutable",
                "admitted_items",
                (
                    "Stored admitted items "
                    "must be a tuple."
                ),
            )

        admitted_items = (
            _normalize_admitted_items(
                self.admitted_items
            )
        )

        if (
            admitted_items
            != self.admitted_items
        ):
            raise _error(
                "admitted_items_not_canonical",
                "admitted_items",
                (
                    "Admitted items must use "
                    "canonical item-ID order."
                ),
            )

        if not isinstance(
            self.excluded_items,
            tuple,
        ):
            raise _error(
                "excluded_items_not_immutable",
                "excluded_items",
                (
                    "Stored excluded items "
                    "must be a tuple."
                ),
            )

        excluded_items = (
            _normalize_excluded_items(
                self.excluded_items
            )
        )

        if (
            excluded_items
            != self.excluded_items
        ):
            raise _error(
                "excluded_items_not_canonical",
                "excluded_items",
                (
                    "Excluded items must use "
                    "canonical exclusion-ID "
                    "order."
                ),
            )

        if (
            len(admitted_items)
            > self.budget.max_items
        ):
            raise _error(
                "context_item_budget_exceeded",
                "admitted_items",
                (
                    "Admitted item count "
                    "exceeds the manifest budget."
                ),
            )

        oversized_items = [
            item.item_id
            for item in admitted_items
            if (
                item.byte_count
                > self.budget.max_item_bytes
            )
        ]

        if oversized_items:
            raise _error(
                "context_per_item_budget_exceeded",
                "admitted_items",
                (
                    "One or more admitted items "
                    "exceed the per-item budget."
                ),
            )

        total_bytes = sum(
            item.byte_count
            for item in admitted_items
        )

        if (
            total_bytes
            > self.budget.max_total_bytes
        ):
            raise _error(
                "context_total_budget_exceeded",
                "admitted_items",
                (
                    "Admitted canonical bytes "
                    "exceed the total budget."
                ),
            )

        admitted_keys = {
            item.material_key()
            for item in admitted_items
        }
        excluded_keys = {
            item.material_key()
            for item in excluded_items
        }

        if admitted_keys & excluded_keys:
            raise _error(
                "context_admission_exclusion_overlap",
                "excluded_items",
                (
                    "The same exact material "
                    "cannot be both admitted "
                    "and excluded."
                ),
            )

        if (
            self.metadata.contract_type
            != CONTEXT_MANIFEST_TYPE
        ):
            raise _error(
                "context_manifest_type_mismatch",
                "contract_type",
                (
                    "Metadata contract type "
                    "is incorrect."
                ),
            )

        if (
            self.metadata.schema_version
            != CONTEXT_MANIFEST_SCHEMA_VERSION
        ):
            raise _error(
                "context_manifest_schema_mismatch",
                "schema_version",
                (
                    "ContextManifest must use "
                    "schema version 1.0.0."
                ),
            )

        if (
            self.metadata.authority_status
            != AuthorityStatus.NONE
        ):
            raise _error(
                "context_manifest_authority_forbidden",
                "authority_status",
                (
                    "ContextManifest cannot "
                    "carry authority."
                ),
            )

        if self.metadata.declared_effects:
            raise _error(
                "context_manifest_effects_forbidden",
                "declared_effects",
                (
                    "ContextManifest cannot "
                    "declare side effects."
                ),
            )

        if (
            self.metadata.parent is not None
            and (
                self.metadata
                .parent
                .contract_type
                != CONTEXT_MANIFEST_TYPE
            )
        ):
            raise _error(
                "context_manifest_parent_type_mismatch",
                "parent",
                (
                    "A ContextManifest parent "
                    "must reference "
                    "ContextManifest."
                ),
            )

        object.__setattr__(
            self,
            "step_id",
            step_id,
        )
        object.__setattr__(
            self,
            "producer_id",
            producer_id,
        )

        verify_contract_metadata(
            self.metadata,
            self.body(),
        )

    @property
    def admitted_total_bytes(
        self,
    ) -> int:
        return sum(
            item.byte_count
            for item in self.admitted_items
        )

    def body(
        self,
    ) -> dict[str, Any]:
        return _context_manifest_body(
            request_contract=(
                self.request_contract
            ),
            step_id=self.step_id,
            repository=self.repository,
            budget=self.budget,
            producer_id=self.producer_id,
            admitted_items=(
                self.admitted_items
            ),
            excluded_items=(
                self.excluded_items
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
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
                "ContextManifest did not "
                "serialize to a mapping."
            )

        return value


def _verify_request_contract_object(
    request_contract: RequestContract,
) -> None:
    if not isinstance(
        request_contract,
        RequestContract,
    ):
        raise _error(
            "invalid_request_contract_type",
            "request_contract",
            (
                "Value must be "
                "RequestContract."
            ),
        )

    verify_contract_metadata(
        request_contract.metadata,
        request_contract.body(),
    )


def create_context_manifest(
    *,
    request_contract: RequestContract,
    step_id: str,
    repository: RepositorySnapshot,
    budget: ContextBudget,
    producer_id: str,
    admitted_items: Iterable[
        ContextItem
    ],
    excluded_items: Iterable[
        ExcludedContextItem
    ],
    created_at: datetime,
) -> ContextManifest:
    """Create a manifest from explicit admission records."""

    _verify_request_contract_object(
        request_contract
    )

    normalized_step_id = _normalized_code(
        step_id,
        field="step_id",
    )

    if not isinstance(
        repository,
        RepositorySnapshot,
    ):
        raise _error(
            "invalid_repository_snapshot",
            "repository",
            (
                "Repository must be "
                "RepositorySnapshot."
            ),
        )

    if not isinstance(
        budget,
        ContextBudget,
    ):
        raise _error(
            "invalid_context_budget",
            "budget",
            (
                "Budget must be "
                "ContextBudget."
            ),
        )

    normalized_producer = (
        _normalized_producer_id(
            producer_id
        )
    )
    normalized_admitted = (
        _normalize_admitted_items(
            admitted_items
        )
    )
    normalized_excluded = (
        _normalize_excluded_items(
            excluded_items
        )
    )

    request_reference = (
        request_contract
        .metadata
        .to_reference()
    )

    body = _context_manifest_body(
        request_contract=request_reference,
        step_id=normalized_step_id,
        repository=repository,
        budget=budget,
        producer_id=normalized_producer,
        admitted_items=normalized_admitted,
        excluded_items=normalized_excluded,
    )

    metadata = create_contract_metadata(
        schema_version=(
            CONTEXT_MANIFEST_SCHEMA_VERSION
        ),
        contract_type=(
            CONTEXT_MANIFEST_TYPE
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

    result = ContextManifest(
        metadata=metadata,
        request_contract=request_reference,
        step_id=normalized_step_id,
        repository=repository,
        budget=budget,
        producer_id=normalized_producer,
        admitted_items=normalized_admitted,
        excluded_items=normalized_excluded,
    )

    verify_context_manifest(
        result,
        request_contract=request_contract,
    )

    return result


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

    keys = tuple(value.keys())

    if any(
        not isinstance(key, str)
        for key in keys
    ):
        raise _error(
            "invalid_mapping_key",
            field,
            (
                "All mapping keys must "
                "be text."
            ),
        )

    observed = frozenset(keys)

    if observed != expected:
        raise _error(
            "mapping_key_mismatch",
            field,
            (
                f"Missing keys: "
                f"{sorted(expected - observed)}; "
                f"unexpected keys: "
                f"{sorted(observed - expected)}."
            ),
        )

    return value


def _sequence(
    value: object,
    *,
    field: str,
) -> tuple[Any, ...]:
    if not isinstance(
        value,
        (list, tuple),
    ):
        raise _error(
            "invalid_sequence_type",
            field,
            (
                f"{field} must be a sequence."
            ),
        )

    return tuple(value)


def _repository_from_dict(
    value: object,
) -> RepositorySnapshot:
    record = _exact_mapping(
        value,
        _REPOSITORY_KEYS,
        field="repository",
    )

    return RepositorySnapshot(
        snapshot_id=record["snapshot_id"],
        repository_uri=(
            record["repository_uri"]
        ),
        commit_sha=record["commit_sha"],
    )


def _budget_from_dict(
    value: object,
) -> ContextBudget:
    record = _exact_mapping(
        value,
        _BUDGET_KEYS,
        field="budget",
    )

    return ContextBudget(
        max_items=record["max_items"],
        max_total_bytes=(
            record["max_total_bytes"]
        ),
        max_item_bytes=(
            record["max_item_bytes"]
        ),
    )


def _context_item_from_dict(
    value: object,
) -> ContextItem:
    record = _exact_mapping(
        value,
        _CONTEXT_ITEM_KEYS,
        field="context_item",
    )

    try:
        kind = ContextItemKind(
            record["kind"]
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise _error(
            "invalid_context_item_kind",
            "kind",
            (
                "Context item kind is unknown."
            ),
        ) from error

    basis_codes = _sequence(
        record["admission_basis_codes"],
        field="admission_basis_codes",
    )

    return ContextItem(
        item_id=record["item_id"],
        kind=kind,
        source_uri=record["source_uri"],
        source_revision=(
            record["source_revision"]
        ),
        locator=record["locator"],
        content_hash=record["content_hash"],
        byte_count=record["byte_count"],
        content=freeze_canonical(
            record["content"]
        ),
        admission_basis_codes=tuple(
            basis_codes
        ),
    )


def _excluded_item_from_dict(
    value: object,
) -> ExcludedContextItem:
    record = _exact_mapping(
        value,
        _EXCLUDED_ITEM_KEYS,
        field="excluded_context_item",
    )

    try:
        kind = ContextItemKind(
            record["kind"]
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise _error(
            "invalid_context_item_kind",
            "kind",
            (
                "Context item kind is unknown."
            ),
        ) from error

    return ExcludedContextItem(
        exclusion_id=record["exclusion_id"],
        kind=kind,
        source_uri=record["source_uri"],
        source_revision=(
            record["source_revision"]
        ),
        locator=record["locator"],
        content_hash=record["content_hash"],
        byte_count=record["byte_count"],
        reason_code=record["reason_code"],
        reason_text=record["reason_text"],
    )


def context_manifest_from_dict(
    value: object,
    *,
    request_contract: RequestContract,
) -> ContextManifest:
    """Decode an exact ContextManifest."""

    top = _exact_mapping(
        value,
        _TOP_LEVEL_KEYS,
        field="context_manifest",
    )
    body = _exact_mapping(
        top["body"],
        _BODY_KEYS,
        field="body",
    )

    admitted_values = _sequence(
        body["admitted_items"],
        field="admitted_items",
    )
    excluded_values = _sequence(
        body["excluded_items"],
        field="excluded_items",
    )

    admitted_items = tuple(
        _context_item_from_dict(item)
        for item in admitted_values
    )
    excluded_items = tuple(
        _excluded_item_from_dict(item)
        for item in excluded_values
    )

    admitted_count = _normalized_integer(
        body["admitted_item_count"],
        field="admitted_item_count",
        minimum=0,
        maximum=100_000,
    )
    excluded_count = _normalized_integer(
        body["excluded_item_count"],
        field="excluded_item_count",
        minimum=0,
        maximum=100_000,
    )
    admitted_total_bytes = (
        _normalized_integer(
            body["admitted_total_bytes"],
            field="admitted_total_bytes",
            minimum=0,
            maximum=1_073_741_824,
        )
    )

    if admitted_count != len(
        admitted_items
    ):
        raise ContractIntegrityError(
            "admitted_item_count_mismatch",
            "admitted_item_count",
            (
                "Recorded admitted count "
                "does not match admitted items."
            ),
        )

    if excluded_count != len(
        excluded_items
    ):
        raise ContractIntegrityError(
            "excluded_item_count_mismatch",
            "excluded_item_count",
            (
                "Recorded excluded count "
                "does not match excluded items."
            ),
        )

    observed_total = sum(
        item.byte_count
        for item in admitted_items
    )

    if (
        admitted_total_bytes
        != observed_total
    ):
        raise ContractIntegrityError(
            "admitted_total_bytes_mismatch",
            "admitted_total_bytes",
            (
                "Recorded admitted bytes "
                "do not match admitted items."
            ),
        )

    result = ContextManifest(
        metadata=(
            contract_metadata_from_dict(
                top["metadata"]
            )
        ),
        request_contract=(
            contract_reference_from_dict(
                body["request_contract"]
            )
        ),
        step_id=body["step_id"],
        repository=_repository_from_dict(
            body["repository"]
        ),
        budget=_budget_from_dict(
            body["budget"]
        ),
        producer_id=body["producer_id"],
        admitted_items=admitted_items,
        excluded_items=excluded_items,
    )

    verify_context_manifest(
        result,
        request_contract=request_contract,
    )

    return result


def verify_context_manifest(
    context_manifest: ContextManifest,
    *,
    request_contract: RequestContract,
) -> None:
    """Verify exact request and manifest identity binding."""

    if not isinstance(
        context_manifest,
        ContextManifest,
    ):
        raise _error(
            "invalid_context_manifest_type",
            "context_manifest",
            (
                "Value must be "
                "ContextManifest."
            ),
        )

    _verify_request_contract_object(
        request_contract
    )

    expected_reference = (
        request_contract
        .metadata
        .to_reference()
    )

    if (
        context_manifest.request_contract
        != expected_reference
    ):
        raise ContractIntegrityError(
            "context_request_contract_mismatch",
            "request_contract",
            (
                "ContextManifest does not "
                "reference the supplied "
                "RequestContract."
            ),
        )

    verify_contract_metadata(
        context_manifest.metadata,
        context_manifest.body(),
    )


__all__ = (
    "CONTEXT_ITEM_ID_NAMESPACE",
    "CONTEXT_MANIFEST_SCHEMA_VERSION",
    "CONTEXT_MANIFEST_TYPE",
    "EXCLUDED_CONTEXT_ITEM_ID_NAMESPACE",
    "REPOSITORY_SNAPSHOT_ID_NAMESPACE",
    "ContextBudget",
    "ContextItem",
    "ContextItemKind",
    "ContextManifest",
    "ExcludedContextItem",
    "RepositorySnapshot",
    "context_manifest_from_dict",
    "create_context_budget",
    "create_context_item",
    "create_context_manifest",
    "create_excluded_context_item",
    "create_repository_snapshot",
    "verify_context_manifest",
)
