"""Immutable ClassificationCandidateSet contract.

This module records model and rule-based request
candidates. It does not select meaning, authorize
action, or execute work.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import re
from typing import Any, Final

from .canonical import (
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
from .input_event import (
    InputEvent,
    verify_input_event,
)


CLASSIFICATION_CANDIDATE_SET_CONTRACT_TYPE: Final[
    str
] = "ClassificationCandidateSet"
CLASSIFICATION_CANDIDATE_SET_SCHEMA_VERSION: Final[
    SchemaVersion
] = SchemaVersion(1, 0, 0)
CLASSIFICATION_CANDIDATE_ID_NAMESPACE: Final[
    str
] = "aiweb.classification-candidate"
FEATURE_EVIDENCE_ID_NAMESPACE: Final[str] = (
    "aiweb.feature-evidence"
)
CONFIDENCE_SCALE_BASIS_POINTS: Final[int] = (
    10_000
)

_EVIDENCE_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.feature-evidence:sha256:"
    r"[0-9a-f]{64}$"
)
_CANDIDATE_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.classification-candidate:sha256:"
    r"[0-9a-f]{64}$"
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

_ALLOWED_INPUT_ROOTS: Final[
    frozenset[str]
] = frozenset(
    {
        "raw_input",
        "conversation_context",
        "identity_context",
        "session_metadata",
    }
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
        "input_event",
        "candidates",
        "uncertainty_codes",
        "clarification_recommended",
        "clarification_reason_codes",
    }
)
_CANDIDATE_KEYS: Final[
    frozenset[str]
] = frozenset(
    {
        "candidate_id",
        "dimension",
        "label",
        "origin",
        "producer_id",
        "confidence_basis_points",
        "evidence",
    }
)
_EVIDENCE_KEYS: Final[
    frozenset[str]
] = frozenset(
    {
        "evidence_id",
        "source_pointer",
        "feature_name",
        "observed_value",
        "span_start",
        "span_end",
    }
)


class CandidateDimension(StrEnum):
    """Roadmap classification dimensions."""

    REQUEST_KIND = "request_kind"
    DOMAIN = "domain"
    EXPECTED_RESULT = "expected_result"
    SIDE_EFFECT_CLASS = "side_effect_class"
    FRESHNESS_REQUIREMENT = (
        "freshness_requirement"
    )
    CAPABILITY = "capability"
    CODE_EXPLANATION_DISTINCTION = (
        "code_explanation_distinction"
    )
    TOOL_DISCOVERY_REQUIREMENT = (
        "tool_discovery_requirement"
    )
    SIMULATION_REQUIREMENT = (
        "simulation_requirement"
    )
    CLARIFICATION_REQUIREMENT = (
        "clarification_requirement"
    )
    RISK_CANDIDATE = "risk_candidate"


class CandidateOrigin(StrEnum):
    """Permitted candidate-producing sources."""

    RULE = "rule"
    MODEL = "model"


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
                "Leading or trailing "
                "whitespace is forbidden."
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


def _normalized_label(
    value: object,
) -> str:
    return _normalized_text(
        value,
        field="label",
        maximum_length=256,
    )


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


def _decode_pointer_segment(
    segment: str,
) -> str:
    output: list[str] = []
    index = 0

    while index < len(segment):
        character = segment[index]

        if character != "~":
            output.append(character)
            index += 1
            continue

        if index + 1 >= len(segment):
            raise _error(
                (
                    "invalid_source_"
                    "pointer_escape"
                ),
                "source_pointer",
                (
                    "Source pointer contains "
                    "an incomplete escape."
                ),
            )

        escape = segment[index + 1]

        if escape == "0":
            output.append("~")
        elif escape == "1":
            output.append("/")
        else:
            raise _error(
                (
                    "invalid_source_"
                    "pointer_escape"
                ),
                "source_pointer",
                (
                    "Source pointer contains "
                    "an unknown escape."
                ),
            )

        index += 2

    return "".join(output)


def _pointer_segments(
    pointer: str,
) -> tuple[str, ...]:
    if not pointer.startswith("/"):
        raise _error(
            "invalid_source_pointer",
            "source_pointer",
            (
                "Source pointer must begin "
                "with '/'."
            ),
        )

    segments = tuple(
        _decode_pointer_segment(segment)
        for segment
        in pointer[1:].split("/")
    )

    if (
        not segments
        or segments[0]
        not in _ALLOWED_INPUT_ROOTS
    ):
        raise _error(
            "invalid_source_pointer_root",
            "source_pointer",
            (
                "Source pointer must begin "
                "at an InputEvent body field."
            ),
        )

    return segments


def _normalized_source_pointer(
    value: object,
) -> str:
    pointer = _normalized_text(
        value,
        field="source_pointer",
        maximum_length=1024,
    )
    _pointer_segments(pointer)

    return pointer


def _normalize_span_value(
    value: object,
    *,
    field: str,
) -> int | None:
    if value is None:
        return None

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
    ):
        raise _error(
            "invalid_span_type",
            field,
            (
                "Span offsets must be "
                "integers or null."
            ),
        )

    if value < 0:
        raise _error(
            "negative_span_offset",
            field,
            (
                "Span offsets must not "
                "be negative."
            ),
        )

    return value


def _normalize_codes(
    values: Iterable[str],
    *,
    field: str,
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

    if len(set(ordered)) != len(ordered):
        raise _error(
            "duplicate_code",
            field,
            "Codes must be unique.",
        )

    return ordered


def _evidence_material(
    *,
    source_pointer: str,
    feature_name: str,
    observed_value: FrozenCanonicalValue,
    span_start: int | None,
    span_end: int | None,
) -> dict[str, Any]:
    return {
        "feature_name": feature_name,
        "observed_value": thaw_canonical(
            observed_value
        ),
        "source_pointer": source_pointer,
        "span_end": span_end,
        "span_start": span_start,
    }


def _expected_evidence_id(
    *,
    source_pointer: str,
    feature_name: str,
    observed_value: FrozenCanonicalValue,
    span_start: int | None,
    span_end: int | None,
) -> str:
    return stable_identifier(
        FEATURE_EVIDENCE_ID_NAMESPACE,
        _evidence_material(
            source_pointer=source_pointer,
            feature_name=feature_name,
            observed_value=observed_value,
            span_start=span_start,
            span_end=span_end,
        ),
    )


@dataclass(frozen=True, slots=True)
class FeatureEvidence:
    """One exact feature from an InputEvent."""

    evidence_id: str
    source_pointer: str
    feature_name: str
    observed_value: FrozenCanonicalValue
    span_start: int | None = None
    span_end: int | None = None

    def __post_init__(self) -> None:
        source_pointer = (
            _normalized_source_pointer(
                self.source_pointer
            )
        )
        feature_name = _normalized_code(
            self.feature_name,
            field="feature_name",
        )

        if not is_frozen_canonical(
            self.observed_value
        ):
            raise _error(
                "evidence_value_not_frozen",
                "observed_value",
                (
                    "Observed value must be "
                    "deeply immutable."
                ),
            )

        span_start = _normalize_span_value(
            self.span_start,
            field="span_start",
        )
        span_end = _normalize_span_value(
            self.span_end,
            field="span_end",
        )

        if (
            (span_start is None)
            != (span_end is None)
        ):
            raise _error(
                "incomplete_text_span",
                "span",
                (
                    "Both span offsets or "
                    "neither must be present."
                ),
            )

        if (
            span_start is not None
            and span_end is not None
            and span_end <= span_start
        ):
            raise _error(
                "invalid_text_span",
                "span",
                (
                    "Text span end must be "
                    "greater than start."
                ),
            )

        if (
            not isinstance(
                self.evidence_id,
                str,
            )
            or not _EVIDENCE_ID_PATTERN.fullmatch(
                self.evidence_id
            )
        ):
            raise _error(
                "invalid_feature_evidence_id",
                "evidence_id",
                (
                    "Evidence ID must use "
                    "the approved SHA-256 form."
                ),
            )

        expected_id = _expected_evidence_id(
            source_pointer=source_pointer,
            feature_name=feature_name,
            observed_value=(
                self.observed_value
            ),
            span_start=span_start,
            span_end=span_end,
        )

        if self.evidence_id != expected_id:
            raise ContractIntegrityError(
                "feature_evidence_id_mismatch",
                "evidence_id",
                (
                    "Evidence ID does not "
                    "match its material."
                ),
            )

        object.__setattr__(
            self,
            "source_pointer",
            source_pointer,
        )
        object.__setattr__(
            self,
            "feature_name",
            feature_name,
        )
        object.__setattr__(
            self,
            "span_start",
            span_start,
        )
        object.__setattr__(
            self,
            "span_end",
            span_end,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_pointer": (
                self.source_pointer
            ),
            "feature_name": self.feature_name,
            "observed_value": thaw_canonical(
                self.observed_value
            ),
            "span_start": self.span_start,
            "span_end": self.span_end,
        }


def create_feature_evidence(
    *,
    source_pointer: str,
    feature_name: str,
    observed_value: Any,
    span_start: int | None = None,
    span_end: int | None = None,
) -> FeatureEvidence:
    """Create immutable feature evidence."""

    pointer = _normalized_source_pointer(
        source_pointer
    )
    feature = _normalized_code(
        feature_name,
        field="feature_name",
    )
    frozen_value = freeze_canonical(
        observed_value
    )
    start = _normalize_span_value(
        span_start,
        field="span_start",
    )
    end = _normalize_span_value(
        span_end,
        field="span_end",
    )

    if (
        (start is None)
        != (end is None)
    ):
        raise _error(
            "incomplete_text_span",
            "span",
            (
                "Both span offsets or neither "
                "must be present."
            ),
        )

    if (
        start is not None
        and end is not None
        and end <= start
    ):
        raise _error(
            "invalid_text_span",
            "span",
            (
                "Text span end must be "
                "greater than start."
            ),
        )

    evidence_id = _expected_evidence_id(
        source_pointer=pointer,
        feature_name=feature,
        observed_value=frozen_value,
        span_start=start,
        span_end=end,
    )

    return FeatureEvidence(
        evidence_id=evidence_id,
        source_pointer=pointer,
        feature_name=feature,
        observed_value=frozen_value,
        span_start=start,
        span_end=end,
    )


def _normalize_evidence(
    values: Iterable[FeatureEvidence],
) -> tuple[FeatureEvidence, ...]:
    if isinstance(values, (str, bytes)):
        raise _error(
            "invalid_evidence_collection",
            "evidence",
            (
                "Evidence must be an iterable "
                "of FeatureEvidence."
            ),
        )

    try:
        evidence = tuple(values)
    except TypeError as error:
        raise _error(
            "invalid_evidence_collection",
            "evidence",
            "Evidence must be iterable.",
        ) from error

    if not evidence:
        raise _error(
            "candidate_evidence_required",
            "evidence",
            (
                "Every candidate must carry "
                "feature evidence."
            ),
        )

    for item in evidence:
        if not isinstance(
            item,
            FeatureEvidence,
        ):
            raise _error(
                "invalid_feature_evidence",
                "evidence",
                (
                    "Every evidence item must "
                    "be FeatureEvidence."
                ),
            )

    ordered = tuple(
        sorted(
            evidence,
            key=lambda item: (
                item.evidence_id
            ),
        )
    )

    if (
        len(
            {
                item.evidence_id
                for item in ordered
            }
        )
        != len(ordered)
    ):
        raise _error(
            "duplicate_feature_evidence",
            "evidence",
            (
                "Evidence IDs must be "
                "unique."
            ),
        )

    return ordered


def _candidate_material(
    *,
    dimension: CandidateDimension,
    label: str,
    origin: CandidateOrigin,
    producer_id: str,
    confidence_basis_points: int,
    evidence: tuple[
        FeatureEvidence,
        ...,
    ],
) -> dict[str, Any]:
    return {
        "confidence_basis_points": (
            confidence_basis_points
        ),
        "dimension": dimension.value,
        "evidence": [
            item.to_dict()
            for item in evidence
        ],
        "label": label,
        "origin": origin.value,
        "producer_id": producer_id,
    }


def _expected_candidate_id(
    *,
    dimension: CandidateDimension,
    label: str,
    origin: CandidateOrigin,
    producer_id: str,
    confidence_basis_points: int,
    evidence: tuple[
        FeatureEvidence,
        ...,
    ],
) -> str:
    return stable_identifier(
        CLASSIFICATION_CANDIDATE_ID_NAMESPACE,
        _candidate_material(
            dimension=dimension,
            label=label,
            origin=origin,
            producer_id=producer_id,
            confidence_basis_points=(
                confidence_basis_points
            ),
            evidence=evidence,
        ),
    )


@dataclass(frozen=True, slots=True)
class ClassificationCandidate:
    """One authority-neutral candidate."""

    candidate_id: str
    dimension: CandidateDimension
    label: str
    origin: CandidateOrigin
    producer_id: str
    confidence_basis_points: int
    evidence: tuple[
        FeatureEvidence,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.dimension,
            CandidateDimension,
        ):
            raise _error(
                "invalid_candidate_dimension",
                "dimension",
                (
                    "Dimension must be "
                    "CandidateDimension."
                ),
            )

        if not isinstance(
            self.origin,
            CandidateOrigin,
        ):
            raise _error(
                "invalid_candidate_origin",
                "origin",
                (
                    "Origin must be "
                    "CandidateOrigin."
                ),
            )

        label = _normalized_label(
            self.label
        )
        producer_id = (
            _normalized_producer_id(
                self.producer_id
            )
        )

        if (
            isinstance(
                self.confidence_basis_points,
                bool,
            )
            or not isinstance(
                self.confidence_basis_points,
                int,
            )
        ):
            raise _error(
                "invalid_confidence_type",
                "confidence_basis_points",
                (
                    "Confidence must be "
                    "an integer."
                ),
            )

        if not (
            0
            <= self.confidence_basis_points
            <= CONFIDENCE_SCALE_BASIS_POINTS
        ):
            raise _error(
                "confidence_out_of_range",
                "confidence_basis_points",
                (
                    "Confidence must be "
                    "between 0 and 10000."
                ),
            )

        if not isinstance(
            self.evidence,
            tuple,
        ):
            raise _error(
                (
                    "candidate_evidence_"
                    "not_immutable"
                ),
                "evidence",
                (
                    "Stored evidence must "
                    "be a tuple."
                ),
            )

        evidence = _normalize_evidence(
            self.evidence
        )

        if evidence != self.evidence:
            raise _error(
                (
                    "candidate_evidence_"
                    "not_canonical"
                ),
                "evidence",
                (
                    "Stored evidence must use "
                    "canonical ID order."
                ),
            )

        if (
            not isinstance(
                self.candidate_id,
                str,
            )
            or not _CANDIDATE_ID_PATTERN.fullmatch(
                self.candidate_id
            )
        ):
            raise _error(
                (
                    "invalid_classification_"
                    "candidate_id"
                ),
                "candidate_id",
                (
                    "Candidate ID must use "
                    "the approved SHA-256 form."
                ),
            )

        expected_id = _expected_candidate_id(
            dimension=self.dimension,
            label=label,
            origin=self.origin,
            producer_id=producer_id,
            confidence_basis_points=(
                self.confidence_basis_points
            ),
            evidence=evidence,
        )

        if self.candidate_id != expected_id:
            raise ContractIntegrityError(
                (
                    "classification_candidate_"
                    "id_mismatch"
                ),
                "candidate_id",
                (
                    "Candidate ID does not "
                    "match its material."
                ),
            )

        object.__setattr__(
            self,
            "label",
            label,
        )
        object.__setattr__(
            self,
            "producer_id",
            producer_id,
        )
        object.__setattr__(
            self,
            "evidence",
            evidence,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "candidate_id": (
                self.candidate_id
            ),
            "dimension": (
                self.dimension.value
            ),
            "label": self.label,
            "origin": self.origin.value,
            "producer_id": (
                self.producer_id
            ),
            "confidence_basis_points": (
                self.confidence_basis_points
            ),
            "evidence": [
                item.to_dict()
                for item in self.evidence
            ],
        }


def create_classification_candidate(
    *,
    dimension: CandidateDimension,
    label: str,
    origin: CandidateOrigin,
    producer_id: str,
    confidence_basis_points: int,
    evidence: Iterable[
        FeatureEvidence
    ],
) -> ClassificationCandidate:
    """Create one deterministic candidate."""

    if not isinstance(
        dimension,
        CandidateDimension,
    ):
        raise _error(
            "invalid_candidate_dimension",
            "dimension",
            (
                "Dimension must be "
                "CandidateDimension."
            ),
        )

    if not isinstance(
        origin,
        CandidateOrigin,
    ):
        raise _error(
            "invalid_candidate_origin",
            "origin",
            (
                "Origin must be "
                "CandidateOrigin."
            ),
        )

    normalized_label = (
        _normalized_label(label)
    )
    normalized_producer = (
        _normalized_producer_id(
            producer_id
        )
    )

    if (
        isinstance(
            confidence_basis_points,
            bool,
        )
        or not isinstance(
            confidence_basis_points,
            int,
        )
    ):
        raise _error(
            "invalid_confidence_type",
            "confidence_basis_points",
            (
                "Confidence must be "
                "an integer."
            ),
        )

    if not (
        0
        <= confidence_basis_points
        <= CONFIDENCE_SCALE_BASIS_POINTS
    ):
        raise _error(
            "confidence_out_of_range",
            "confidence_basis_points",
            (
                "Confidence must be "
                "between 0 and 10000."
            ),
        )

    normalized_evidence = (
        _normalize_evidence(evidence)
    )

    candidate_id = (
        _expected_candidate_id(
            dimension=dimension,
            label=normalized_label,
            origin=origin,
            producer_id=(
                normalized_producer
            ),
            confidence_basis_points=(
                confidence_basis_points
            ),
            evidence=(
                normalized_evidence
            ),
        )
    )

    return ClassificationCandidate(
        candidate_id=candidate_id,
        dimension=dimension,
        label=normalized_label,
        origin=origin,
        producer_id=normalized_producer,
        confidence_basis_points=(
            confidence_basis_points
        ),
        evidence=normalized_evidence,
    )


def _normalize_candidates(
    values: Iterable[
        ClassificationCandidate
    ],
    *,
    allow_empty: bool,
) -> tuple[
    ClassificationCandidate,
    ...,
]:
    if isinstance(values, (str, bytes)):
        raise _error(
            "invalid_candidate_collection",
            "candidates",
            (
                "Candidates must be "
                "an iterable."
            ),
        )

    try:
        candidates = tuple(values)
    except TypeError as error:
        raise _error(
            "invalid_candidate_collection",
            "candidates",
            (
                "Candidates must be "
                "iterable."
            ),
        ) from error

    if not candidates and not allow_empty:
        raise _error(
            (
                "classification_candidates_"
                "required"
            ),
            "candidates",
            (
                "At least one candidate is "
                "required unless clarification "
                "is recommended."
            ),
        )

    for candidate in candidates:
        if not isinstance(
            candidate,
            ClassificationCandidate,
        ):
            raise _error(
                (
                    "invalid_classification_"
                    "candidate"
                ),
                "candidates",
                (
                    "Every item must be "
                    "ClassificationCandidate."
                ),
            )

    ordered = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.candidate_id
            ),
        )
    )

    if (
        len(
            {
                item.candidate_id
                for item in ordered
            }
        )
        != len(ordered)
    ):
        raise _error(
            (
                "duplicate_classification_"
                "candidate"
            ),
            "candidates",
            (
                "Candidate IDs must be "
                "unique."
            ),
        )

    return ordered


def _set_body(
    *,
    input_event: ContractReference,
    candidates: tuple[
        ClassificationCandidate,
        ...,
    ],
    uncertainty_codes: tuple[
        str,
        ...,
    ],
    clarification_recommended: bool,
    clarification_reason_codes: tuple[
        str,
        ...,
    ],
) -> dict[str, Any]:
    return {
        "input_event": (
            input_event.to_dict()
        ),
        "candidates": [
            candidate.to_dict()
            for candidate in candidates
        ],
        "uncertainty_codes": list(
            uncertainty_codes
        ),
        "clarification_recommended": (
            clarification_recommended
        ),
        "clarification_reason_codes": list(
            clarification_reason_codes
        ),
    }


@dataclass(frozen=True, slots=True)
class ClassificationCandidateSet:
    """Immutable set of unselected candidates."""

    metadata: ContractMetadata
    input_event: ContractReference
    candidates: tuple[
        ClassificationCandidate,
        ...,
    ]
    uncertainty_codes: tuple[str, ...]
    clarification_recommended: bool
    clarification_reason_codes: tuple[
        str,
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
            self.input_event,
            ContractReference,
        ):
            raise _error(
                (
                    "invalid_input_event_"
                    "reference"
                ),
                "input_event",
                (
                    "Input event must be "
                    "ContractReference."
                ),
            )

        if (
            self.input_event.contract_type
            != "InputEvent"
        ):
            raise _error(
                (
                    "input_event_reference_"
                    "type_mismatch"
                ),
                "input_event",
                (
                    "Source reference must "
                    "identify InputEvent."
                ),
            )

        if not isinstance(
            self.clarification_recommended,
            bool,
        ):
            raise _error(
                "invalid_clarification_flag",
                "clarification_recommended",
                (
                    "Clarification "
                    "recommendation must "
                    "be boolean."
                ),
            )

        if not isinstance(
            self.candidates,
            tuple,
        ):
            raise _error(
                "candidates_not_immutable",
                "candidates",
                (
                    "Stored candidates must "
                    "be a tuple."
                ),
            )

        candidates = _normalize_candidates(
            self.candidates,
            allow_empty=(
                self
                .clarification_recommended
            ),
        )

        if candidates != self.candidates:
            raise _error(
                "candidates_not_canonical",
                "candidates",
                (
                    "Stored candidates must "
                    "use canonical ID order."
                ),
            )

        if not isinstance(
            self.uncertainty_codes,
            tuple,
        ):
            raise _error(
                (
                    "uncertainty_not_"
                    "immutable"
                ),
                "uncertainty_codes",
                (
                    "Uncertainty codes must "
                    "be a tuple."
                ),
            )

        if not isinstance(
            self.clarification_reason_codes,
            tuple,
        ):
            raise _error(
                (
                    "clarification_reasons_"
                    "not_immutable"
                ),
                "clarification_reason_codes",
                (
                    "Clarification reason "
                    "codes must be a tuple."
                ),
            )

        uncertainty_codes = (
            _normalize_codes(
                self.uncertainty_codes,
                field="uncertainty_codes",
            )
        )
        clarification_reason_codes = (
            _normalize_codes(
                (
                    self
                    .clarification_reason_codes
                ),
                field=(
                    "clarification_reason_codes"
                ),
            )
        )

        if (
            uncertainty_codes
            != self.uncertainty_codes
        ):
            raise _error(
                (
                    "uncertainty_codes_"
                    "not_canonical"
                ),
                "uncertainty_codes",
                (
                    "Uncertainty codes must "
                    "use canonical order."
                ),
            )

        if (
            clarification_reason_codes
            != self
            .clarification_reason_codes
        ):
            raise _error(
                (
                    "clarification_reason_"
                    "codes_not_canonical"
                ),
                (
                    "clarification_reason_codes"
                ),
                (
                    "Clarification reason "
                    "codes must use canonical "
                    "order."
                ),
            )

        if (
            self.clarification_recommended
            and not clarification_reason_codes
        ):
            raise _error(
                (
                    "clarification_reason_"
                    "required"
                ),
                (
                    "clarification_reason_codes"
                ),
                (
                    "Clarification "
                    "recommendation requires "
                    "at least one reason."
                ),
            )

        if (
            not self
            .clarification_recommended
            and clarification_reason_codes
        ):
            raise _error(
                (
                    "clarification_reason_"
                    "without_recommendation"
                ),
                (
                    "clarification_reason_codes"
                ),
                (
                    "Clarification reasons "
                    "require a recommendation."
                ),
            )

        if (
            self.metadata.contract_type
            != (
                CLASSIFICATION_CANDIDATE_SET_CONTRACT_TYPE
            )
        ):
            raise _error(
                (
                    "classification_candidate_"
                    "set_type_mismatch"
                ),
                "contract_type",
                (
                    "Metadata contract type "
                    "is incorrect."
                ),
            )

        if (
            self.metadata.schema_version
            != (
                CLASSIFICATION_CANDIDATE_SET_SCHEMA_VERSION
            )
        ):
            raise _error(
                (
                    "classification_candidate_"
                    "set_schema_mismatch"
                ),
                "schema_version",
                (
                    "Candidate set must use "
                    "schema version 1.0.0."
                ),
            )

        if (
            self.metadata.authority_status
            != AuthorityStatus.NONE
        ):
            raise _error(
                (
                    "classification_candidate_"
                    "set_authority_forbidden"
                ),
                "authority_status",
                (
                    "Candidate sets cannot "
                    "carry authority."
                ),
            )

        if self.metadata.declared_effects:
            raise _error(
                (
                    "classification_candidate_"
                    "set_effects_forbidden"
                ),
                "declared_effects",
                (
                    "Candidate sets cannot "
                    "declare side effects."
                ),
            )

        if (
            self.metadata.parent is not None
            and (
                self.metadata
                .parent
                .contract_type
                != (
                    CLASSIFICATION_CANDIDATE_SET_CONTRACT_TYPE
                )
            )
        ):
            raise _error(
                (
                    "classification_candidate_"
                    "set_parent_type_mismatch"
                ),
                "parent",
                (
                    "A parent must reference "
                    "ClassificationCandidateSet."
                ),
            )

        verify_contract_metadata(
            self.metadata,
            self.body(),
        )

    def body(
        self,
    ) -> dict[str, Any]:
        return _set_body(
            input_event=self.input_event,
            candidates=self.candidates,
            uncertainty_codes=(
                self.uncertainty_codes
            ),
            clarification_recommended=(
                self
                .clarification_recommended
            ),
            clarification_reason_codes=(
                self
                .clarification_reason_codes
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
                (
                    "ClassificationCandidateSet "
                    "did not serialize to a "
                    "mapping."
                )
            )

        return value


def _resolve_pointer(
    body: Any,
    pointer: str,
) -> Any:
    current = body

    for segment in _pointer_segments(
        pointer
    ):
        if isinstance(
            current,
            Mapping,
        ):
            if segment not in current:
                raise _error(
                    (
                        "source_pointer_"
                        "not_found"
                    ),
                    "source_pointer",
                    (
                        "Source pointer does "
                        "not resolve."
                    ),
                )

            current = current[segment]
            continue

        if isinstance(current, list):
            if (
                not segment.isdigit()
                or (
                    len(segment) > 1
                    and segment.startswith(
                        "0"
                    )
                )
            ):
                raise _error(
                    (
                        "invalid_list_"
                        "pointer_index"
                    ),
                    "source_pointer",
                    (
                        "List pointer index "
                        "is not canonical."
                    ),
                )

            index = int(segment)

            if index >= len(current):
                raise _error(
                    (
                        "source_pointer_"
                        "not_found"
                    ),
                    "source_pointer",
                    (
                        "Source pointer list "
                        "index is out of range."
                    ),
                )

            current = current[index]
            continue

        raise _error(
            "source_pointer_not_found",
            "source_pointer",
            (
                "Source pointer traverses "
                "a scalar value."
            ),
        )

    return current


def _verify_feature_evidence(
    evidence: FeatureEvidence,
    input_event: InputEvent,
) -> None:
    resolved = _resolve_pointer(
        input_event.body(),
        evidence.source_pointer,
    )
    observed = thaw_canonical(
        evidence.observed_value
    )

    if evidence.span_start is None:
        if (
            freeze_canonical(resolved)
            != evidence.observed_value
        ):
            raise ContractIntegrityError(
                "feature_evidence_mismatch",
                "observed_value",
                (
                    "Observed value does not "
                    "match the InputEvent "
                    "source."
                ),
            )

        return

    if (
        not isinstance(resolved, str)
        or not isinstance(
            observed,
            str,
        )
    ):
        raise _error(
            "text_span_requires_text",
            "span",
            (
                "Text spans may reference "
                "only text values."
            ),
        )

    assert evidence.span_end is not None

    if evidence.span_end > len(resolved):
        raise _error(
            "text_span_out_of_range",
            "span",
            (
                "Text span exceeds the "
                "source value."
            ),
        )

    if (
        resolved[
            evidence.span_start
            : evidence.span_end
        ]
        != observed
    ):
        raise ContractIntegrityError(
            "feature_evidence_mismatch",
            "observed_value",
            (
                "Text span does not match "
                "observed evidence."
            ),
        )


def create_classification_candidate_set(
    *,
    input_event: InputEvent,
    candidates: Iterable[
        ClassificationCandidate
    ],
    uncertainty_codes: Iterable[
        str
    ] = (),
    clarification_recommended: bool = False,
    clarification_reason_codes: Iterable[
        str
    ] = (),
    created_at: datetime,
) -> ClassificationCandidateSet:
    """Create an authority-neutral set."""

    verify_input_event(input_event)

    if not isinstance(
        clarification_recommended,
        bool,
    ):
        raise _error(
            "invalid_clarification_flag",
            "clarification_recommended",
            (
                "Clarification "
                "recommendation must be "
                "boolean."
            ),
        )

    normalized_candidates = (
        _normalize_candidates(
            candidates,
            allow_empty=(
                clarification_recommended
            ),
        )
    )
    normalized_uncertainty = (
        _normalize_codes(
            uncertainty_codes,
            field="uncertainty_codes",
        )
    )
    normalized_reasons = (
        _normalize_codes(
            clarification_reason_codes,
            field=(
                "clarification_reason_codes"
            ),
        )
    )
    input_reference = (
        input_event.metadata.to_reference()
    )

    body = _set_body(
        input_event=input_reference,
        candidates=normalized_candidates,
        uncertainty_codes=(
            normalized_uncertainty
        ),
        clarification_recommended=(
            clarification_recommended
        ),
        clarification_reason_codes=(
            normalized_reasons
        ),
    )

    metadata = create_contract_metadata(
        schema_version=(
            CLASSIFICATION_CANDIDATE_SET_SCHEMA_VERSION
        ),
        contract_type=(
            CLASSIFICATION_CANDIDATE_SET_CONTRACT_TYPE
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

    result = ClassificationCandidateSet(
        metadata=metadata,
        input_event=input_reference,
        candidates=normalized_candidates,
        uncertainty_codes=(
            normalized_uncertainty
        ),
        clarification_recommended=(
            clarification_recommended
        ),
        clarification_reason_codes=(
            normalized_reasons
        ),
    )

    verify_classification_candidate_set(
        result,
        input_event=input_event,
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


def _feature_evidence_from_dict(
    value: object,
) -> FeatureEvidence:
    record = _exact_mapping(
        value,
        _EVIDENCE_KEYS,
        field="evidence",
    )

    return FeatureEvidence(
        evidence_id=record["evidence_id"],
        source_pointer=(
            record["source_pointer"]
        ),
        feature_name=(
            record["feature_name"]
        ),
        observed_value=freeze_canonical(
            record["observed_value"]
        ),
        span_start=record["span_start"],
        span_end=record["span_end"],
    )


def _classification_candidate_from_dict(
    value: object,
) -> ClassificationCandidate:
    record = _exact_mapping(
        value,
        _CANDIDATE_KEYS,
        field="candidate",
    )
    evidence_value = record["evidence"]

    if not isinstance(
        evidence_value,
        (list, tuple),
    ):
        raise _error(
            "invalid_evidence_collection",
            "evidence",
            (
                "Evidence must be a "
                "sequence."
            ),
        )

    try:
        dimension = CandidateDimension(
            record["dimension"]
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise _error(
            "invalid_candidate_dimension",
            "dimension",
            (
                "Candidate dimension "
                "is unknown."
            ),
        ) from error

    try:
        origin = CandidateOrigin(
            record["origin"]
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise _error(
            "invalid_candidate_origin",
            "origin",
            (
                "Candidate origin "
                "is unknown."
            ),
        ) from error

    return ClassificationCandidate(
        candidate_id=record["candidate_id"],
        dimension=dimension,
        label=record["label"],
        origin=origin,
        producer_id=record["producer_id"],
        confidence_basis_points=(
            record[
                "confidence_basis_points"
            ]
        ),
        evidence=tuple(
            _feature_evidence_from_dict(
                item
            )
            for item in evidence_value
        ),
    )


def classification_candidate_set_from_dict(
    value: object,
    *,
    input_event: InputEvent,
) -> ClassificationCandidateSet:
    """Decode and verify an exact set."""

    top = _exact_mapping(
        value,
        _TOP_LEVEL_KEYS,
        field=(
            "classification_candidate_set"
        ),
    )
    body = _exact_mapping(
        top["body"],
        _BODY_KEYS,
        field="body",
    )

    candidates_value = body[
        "candidates"
    ]
    uncertainty_value = body[
        "uncertainty_codes"
    ]
    reasons_value = body[
        "clarification_reason_codes"
    ]

    if not isinstance(
        candidates_value,
        (list, tuple),
    ):
        raise _error(
            "invalid_candidate_collection",
            "candidates",
            (
                "Candidates must be "
                "a sequence."
            ),
        )

    if not isinstance(
        uncertainty_value,
        (list, tuple),
    ):
        raise _error(
            "invalid_code_collection",
            "uncertainty_codes",
            (
                "Uncertainty codes must "
                "be a sequence."
            ),
        )

    if not isinstance(
        reasons_value,
        (list, tuple),
    ):
        raise _error(
            "invalid_code_collection",
            (
                "clarification_reason_codes"
            ),
            (
                "Clarification reasons "
                "must be a sequence."
            ),
        )

    result = ClassificationCandidateSet(
        metadata=(
            contract_metadata_from_dict(
                top["metadata"]
            )
        ),
        input_event=(
            contract_reference_from_dict(
                body["input_event"]
            )
        ),
        candidates=tuple(
            _classification_candidate_from_dict(
                item
            )
            for item
            in candidates_value
        ),
        uncertainty_codes=tuple(
            uncertainty_value
        ),
        clarification_recommended=(
            body[
                "clarification_recommended"
            ]
        ),
        clarification_reason_codes=tuple(
            reasons_value
        ),
    )

    verify_classification_candidate_set(
        result,
        input_event=input_event,
    )

    return result


def verify_classification_candidate_set(
    candidate_set: ClassificationCandidateSet,
    *,
    input_event: InputEvent,
) -> None:
    """Verify body and source evidence."""

    if not isinstance(
        candidate_set,
        ClassificationCandidateSet,
    ):
        raise _error(
            (
                "invalid_classification_"
                "candidate_set_type"
            ),
            "candidate_set",
            (
                "Value must be "
                "ClassificationCandidateSet."
            ),
        )

    verify_input_event(input_event)

    if (
        candidate_set.input_event
        != input_event
        .metadata
        .to_reference()
    ):
        raise ContractIntegrityError(
            (
                "classification_input_"
                "event_mismatch"
            ),
            "input_event",
            (
                "Candidate set does not "
                "reference the supplied "
                "InputEvent."
            ),
        )

    verify_contract_metadata(
        candidate_set.metadata,
        candidate_set.body(),
    )

    for candidate in (
        candidate_set.candidates
    ):
        for evidence in candidate.evidence:
            _verify_feature_evidence(
                evidence,
                input_event,
            )


__all__ = (
    "CLASSIFICATION_CANDIDATE_ID_NAMESPACE",
    "CLASSIFICATION_CANDIDATE_SET_CONTRACT_TYPE",
    "CLASSIFICATION_CANDIDATE_SET_SCHEMA_VERSION",
    "CONFIDENCE_SCALE_BASIS_POINTS",
    "FEATURE_EVIDENCE_ID_NAMESPACE",
    "CandidateDimension",
    "CandidateOrigin",
    "ClassificationCandidate",
    "ClassificationCandidateSet",
    "FeatureEvidence",
    "classification_candidate_set_from_dict",
    "create_classification_candidate",
    "create_classification_candidate_set",
    "create_feature_evidence",
    "verify_classification_candidate_set",
)
