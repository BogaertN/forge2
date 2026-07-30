"""Immutable, evidence-bound RequestContract.

This module records an already-supported request
interpretation. It does not implement automatic
candidate selection, conflict resolution, planning,
tool selection, authorization, or execution.
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
from .classification_candidate import (
    CandidateDimension,
    ClassificationCandidate,
    ClassificationCandidateSet,
    verify_classification_candidate_set,
)
from .codec import (
    contract_metadata_from_dict,
    contract_metadata_to_dict,
    contract_reference_from_dict,
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


REQUEST_CONTRACT_TYPE: Final[str] = (
    "RequestContract"
)
REQUEST_CONTRACT_SCHEMA_VERSION: Final[
    SchemaVersion
] = SchemaVersion(1, 0, 0)
CANDIDATE_SELECTION_ID_NAMESPACE: Final[
    str
] = "aiweb.candidate-selection"
REQUEST_STATEMENT_ID_NAMESPACE: Final[
    str
] = "aiweb.request-statement"

_SELECTION_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.candidate-selection:sha256:"
    r"[0-9a-f]{64}$"
)
_STATEMENT_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.request-statement:sha256:"
    r"[0-9a-f]{64}$"
)
_CANDIDATE_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.classification-candidate:sha256:"
    r"[0-9a-f]{64}$"
)
_EVIDENCE_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.feature-evidence:sha256:"
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
        "classification_candidate_set",
        "producer_id",
        "selected_candidates",
        "goals",
        "constraints",
        "desired_result",
        "uncertainty_codes",
    }
)
_SELECTION_KEYS: Final[
    frozenset[str]
] = frozenset(
    {
        "selection_id",
        "candidate_id",
        "dimension",
        "label",
        "basis_codes",
    }
)
_STATEMENT_KEYS: Final[
    frozenset[str]
] = frozenset(
    {
        "statement_id",
        "kind",
        "code",
        "text",
        "evidence_ids",
    }
)

_REQUIRED_DIMENSIONS: Final[
    frozenset[CandidateDimension]
] = frozenset(
    {
        CandidateDimension.REQUEST_KIND,
        CandidateDimension.EXPECTED_RESULT,
        CandidateDimension.SIDE_EFFECT_CLASS,
    }
)


class RequestStatementKind(StrEnum):
    """Evidence-bound RequestContract statements."""

    GOAL = "goal"
    CONSTRAINT = "constraint"
    DESIRED_RESULT = "desired_result"


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


def _normalize_evidence_ids(
    values: Iterable[str],
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise _error(
            "invalid_evidence_id_collection",
            "evidence_ids",
            (
                "Evidence IDs must be an "
                "iterable of strings."
            ),
        )

    try:
        observed = tuple(values)
    except TypeError as error:
        raise _error(
            "invalid_evidence_id_collection",
            "evidence_ids",
            "Evidence IDs must be iterable.",
        ) from error

    if not observed:
        raise _error(
            "statement_evidence_required",
            "evidence_ids",
            (
                "Every request statement must "
                "carry source evidence."
            ),
        )

    for value in observed:
        if (
            not isinstance(value, str)
            or not _EVIDENCE_ID_PATTERN.fullmatch(
                value
            )
        ):
            raise _error(
                "invalid_feature_evidence_id",
                "evidence_ids",
                (
                    "Evidence IDs must use the "
                    "approved SHA-256 form."
                ),
            )

    ordered = tuple(sorted(observed))

    if len(set(ordered)) != len(ordered):
        raise _error(
            "duplicate_feature_evidence_id",
            "evidence_ids",
            "Evidence IDs must be unique.",
        )

    return ordered


def _selection_material(
    *,
    candidate_id: str,
    dimension: CandidateDimension,
    label: str,
    basis_codes: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "basis_codes": list(basis_codes),
        "candidate_id": candidate_id,
        "dimension": dimension.value,
        "label": label,
    }


def _expected_selection_id(
    *,
    candidate_id: str,
    dimension: CandidateDimension,
    label: str,
    basis_codes: tuple[str, ...],
) -> str:
    return stable_identifier(
        CANDIDATE_SELECTION_ID_NAMESPACE,
        _selection_material(
            candidate_id=candidate_id,
            dimension=dimension,
            label=label,
            basis_codes=basis_codes,
        ),
    )


@dataclass(frozen=True, slots=True)
class CandidateSelection:
    """Recorded selection of one existing candidate."""

    selection_id: str
    candidate_id: str
    dimension: CandidateDimension
    label: str
    basis_codes: tuple[str, ...]

    def __post_init__(self) -> None:
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
                "invalid_candidate_id",
                "candidate_id",
                (
                    "Candidate ID must use the "
                    "approved SHA-256 form."
                ),
            )

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

        label = _normalized_text(
            self.label,
            field="label",
            maximum_length=256,
        )

        if not isinstance(
            self.basis_codes,
            tuple,
        ):
            raise _error(
                "selection_basis_not_immutable",
                "basis_codes",
                (
                    "Stored selection basis "
                    "codes must be a tuple."
                ),
            )

        basis_codes = _normalize_codes(
            self.basis_codes,
            field="basis_codes",
            allow_empty=False,
        )

        if basis_codes != self.basis_codes:
            raise _error(
                "selection_basis_not_canonical",
                "basis_codes",
                (
                    "Selection basis codes must "
                    "use canonical order."
                ),
            )

        if (
            not isinstance(
                self.selection_id,
                str,
            )
            or not _SELECTION_ID_PATTERN.fullmatch(
                self.selection_id
            )
        ):
            raise _error(
                "invalid_candidate_selection_id",
                "selection_id",
                (
                    "Selection ID must use the "
                    "approved SHA-256 form."
                ),
            )

        expected_id = _expected_selection_id(
            candidate_id=self.candidate_id,
            dimension=self.dimension,
            label=label,
            basis_codes=basis_codes,
        )

        if self.selection_id != expected_id:
            raise ContractIntegrityError(
                "candidate_selection_id_mismatch",
                "selection_id",
                (
                    "Selection ID does not "
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
            "basis_codes",
            basis_codes,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "selection_id": self.selection_id,
            "candidate_id": self.candidate_id,
            "dimension": self.dimension.value,
            "label": self.label,
            "basis_codes": list(
                self.basis_codes
            ),
        }


def create_candidate_selection(
    *,
    candidate: ClassificationCandidate,
    basis_codes: Iterable[str],
) -> CandidateSelection:
    """Record selection without selecting automatically."""

    if not isinstance(
        candidate,
        ClassificationCandidate,
    ):
        raise _error(
            "invalid_classification_candidate",
            "candidate",
            (
                "Candidate must be "
                "ClassificationCandidate."
            ),
        )

    normalized_basis = _normalize_codes(
        basis_codes,
        field="basis_codes",
        allow_empty=False,
    )

    selection_id = _expected_selection_id(
        candidate_id=candidate.candidate_id,
        dimension=candidate.dimension,
        label=candidate.label,
        basis_codes=normalized_basis,
    )

    return CandidateSelection(
        selection_id=selection_id,
        candidate_id=candidate.candidate_id,
        dimension=candidate.dimension,
        label=candidate.label,
        basis_codes=normalized_basis,
    )


def _statement_material(
    *,
    kind: RequestStatementKind,
    code: str,
    text: str,
    evidence_ids: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "code": code,
        "evidence_ids": list(evidence_ids),
        "kind": kind.value,
        "text": text,
    }


def _expected_statement_id(
    *,
    kind: RequestStatementKind,
    code: str,
    text: str,
    evidence_ids: tuple[str, ...],
) -> str:
    return stable_identifier(
        REQUEST_STATEMENT_ID_NAMESPACE,
        _statement_material(
            kind=kind,
            code=code,
            text=text,
            evidence_ids=evidence_ids,
        ),
    )


@dataclass(frozen=True, slots=True)
class RequestStatement:
    """One evidence-bound goal, constraint, or result."""

    statement_id: str
    kind: RequestStatementKind
    code: str
    text: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.kind,
            RequestStatementKind,
        ):
            raise _error(
                "invalid_request_statement_kind",
                "kind",
                (
                    "Kind must be "
                    "RequestStatementKind."
                ),
            )

        code = _normalized_code(
            self.code,
            field="code",
        )
        text = _normalized_text(
            self.text,
            field="text",
            maximum_length=2048,
        )

        if not isinstance(
            self.evidence_ids,
            tuple,
        ):
            raise _error(
                "statement_evidence_not_immutable",
                "evidence_ids",
                (
                    "Stored evidence IDs must "
                    "be a tuple."
                ),
            )

        evidence_ids = (
            _normalize_evidence_ids(
                self.evidence_ids
            )
        )

        if evidence_ids != self.evidence_ids:
            raise _error(
                "statement_evidence_not_canonical",
                "evidence_ids",
                (
                    "Evidence IDs must use "
                    "canonical order."
                ),
            )

        if (
            not isinstance(
                self.statement_id,
                str,
            )
            or not _STATEMENT_ID_PATTERN.fullmatch(
                self.statement_id
            )
        ):
            raise _error(
                "invalid_request_statement_id",
                "statement_id",
                (
                    "Statement ID must use the "
                    "approved SHA-256 form."
                ),
            )

        expected_id = _expected_statement_id(
            kind=self.kind,
            code=code,
            text=text,
            evidence_ids=evidence_ids,
        )

        if self.statement_id != expected_id:
            raise ContractIntegrityError(
                "request_statement_id_mismatch",
                "statement_id",
                (
                    "Statement ID does not "
                    "match its material."
                ),
            )

        object.__setattr__(
            self,
            "code",
            code,
        )
        object.__setattr__(
            self,
            "text",
            text,
        )
        object.__setattr__(
            self,
            "evidence_ids",
            evidence_ids,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "statement_id": self.statement_id,
            "kind": self.kind.value,
            "code": self.code,
            "text": self.text,
            "evidence_ids": list(
                self.evidence_ids
            ),
        }


def create_request_statement(
    *,
    kind: RequestStatementKind,
    code: str,
    text: str,
    evidence_ids: Iterable[str],
) -> RequestStatement:
    """Create one deterministic request statement."""

    if not isinstance(
        kind,
        RequestStatementKind,
    ):
        raise _error(
            "invalid_request_statement_kind",
            "kind",
            (
                "Kind must be "
                "RequestStatementKind."
            ),
        )

    normalized_code = _normalized_code(
        code,
        field="code",
    )
    normalized_text = _normalized_text(
        text,
        field="text",
        maximum_length=2048,
    )
    normalized_evidence = (
        _normalize_evidence_ids(
            evidence_ids
        )
    )

    statement_id = _expected_statement_id(
        kind=kind,
        code=normalized_code,
        text=normalized_text,
        evidence_ids=normalized_evidence,
    )

    return RequestStatement(
        statement_id=statement_id,
        kind=kind,
        code=normalized_code,
        text=normalized_text,
        evidence_ids=normalized_evidence,
    )


def _normalize_selections(
    values: Iterable[CandidateSelection],
) -> tuple[CandidateSelection, ...]:
    if isinstance(values, (str, bytes)):
        raise _error(
            "invalid_selection_collection",
            "selected_candidates",
            (
                "Selections must be an "
                "iterable."
            ),
        )

    try:
        selections = tuple(values)
    except TypeError as error:
        raise _error(
            "invalid_selection_collection",
            "selected_candidates",
            "Selections must be iterable.",
        ) from error

    if not selections:
        raise _error(
            "candidate_selection_required",
            "selected_candidates",
            (
                "At least one selected "
                "candidate is required."
            ),
        )

    for selection in selections:
        if not isinstance(
            selection,
            CandidateSelection,
        ):
            raise _error(
                "invalid_candidate_selection",
                "selected_candidates",
                (
                    "Every selection must be "
                    "CandidateSelection."
                ),
            )

    ordered = tuple(
        sorted(
            selections,
            key=lambda item: item.selection_id,
        )
    )

    if (
        len(
            {
                item.selection_id
                for item in ordered
            }
        )
        != len(ordered)
    ):
        raise _error(
            "duplicate_candidate_selection",
            "selected_candidates",
            (
                "Selection IDs must be "
                "unique."
            ),
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
            "duplicate_selected_candidate",
            "selected_candidates",
            (
                "Candidate IDs must be "
                "selected at most once."
            ),
        )

    if (
        len(
            {
                item.dimension
                for item in ordered
            }
        )
        != len(ordered)
    ):
        raise _error(
            "duplicate_selected_dimension",
            "selected_candidates",
            (
                "Only one candidate may be "
                "selected per dimension."
            ),
        )

    return ordered


def _normalize_statements(
    values: Iterable[RequestStatement],
    *,
    expected_kind: RequestStatementKind,
    field: str,
    allow_empty: bool,
) -> tuple[RequestStatement, ...]:
    if isinstance(values, (str, bytes)):
        raise _error(
            "invalid_statement_collection",
            field,
            (
                "Statements must be an "
                "iterable."
            ),
        )

    try:
        statements = tuple(values)
    except TypeError as error:
        raise _error(
            "invalid_statement_collection",
            field,
            "Statements must be iterable.",
        ) from error

    if not statements and not allow_empty:
        raise _error(
            "request_statement_required",
            field,
            (
                "At least one statement "
                "is required."
            ),
        )

    for statement in statements:
        if not isinstance(
            statement,
            RequestStatement,
        ):
            raise _error(
                "invalid_request_statement",
                field,
                (
                    "Every item must be "
                    "RequestStatement."
                ),
            )

        if statement.kind is not expected_kind:
            raise _error(
                "request_statement_kind_mismatch",
                field,
                (
                    "Statement kind does not "
                    "match its body field."
                ),
            )

    ordered = tuple(
        sorted(
            statements,
            key=lambda item: item.statement_id,
        )
    )

    if (
        len(
            {
                item.statement_id
                for item in ordered
            }
        )
        != len(ordered)
    ):
        raise _error(
            "duplicate_request_statement",
            field,
            (
                "Statement IDs must be "
                "unique."
            ),
        )

    if (
        len(
            {
                item.code
                for item in ordered
            }
        )
        != len(ordered)
    ):
        raise _error(
            "duplicate_request_statement_code",
            field,
            (
                "Statement codes must be "
                "unique within the field."
            ),
        )

    return ordered


def _request_body(
    *,
    input_event: ContractReference,
    classification_candidate_set: (
        ContractReference
    ),
    producer_id: str,
    selected_candidates: tuple[
        CandidateSelection,
        ...,
    ],
    goals: tuple[
        RequestStatement,
        ...,
    ],
    constraints: tuple[
        RequestStatement,
        ...,
    ],
    desired_result: RequestStatement,
    uncertainty_codes: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "input_event": input_event.to_dict(),
        "classification_candidate_set": (
            classification_candidate_set
            .to_dict()
        ),
        "producer_id": producer_id,
        "selected_candidates": [
            item.to_dict()
            for item in selected_candidates
        ],
        "goals": [
            item.to_dict()
            for item in goals
        ],
        "constraints": [
            item.to_dict()
            for item in constraints
        ],
        "desired_result": (
            desired_result.to_dict()
        ),
        "uncertainty_codes": list(
            uncertainty_codes
        ),
    }


@dataclass(frozen=True, slots=True)
class RequestContract:
    """One selected, authority-neutral request meaning."""

    metadata: ContractMetadata
    input_event: ContractReference
    classification_candidate_set: (
        ContractReference
    )
    producer_id: str
    selected_candidates: tuple[
        CandidateSelection,
        ...,
    ]
    goals: tuple[
        RequestStatement,
        ...,
    ]
    constraints: tuple[
        RequestStatement,
        ...,
    ]
    desired_result: RequestStatement
    uncertainty_codes: tuple[str, ...]

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
                "invalid_input_event_reference",
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
                "input_event_reference_type_mismatch",
                "input_event",
                (
                    "Source reference must "
                    "identify InputEvent."
                ),
            )

        if not isinstance(
            self.classification_candidate_set,
            ContractReference,
        ):
            raise _error(
                (
                    "invalid_classification_"
                    "candidate_set_reference"
                ),
                "classification_candidate_set",
                (
                    "Candidate set must be "
                    "ContractReference."
                ),
            )

        if (
            self
            .classification_candidate_set
            .contract_type
            != "ClassificationCandidateSet"
        ):
            raise _error(
                (
                    "classification_candidate_"
                    "set_reference_type_mismatch"
                ),
                "classification_candidate_set",
                (
                    "Source reference must "
                    "identify "
                    "ClassificationCandidateSet."
                ),
            )

        producer_id = (
            _normalized_producer_id(
                self.producer_id
            )
        )

        if not isinstance(
            self.selected_candidates,
            tuple,
        ):
            raise _error(
                "selections_not_immutable",
                "selected_candidates",
                (
                    "Stored selections must "
                    "be a tuple."
                ),
            )

        selections = _normalize_selections(
            self.selected_candidates
        )

        if selections != self.selected_candidates:
            raise _error(
                "selections_not_canonical",
                "selected_candidates",
                (
                    "Selections must use "
                    "canonical ID order."
                ),
            )

        observed_dimensions = frozenset(
            item.dimension
            for item in selections
        )
        missing_dimensions = (
            _REQUIRED_DIMENSIONS
            - observed_dimensions
        )

        if missing_dimensions:
            raise _error(
                "required_candidate_dimension_missing",
                "selected_candidates",
                (
                    "Missing required dimensions: "
                    + ", ".join(
                        sorted(
                            item.value
                            for item
                            in missing_dimensions
                        )
                    )
                ),
            )

        if not isinstance(
            self.goals,
            tuple,
        ):
            raise _error(
                "goals_not_immutable",
                "goals",
                (
                    "Stored goals must be "
                    "a tuple."
                ),
            )

        goals = _normalize_statements(
            self.goals,
            expected_kind=(
                RequestStatementKind.GOAL
            ),
            field="goals",
            allow_empty=False,
        )

        if goals != self.goals:
            raise _error(
                "goals_not_canonical",
                "goals",
                (
                    "Goals must use canonical "
                    "statement-ID order."
                ),
            )

        if not isinstance(
            self.constraints,
            tuple,
        ):
            raise _error(
                "constraints_not_immutable",
                "constraints",
                (
                    "Stored constraints must "
                    "be a tuple."
                ),
            )

        constraints = _normalize_statements(
            self.constraints,
            expected_kind=(
                RequestStatementKind.CONSTRAINT
            ),
            field="constraints",
            allow_empty=True,
        )

        if constraints != self.constraints:
            raise _error(
                "constraints_not_canonical",
                "constraints",
                (
                    "Constraints must use "
                    "canonical statement-ID "
                    "order."
                ),
            )

        if not isinstance(
            self.desired_result,
            RequestStatement,
        ):
            raise _error(
                "invalid_desired_result",
                "desired_result",
                (
                    "Desired result must be "
                    "RequestStatement."
                ),
            )

        if (
            self.desired_result.kind
            is not (
                RequestStatementKind
                .DESIRED_RESULT
            )
        ):
            raise _error(
                "desired_result_kind_mismatch",
                "desired_result",
                (
                    "Desired result statement "
                    "must use desired_result "
                    "kind."
                ),
            )

        if not isinstance(
            self.uncertainty_codes,
            tuple,
        ):
            raise _error(
                "uncertainty_not_immutable",
                "uncertainty_codes",
                (
                    "Stored uncertainty codes "
                    "must be a tuple."
                ),
            )

        uncertainty_codes = (
            _normalize_codes(
                self.uncertainty_codes,
                field="uncertainty_codes",
                allow_empty=True,
            )
        )

        if (
            uncertainty_codes
            != self.uncertainty_codes
        ):
            raise _error(
                "uncertainty_not_canonical",
                "uncertainty_codes",
                (
                    "Uncertainty codes must "
                    "use canonical order."
                ),
            )

        if (
            self.metadata.contract_type
            != REQUEST_CONTRACT_TYPE
        ):
            raise _error(
                "request_contract_type_mismatch",
                "contract_type",
                (
                    "Metadata contract type "
                    "is incorrect."
                ),
            )

        if (
            self.metadata.schema_version
            != REQUEST_CONTRACT_SCHEMA_VERSION
        ):
            raise _error(
                "request_contract_schema_mismatch",
                "schema_version",
                (
                    "RequestContract must use "
                    "schema version 1.0.0."
                ),
            )

        if (
            self.metadata.authority_status
            != AuthorityStatus.NONE
        ):
            raise _error(
                "request_contract_authority_forbidden",
                "authority_status",
                (
                    "RequestContract cannot "
                    "carry authority."
                ),
            )

        if self.metadata.declared_effects:
            raise _error(
                "request_contract_effects_forbidden",
                "declared_effects",
                (
                    "RequestContract cannot "
                    "declare side effects."
                ),
            )

        if (
            self.metadata.parent is not None
            and (
                self.metadata
                .parent
                .contract_type
                != REQUEST_CONTRACT_TYPE
            )
        ):
            raise _error(
                "request_contract_parent_type_mismatch",
                "parent",
                (
                    "A RequestContract parent "
                    "must reference "
                    "RequestContract."
                ),
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

    def body(
        self,
    ) -> dict[str, Any]:
        return _request_body(
            input_event=self.input_event,
            classification_candidate_set=(
                self
                .classification_candidate_set
            ),
            producer_id=self.producer_id,
            selected_candidates=(
                self.selected_candidates
            ),
            goals=self.goals,
            constraints=self.constraints,
            desired_result=(
                self.desired_result
            ),
            uncertainty_codes=(
                self.uncertainty_codes
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
                "RequestContract did not "
                "serialize to a mapping."
            )

        return value


def create_request_contract(
    *,
    input_event: InputEvent,
    classification_candidate_set: (
        ClassificationCandidateSet
    ),
    producer_id: str,
    selected_candidates: Iterable[
        CandidateSelection
    ],
    goals: Iterable[
        RequestStatement
    ],
    constraints: Iterable[
        RequestStatement
    ],
    desired_result: RequestStatement,
    uncertainty_codes: Iterable[
        str
    ],
    created_at: datetime,
) -> RequestContract:
    """Create a contract from explicit selection records."""

    verify_input_event(input_event)
    verify_classification_candidate_set(
        classification_candidate_set,
        input_event=input_event,
    )

    if (
        classification_candidate_set
        .clarification_recommended
        or (
            classification_candidate_set
            .clarification_reason_codes
        )
    ):
        raise _error(
            "classification_requires_clarification",
            "classification_candidate_set",
            (
                "A candidate set requiring "
                "clarification cannot produce "
                "RequestContract."
            ),
        )

    normalized_producer = (
        _normalized_producer_id(
            producer_id
        )
    )
    normalized_selections = (
        _normalize_selections(
            selected_candidates
        )
    )
    normalized_goals = (
        _normalize_statements(
            goals,
            expected_kind=(
                RequestStatementKind.GOAL
            ),
            field="goals",
            allow_empty=False,
        )
    )
    normalized_constraints = (
        _normalize_statements(
            constraints,
            expected_kind=(
                RequestStatementKind
                .CONSTRAINT
            ),
            field="constraints",
            allow_empty=True,
        )
    )

    if not isinstance(
        desired_result,
        RequestStatement,
    ):
        raise _error(
            "invalid_desired_result",
            "desired_result",
            (
                "Desired result must be "
                "RequestStatement."
            ),
        )

    if (
        desired_result.kind
        is not (
            RequestStatementKind
            .DESIRED_RESULT
        )
    ):
        raise _error(
            "desired_result_kind_mismatch",
            "desired_result",
            (
                "Desired result statement "
                "must use desired_result kind."
            ),
        )

    normalized_uncertainty = (
        _normalize_codes(
            uncertainty_codes,
            field="uncertainty_codes",
            allow_empty=True,
        )
    )

    input_reference = (
        input_event.metadata.to_reference()
    )
    candidate_set_reference = (
        classification_candidate_set
        .metadata
        .to_reference()
    )

    body = _request_body(
        input_event=input_reference,
        classification_candidate_set=(
            candidate_set_reference
        ),
        producer_id=normalized_producer,
        selected_candidates=(
            normalized_selections
        ),
        goals=normalized_goals,
        constraints=normalized_constraints,
        desired_result=desired_result,
        uncertainty_codes=(
            normalized_uncertainty
        ),
    )

    metadata = create_contract_metadata(
        schema_version=(
            REQUEST_CONTRACT_SCHEMA_VERSION
        ),
        contract_type=(
            REQUEST_CONTRACT_TYPE
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

    result = RequestContract(
        metadata=metadata,
        input_event=input_reference,
        classification_candidate_set=(
            candidate_set_reference
        ),
        producer_id=normalized_producer,
        selected_candidates=(
            normalized_selections
        ),
        goals=normalized_goals,
        constraints=normalized_constraints,
        desired_result=desired_result,
        uncertainty_codes=(
            normalized_uncertainty
        ),
    )

    verify_request_contract(
        result,
        input_event=input_event,
        classification_candidate_set=(
            classification_candidate_set
        ),
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


def _candidate_selection_from_dict(
    value: object,
) -> CandidateSelection:
    record = _exact_mapping(
        value,
        _SELECTION_KEYS,
        field="candidate_selection",
    )
    basis_value = record["basis_codes"]

    if not isinstance(
        basis_value,
        (list, tuple),
    ):
        raise _error(
            "invalid_code_collection",
            "basis_codes",
            (
                "Selection basis codes must "
                "be a sequence."
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
                "Candidate dimension is "
                "unknown."
            ),
        ) from error

    return CandidateSelection(
        selection_id=record["selection_id"],
        candidate_id=record["candidate_id"],
        dimension=dimension,
        label=record["label"],
        basis_codes=tuple(basis_value),
    )


def _request_statement_from_dict(
    value: object,
) -> RequestStatement:
    record = _exact_mapping(
        value,
        _STATEMENT_KEYS,
        field="request_statement",
    )
    evidence_value = record[
        "evidence_ids"
    ]

    if not isinstance(
        evidence_value,
        (list, tuple),
    ):
        raise _error(
            "invalid_evidence_id_collection",
            "evidence_ids",
            (
                "Evidence IDs must be a "
                "sequence."
            ),
        )

    try:
        kind = RequestStatementKind(
            record["kind"]
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise _error(
            "invalid_request_statement_kind",
            "kind",
            (
                "Request statement kind "
                "is unknown."
            ),
        ) from error

    return RequestStatement(
        statement_id=record["statement_id"],
        kind=kind,
        code=record["code"],
        text=record["text"],
        evidence_ids=tuple(
            evidence_value
        ),
    )


def request_contract_from_dict(
    value: object,
    *,
    input_event: InputEvent,
    classification_candidate_set: (
        ClassificationCandidateSet
    ),
) -> RequestContract:
    """Decode and verify an exact RequestContract."""

    top = _exact_mapping(
        value,
        _TOP_LEVEL_KEYS,
        field="request_contract",
    )
    body = _exact_mapping(
        top["body"],
        _BODY_KEYS,
        field="body",
    )

    selections_value = body[
        "selected_candidates"
    ]
    goals_value = body["goals"]
    constraints_value = body[
        "constraints"
    ]
    uncertainty_value = body[
        "uncertainty_codes"
    ]

    for field, collection in (
        (
            "selected_candidates",
            selections_value,
        ),
        ("goals", goals_value),
        ("constraints", constraints_value),
        (
            "uncertainty_codes",
            uncertainty_value,
        ),
    ):
        if not isinstance(
            collection,
            (list, tuple),
        ):
            raise _error(
                "invalid_sequence_type",
                field,
                (
                    f"{field} must be a "
                    "sequence."
                ),
            )

    result = RequestContract(
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
        classification_candidate_set=(
            contract_reference_from_dict(
                body[
                    "classification_candidate_set"
                ]
            )
        ),
        producer_id=body["producer_id"],
        selected_candidates=tuple(
            _candidate_selection_from_dict(
                item
            )
            for item
            in selections_value
        ),
        goals=tuple(
            _request_statement_from_dict(
                item
            )
            for item in goals_value
        ),
        constraints=tuple(
            _request_statement_from_dict(
                item
            )
            for item
            in constraints_value
        ),
        desired_result=(
            _request_statement_from_dict(
                body["desired_result"]
            )
        ),
        uncertainty_codes=tuple(
            uncertainty_value
        ),
    )

    verify_request_contract(
        result,
        input_event=input_event,
        classification_candidate_set=(
            classification_candidate_set
        ),
    )

    return result


def verify_request_contract(
    request_contract: RequestContract,
    *,
    input_event: InputEvent,
    classification_candidate_set: (
        ClassificationCandidateSet
    ),
) -> None:
    """Verify selections and source-evidence custody."""

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

    verify_input_event(input_event)

    if (
        request_contract.input_event
        != input_event
        .metadata
        .to_reference()
    ):
        raise ContractIntegrityError(
            "request_input_event_mismatch",
            "input_event",
            (
                "RequestContract does not "
                "reference the supplied "
                "InputEvent."
            ),
        )

    verify_classification_candidate_set(
        classification_candidate_set,
        input_event=input_event,
    )

    if (
        request_contract
        .classification_candidate_set
        != (
            classification_candidate_set
            .metadata
            .to_reference()
        )
    ):
        raise ContractIntegrityError(
            "request_candidate_set_mismatch",
            "classification_candidate_set",
            (
                "RequestContract does not "
                "reference the supplied "
                "candidate set."
            ),
        )

    if (
        classification_candidate_set
        .clarification_recommended
        or (
            classification_candidate_set
            .clarification_reason_codes
        )
    ):
        raise _error(
            "classification_requires_clarification",
            "classification_candidate_set",
            (
                "A candidate set requiring "
                "clarification cannot support "
                "RequestContract."
            ),
        )

    if (
        request_contract.uncertainty_codes
        != (
            classification_candidate_set
            .uncertainty_codes
        )
    ):
        raise ContractIntegrityError(
            "request_uncertainty_mismatch",
            "uncertainty_codes",
            (
                "RequestContract must preserve "
                "the candidate set's exact "
                "uncertainty codes."
            ),
        )

    candidate_by_id = {
        candidate.candidate_id: candidate
        for candidate
        in (
            classification_candidate_set
            .candidates
        )
    }
    selected_by_dimension: dict[
        CandidateDimension,
        ClassificationCandidate,
    ] = {}
    selected_evidence_ids: set[str] = set()

    for selection in (
        request_contract
        .selected_candidates
    ):
        candidate = candidate_by_id.get(
            selection.candidate_id
        )

        if candidate is None:
            raise ContractIntegrityError(
                "selected_candidate_not_found",
                "selected_candidates",
                (
                    "A selected candidate is "
                    "not present in the source "
                    "candidate set."
                ),
            )

        if (
            selection.dimension
            is not candidate.dimension
            or selection.label
            != candidate.label
        ):
            raise ContractIntegrityError(
                "selected_candidate_material_mismatch",
                "selected_candidates",
                (
                    "Selection dimension or "
                    "label does not match the "
                    "source candidate."
                ),
            )

        selected_by_dimension[
            candidate.dimension
        ] = candidate

        for evidence in candidate.evidence:
            selected_evidence_ids.add(
                evidence.evidence_id
            )

    missing_dimensions = (
        _REQUIRED_DIMENSIONS
        - frozenset(
            selected_by_dimension
        )
    )

    if missing_dimensions:
        raise _error(
            "required_candidate_dimension_missing",
            "selected_candidates",
            (
                "Missing required dimensions: "
                + ", ".join(
                    sorted(
                        item.value
                        for item
                        in missing_dimensions
                    )
                )
            ),
        )

    statements = (
        *request_contract.goals,
        *request_contract.constraints,
        request_contract.desired_result,
    )

    for statement in statements:
        missing_evidence = (
            set(statement.evidence_ids)
            - selected_evidence_ids
        )

        if missing_evidence:
            raise ContractIntegrityError(
                (
                    "request_statement_"
                    "evidence_not_selected"
                ),
                "evidence_ids",
                (
                    "Request statement evidence "
                    "must come from selected "
                    "candidates."
                ),
            )

    expected_result_candidate = (
        selected_by_dimension[
            CandidateDimension
            .EXPECTED_RESULT
        ]
    )

    if (
        request_contract
        .desired_result
        .code
        != expected_result_candidate.label
    ):
        raise ContractIntegrityError(
            "desired_result_candidate_mismatch",
            "desired_result",
            (
                "Desired-result code must "
                "match the selected expected-"
                "result candidate label."
            ),
        )

    verify_contract_metadata(
        request_contract.metadata,
        request_contract.body(),
    )


__all__ = (
    "CANDIDATE_SELECTION_ID_NAMESPACE",
    "REQUEST_CONTRACT_SCHEMA_VERSION",
    "REQUEST_CONTRACT_TYPE",
    "REQUEST_STATEMENT_ID_NAMESPACE",
    "CandidateSelection",
    "RequestContract",
    "RequestStatement",
    "RequestStatementKind",
    "create_candidate_selection",
    "create_request_contract",
    "create_request_statement",
    "request_contract_from_dict",
    "verify_request_contract",
)
