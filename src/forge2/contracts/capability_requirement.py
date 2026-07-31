"""Immutable provider-neutral CapabilityRequirement.

A CapabilityRequirement records behavior that is
required without naming, selecting, qualifying, or
authorizing a provider.

This module does not discover tools, rank providers,
install packages, construct plans, authorize actions,
or execute anything.
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
)
from .codec import (
    contract_metadata_from_dict,
    contract_metadata_to_dict,
    contract_reference_from_dict,
)
from .context_manifest import (
    ContextManifest,
    verify_context_manifest,
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


CAPABILITY_REQUIREMENT_TYPE: Final[str] = (
    "CapabilityRequirement"
)
CAPABILITY_REQUIREMENT_SCHEMA_VERSION: Final[
    SchemaVersion
] = SchemaVersion(1, 0, 0)

CAPABILITY_DATA_REQUIREMENT_ID_NAMESPACE: Final[
    str
] = "aiweb.capability-data-requirement"
CAPABILITY_ACCEPTANCE_CRITERION_ID_NAMESPACE: Final[
    str
] = "aiweb.capability-acceptance-criterion"

_DATA_REQUIREMENT_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.capability-data-requirement:"
    r"sha256:[0-9a-f]{64}$"
)
_CRITERION_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.capability-acceptance-criterion:"
    r"sha256:[0-9a-f]{64}$"
)
_SELECTION_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.candidate-selection:"
    r"sha256:[0-9a-f]{64}$"
)
_STATEMENT_ID_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^aiweb\.request-statement:"
    r"sha256:[0-9a-f]{64}$"
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
_MEDIA_TYPE_PATTERN: Final[
    re.Pattern[str]
] = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,126}/"
    r"[a-z0-9][a-z0-9!#$&^_.+-]{0,126}$"
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
        "context_manifest",
        "producer_id",
        "requirement_code",
        "behavior_description",
        "behavior_statement_ids",
        "side_effect_selection_id",
        "side_effect_class",
        "input_requirements",
        "output_requirements",
        "required_property_codes",
        "acceptance_criteria",
        "uncertainty_codes",
        "input_requirement_count",
        "output_requirement_count",
        "acceptance_criterion_count",
    }
)
_DATA_REQUIREMENT_KEYS: Final[
    frozenset[str]
] = frozenset(
    {
        "requirement_id",
        "direction",
        "code",
        "description",
        "media_type",
        "schema_uri",
        "required",
        "source_statement_ids",
    }
)
_CRITERION_KEYS: Final[
    frozenset[str]
] = frozenset(
    {
        "criterion_id",
        "code",
        "description",
        "source_statement_ids",
    }
)


class CapabilityDataDirection(StrEnum):
    """Provider-neutral capability data direction."""

    INPUT = "input"
    OUTPUT = "output"


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


def _normalized_media_type(
    value: object,
) -> str:
    normalized = _normalized_text(
        value,
        field="media_type",
        maximum_length=255,
    ).lower()

    if not _MEDIA_TYPE_PATTERN.fullmatch(
        normalized
    ):
        raise _error(
            "invalid_media_type",
            "media_type",
            (
                "Media type must use lowercase "
                "type/subtype form."
            ),
        )

    return normalized


def _normalized_optional_uri(
    value: object,
) -> str | None:
    if value is None:
        return None

    normalized = _normalized_text(
        value,
        field="schema_uri",
        maximum_length=2048,
    )

    if not _SOURCE_URI_PATTERN.fullmatch(
        normalized
    ):
        raise _error(
            "invalid_schema_uri",
            "schema_uri",
            (
                "Schema URI must use a stable "
                "scheme and contain no whitespace."
            ),
        )

    return normalized


def _normalized_bool(
    value: object,
    *,
    field: str,
) -> bool:
    if not isinstance(value, bool):
        raise _error(
            "invalid_boolean_type",
            field,
            "Value must be a boolean.",
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


def _normalize_statement_ids(
    values: Iterable[str],
    *,
    field: str,
    allow_empty: bool,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise _error(
            "invalid_statement_id_collection",
            field,
            (
                "Statement IDs must be an "
                "iterable of strings."
            ),
        )

    try:
        observed = tuple(values)
    except TypeError as error:
        raise _error(
            "invalid_statement_id_collection",
            field,
            "Statement IDs must be iterable.",
        ) from error

    if not observed and not allow_empty:
        raise _error(
            "statement_reference_required",
            field,
            (
                "At least one RequestStatement "
                "reference is required."
            ),
        )

    for value in observed:
        if (
            not isinstance(value, str)
            or not _STATEMENT_ID_PATTERN.fullmatch(
                value
            )
        ):
            raise _error(
                "invalid_request_statement_id",
                field,
                (
                    "Statement IDs must use the "
                    "approved SHA-256 form."
                ),
            )

    ordered = tuple(sorted(observed))

    if len(set(ordered)) != len(ordered):
        raise _error(
            "duplicate_request_statement_id",
            field,
            "Statement IDs must be unique.",
        )

    return ordered


def _data_requirement_material(
    *,
    direction: CapabilityDataDirection,
    code: str,
    description: str,
    media_type: str,
    schema_uri: str | None,
    required: bool,
    source_statement_ids: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "direction": direction.value,
        "code": code,
        "description": description,
        "media_type": media_type,
        "schema_uri": schema_uri,
        "required": required,
        "source_statement_ids": list(
            source_statement_ids
        ),
    }


@dataclass(frozen=True, slots=True)
class CapabilityDataRequirement:
    """One provider-neutral input or output requirement."""

    requirement_id: str
    direction: CapabilityDataDirection
    code: str
    description: str
    media_type: str
    schema_uri: str | None
    required: bool
    source_statement_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.direction,
            CapabilityDataDirection,
        ):
            raise _error(
                "invalid_data_direction",
                "direction",
                (
                    "Direction must be "
                    "CapabilityDataDirection."
                ),
            )

        code = _normalized_code(
            self.code,
            field="code",
        )
        description = _normalized_text(
            self.description,
            field="description",
            maximum_length=2048,
        )
        media_type = _normalized_media_type(
            self.media_type
        )
        schema_uri = _normalized_optional_uri(
            self.schema_uri
        )
        required = _normalized_bool(
            self.required,
            field="required",
        )

        if not isinstance(
            self.source_statement_ids,
            tuple,
        ):
            raise _error(
                "statement_ids_not_immutable",
                "source_statement_ids",
                (
                    "Stored statement IDs must "
                    "be a tuple."
                ),
            )

        statement_ids = (
            _normalize_statement_ids(
                self.source_statement_ids,
                field="source_statement_ids",
                allow_empty=False,
            )
        )

        if (
            statement_ids
            != self.source_statement_ids
        ):
            raise _error(
                "statement_ids_not_canonical",
                "source_statement_ids",
                (
                    "Statement IDs must use "
                    "canonical order."
                ),
            )

        if (
            not isinstance(
                self.requirement_id,
                str,
            )
            or not (
                _DATA_REQUIREMENT_ID_PATTERN
                .fullmatch(self.requirement_id)
            )
        ):
            raise _error(
                "invalid_data_requirement_id",
                "requirement_id",
                (
                    "Data requirement ID must "
                    "use the approved SHA-256 form."
                ),
            )

        expected_id = stable_identifier(
            CAPABILITY_DATA_REQUIREMENT_ID_NAMESPACE,
            _data_requirement_material(
                direction=self.direction,
                code=code,
                description=description,
                media_type=media_type,
                schema_uri=schema_uri,
                required=required,
                source_statement_ids=statement_ids,
            ),
        )

        if self.requirement_id != expected_id:
            raise ContractIntegrityError(
                "data_requirement_id_mismatch",
                "requirement_id",
                (
                    "Data requirement ID does "
                    "not match its material."
                ),
            )

        object.__setattr__(
            self,
            "code",
            code,
        )
        object.__setattr__(
            self,
            "description",
            description,
        )
        object.__setattr__(
            self,
            "media_type",
            media_type,
        )
        object.__setattr__(
            self,
            "schema_uri",
            schema_uri,
        )
        object.__setattr__(
            self,
            "required",
            required,
        )
        object.__setattr__(
            self,
            "source_statement_ids",
            statement_ids,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "direction": self.direction.value,
            "code": self.code,
            "description": self.description,
            "media_type": self.media_type,
            "schema_uri": self.schema_uri,
            "required": self.required,
            "source_statement_ids": list(
                self.source_statement_ids
            ),
        }


def create_capability_data_requirement(
    *,
    direction: CapabilityDataDirection,
    code: str,
    description: str,
    media_type: str,
    schema_uri: str | None,
    required: bool,
    source_statement_ids: Iterable[str],
) -> CapabilityDataRequirement:
    if not isinstance(
        direction,
        CapabilityDataDirection,
    ):
        raise _error(
            "invalid_data_direction",
            "direction",
            (
                "Direction must be "
                "CapabilityDataDirection."
            ),
        )

    normalized_code = _normalized_code(
        code,
        field="code",
    )
    normalized_description = (
        _normalized_text(
            description,
            field="description",
            maximum_length=2048,
        )
    )
    normalized_media_type = (
        _normalized_media_type(
            media_type
        )
    )
    normalized_schema_uri = (
        _normalized_optional_uri(
            schema_uri
        )
    )
    normalized_required = _normalized_bool(
        required,
        field="required",
    )
    normalized_statement_ids = (
        _normalize_statement_ids(
            source_statement_ids,
            field="source_statement_ids",
            allow_empty=False,
        )
    )

    requirement_id = stable_identifier(
        CAPABILITY_DATA_REQUIREMENT_ID_NAMESPACE,
        _data_requirement_material(
            direction=direction,
            code=normalized_code,
            description=normalized_description,
            media_type=normalized_media_type,
            schema_uri=normalized_schema_uri,
            required=normalized_required,
            source_statement_ids=(
                normalized_statement_ids
            ),
        ),
    )

    return CapabilityDataRequirement(
        requirement_id=requirement_id,
        direction=direction,
        code=normalized_code,
        description=normalized_description,
        media_type=normalized_media_type,
        schema_uri=normalized_schema_uri,
        required=normalized_required,
        source_statement_ids=(
            normalized_statement_ids
        ),
    )


def _criterion_material(
    *,
    code: str,
    description: str,
    source_statement_ids: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "code": code,
        "description": description,
        "source_statement_ids": list(
            source_statement_ids
        ),
    }


@dataclass(frozen=True, slots=True)
class CapabilityAcceptanceCriterion:
    """Provider-neutral observable completion criterion."""

    criterion_id: str
    code: str
    description: str
    source_statement_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        code = _normalized_code(
            self.code,
            field="code",
        )
        description = _normalized_text(
            self.description,
            field="description",
            maximum_length=2048,
        )

        if not isinstance(
            self.source_statement_ids,
            tuple,
        ):
            raise _error(
                "statement_ids_not_immutable",
                "source_statement_ids",
                (
                    "Stored statement IDs must "
                    "be a tuple."
                ),
            )

        statement_ids = (
            _normalize_statement_ids(
                self.source_statement_ids,
                field="source_statement_ids",
                allow_empty=False,
            )
        )

        if (
            statement_ids
            != self.source_statement_ids
        ):
            raise _error(
                "statement_ids_not_canonical",
                "source_statement_ids",
                (
                    "Statement IDs must use "
                    "canonical order."
                ),
            )

        if (
            not isinstance(
                self.criterion_id,
                str,
            )
            or not (
                _CRITERION_ID_PATTERN
                .fullmatch(self.criterion_id)
            )
        ):
            raise _error(
                "invalid_acceptance_criterion_id",
                "criterion_id",
                (
                    "Criterion ID must use the "
                    "approved SHA-256 form."
                ),
            )

        expected_id = stable_identifier(
            CAPABILITY_ACCEPTANCE_CRITERION_ID_NAMESPACE,
            _criterion_material(
                code=code,
                description=description,
                source_statement_ids=statement_ids,
            ),
        )

        if self.criterion_id != expected_id:
            raise ContractIntegrityError(
                "acceptance_criterion_id_mismatch",
                "criterion_id",
                (
                    "Criterion ID does not "
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
            "description",
            description,
        )
        object.__setattr__(
            self,
            "source_statement_ids",
            statement_ids,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "code": self.code,
            "description": self.description,
            "source_statement_ids": list(
                self.source_statement_ids
            ),
        }


def create_capability_acceptance_criterion(
    *,
    code: str,
    description: str,
    source_statement_ids: Iterable[str],
) -> CapabilityAcceptanceCriterion:
    normalized_code = _normalized_code(
        code,
        field="code",
    )
    normalized_description = (
        _normalized_text(
            description,
            field="description",
            maximum_length=2048,
        )
    )
    normalized_statement_ids = (
        _normalize_statement_ids(
            source_statement_ids,
            field="source_statement_ids",
            allow_empty=False,
        )
    )

    criterion_id = stable_identifier(
        CAPABILITY_ACCEPTANCE_CRITERION_ID_NAMESPACE,
        _criterion_material(
            code=normalized_code,
            description=normalized_description,
            source_statement_ids=(
                normalized_statement_ids
            ),
        ),
    )

    return CapabilityAcceptanceCriterion(
        criterion_id=criterion_id,
        code=normalized_code,
        description=normalized_description,
        source_statement_ids=(
            normalized_statement_ids
        ),
    )


def _normalize_data_requirements(
    values: Iterable[
        CapabilityDataRequirement
    ],
    *,
    expected_direction: CapabilityDataDirection,
    field: str,
    require_nonempty: bool,
) -> tuple[
    CapabilityDataRequirement,
    ...,
]:
    if isinstance(values, (str, bytes)):
        raise _error(
            "invalid_data_requirement_collection",
            field,
            (
                "Data requirements must be "
                "an iterable."
            ),
        )

    try:
        requirements = tuple(values)
    except TypeError as error:
        raise _error(
            "invalid_data_requirement_collection",
            field,
            (
                "Data requirements must be "
                "iterable."
            ),
        ) from error

    if require_nonempty and not requirements:
        raise _error(
            "output_requirement_required",
            field,
            (
                "At least one provider-neutral "
                "output requirement is required."
            ),
        )

    for requirement in requirements:
        if not isinstance(
            requirement,
            CapabilityDataRequirement,
        ):
            raise _error(
                "invalid_data_requirement",
                field,
                (
                    "Every item must be "
                    "CapabilityDataRequirement."
                ),
            )

        if (
            requirement.direction
            != expected_direction
        ):
            raise _error(
                "data_direction_mismatch",
                field,
                (
                    "Data requirement appears "
                    "in the wrong direction list."
                ),
            )

    ordered = tuple(
        sorted(
            requirements,
            key=lambda value: (
                value.code,
                value.requirement_id,
            ),
        )
    )

    ids = [
        value.requirement_id
        for value in ordered
    ]
    codes = [
        value.code
        for value in ordered
    ]

    if len(set(ids)) != len(ids):
        raise _error(
            "duplicate_data_requirement",
            field,
            (
                "Data requirement IDs must "
                "be unique."
            ),
        )

    if len(set(codes)) != len(codes):
        raise _error(
            "duplicate_data_requirement_code",
            field,
            (
                "Data requirement codes must "
                "be unique within a direction."
            ),
        )

    return ordered


def _normalize_criteria(
    values: Iterable[
        CapabilityAcceptanceCriterion
    ],
) -> tuple[
    CapabilityAcceptanceCriterion,
    ...,
]:
    if isinstance(values, (str, bytes)):
        raise _error(
            "invalid_acceptance_criterion_collection",
            "acceptance_criteria",
            (
                "Acceptance criteria must be "
                "an iterable."
            ),
        )

    try:
        criteria = tuple(values)
    except TypeError as error:
        raise _error(
            "invalid_acceptance_criterion_collection",
            "acceptance_criteria",
            (
                "Acceptance criteria must "
                "be iterable."
            ),
        ) from error

    if not criteria:
        raise _error(
            "acceptance_criterion_required",
            "acceptance_criteria",
            (
                "At least one provider-neutral "
                "acceptance criterion is required."
            ),
        )

    for criterion in criteria:
        if not isinstance(
            criterion,
            CapabilityAcceptanceCriterion,
        ):
            raise _error(
                "invalid_acceptance_criterion",
                "acceptance_criteria",
                (
                    "Every criterion must be "
                    "CapabilityAcceptanceCriterion."
                ),
            )

    ordered = tuple(
        sorted(
            criteria,
            key=lambda value: (
                value.code,
                value.criterion_id,
            ),
        )
    )

    ids = [
        value.criterion_id
        for value in ordered
    ]
    codes = [
        value.code
        for value in ordered
    ]

    if len(set(ids)) != len(ids):
        raise _error(
            "duplicate_acceptance_criterion",
            "acceptance_criteria",
            (
                "Acceptance criterion IDs "
                "must be unique."
            ),
        )

    if len(set(codes)) != len(codes):
        raise _error(
            "duplicate_acceptance_criterion_code",
            "acceptance_criteria",
            (
                "Acceptance criterion codes "
                "must be unique."
            ),
        )

    return ordered


def _request_statement_ids(
    request_contract: RequestContract,
) -> frozenset[str]:
    values: set[str] = set()

    for statement in request_contract.goals:
        values.add(statement.statement_id)

    for statement in request_contract.constraints:
        values.add(statement.statement_id)

    values.add(
        request_contract
        .desired_result
        .statement_id
    )

    return frozenset(values)


def _side_effect_selection(
    request_contract: RequestContract,
):
    matches = [
        selection
        for selection
        in request_contract.selected_candidates
        if (
            selection.dimension
            == CandidateDimension
            .SIDE_EFFECT_CLASS
        )
    ]

    if len(matches) != 1:
        raise ContractIntegrityError(
            "side_effect_selection_missing",
            "selected_candidates",
            (
                "RequestContract must contain "
                "exactly one selected side-effect "
                "classification."
            ),
        )

    return matches[0]


def _capability_requirement_body(
    *,
    request_contract: ContractReference,
    context_manifest: ContractReference,
    producer_id: str,
    requirement_code: str,
    behavior_description: str,
    behavior_statement_ids: tuple[str, ...],
    side_effect_selection_id: str,
    side_effect_class: str,
    input_requirements: tuple[
        CapabilityDataRequirement,
        ...,
    ],
    output_requirements: tuple[
        CapabilityDataRequirement,
        ...,
    ],
    required_property_codes: tuple[str, ...],
    acceptance_criteria: tuple[
        CapabilityAcceptanceCriterion,
        ...,
    ],
    uncertainty_codes: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "request_contract": (
            request_contract.to_dict()
        ),
        "context_manifest": (
            context_manifest.to_dict()
        ),
        "producer_id": producer_id,
        "requirement_code": requirement_code,
        "behavior_description": (
            behavior_description
        ),
        "behavior_statement_ids": list(
            behavior_statement_ids
        ),
        "side_effect_selection_id": (
            side_effect_selection_id
        ),
        "side_effect_class": (
            side_effect_class
        ),
        "input_requirements": [
            requirement.to_dict()
            for requirement
            in input_requirements
        ],
        "output_requirements": [
            requirement.to_dict()
            for requirement
            in output_requirements
        ],
        "required_property_codes": list(
            required_property_codes
        ),
        "acceptance_criteria": [
            criterion.to_dict()
            for criterion
            in acceptance_criteria
        ],
        "uncertainty_codes": list(
            uncertainty_codes
        ),
        "input_requirement_count": len(
            input_requirements
        ),
        "output_requirement_count": len(
            output_requirements
        ),
        "acceptance_criterion_count": len(
            acceptance_criteria
        ),
    }


@dataclass(frozen=True, slots=True)
class CapabilityRequirement:
    """Required behavior without provider assumption."""

    metadata: ContractMetadata
    request_contract: ContractReference
    context_manifest: ContractReference
    producer_id: str
    requirement_code: str
    behavior_description: str
    behavior_statement_ids: tuple[str, ...]
    side_effect_selection_id: str
    side_effect_class: str
    input_requirements: tuple[
        CapabilityDataRequirement,
        ...,
    ]
    output_requirements: tuple[
        CapabilityDataRequirement,
        ...,
    ]
    required_property_codes: tuple[str, ...]
    acceptance_criteria: tuple[
        CapabilityAcceptanceCriterion,
        ...,
    ]
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

        if not isinstance(
            self.context_manifest,
            ContractReference,
        ):
            raise _error(
                "invalid_context_manifest_reference",
                "context_manifest",
                (
                    "Context manifest must be "
                    "ContractReference."
                ),
            )

        if (
            self.context_manifest.contract_type
            != "ContextManifest"
        ):
            raise _error(
                "context_manifest_reference_type_mismatch",
                "context_manifest",
                (
                    "Source reference must "
                    "identify ContextManifest."
                ),
            )

        producer_id = _normalized_producer_id(
            self.producer_id
        )
        requirement_code = _normalized_code(
            self.requirement_code,
            field="requirement_code",
        )
        behavior_description = (
            _normalized_text(
                self.behavior_description,
                field="behavior_description",
                maximum_length=4096,
            )
        )

        if not isinstance(
            self.behavior_statement_ids,
            tuple,
        ):
            raise _error(
                "behavior_statement_ids_not_immutable",
                "behavior_statement_ids",
                (
                    "Stored behavior statement "
                    "IDs must be a tuple."
                ),
            )

        behavior_statement_ids = (
            _normalize_statement_ids(
                self.behavior_statement_ids,
                field="behavior_statement_ids",
                allow_empty=False,
            )
        )

        if (
            behavior_statement_ids
            != self.behavior_statement_ids
        ):
            raise _error(
                "behavior_statement_ids_not_canonical",
                "behavior_statement_ids",
                (
                    "Behavior statement IDs "
                    "must use canonical order."
                ),
            )

        if (
            not isinstance(
                self.side_effect_selection_id,
                str,
            )
            or not _SELECTION_ID_PATTERN.fullmatch(
                self.side_effect_selection_id
            )
        ):
            raise _error(
                "invalid_side_effect_selection_id",
                "side_effect_selection_id",
                (
                    "Side-effect selection ID "
                    "must use the approved form."
                ),
            )

        side_effect_class = (
            _normalized_text(
                self.side_effect_class,
                field="side_effect_class",
                maximum_length=256,
            )
        )

        if not isinstance(
            self.input_requirements,
            tuple,
        ):
            raise _error(
                "input_requirements_not_immutable",
                "input_requirements",
                (
                    "Stored input requirements "
                    "must be a tuple."
                ),
            )

        input_requirements = (
            _normalize_data_requirements(
                self.input_requirements,
                expected_direction=(
                    CapabilityDataDirection.INPUT
                ),
                field="input_requirements",
                require_nonempty=False,
            )
        )

        if (
            input_requirements
            != self.input_requirements
        ):
            raise _error(
                "input_requirements_not_canonical",
                "input_requirements",
                (
                    "Input requirements must "
                    "use canonical order."
                ),
            )

        if not isinstance(
            self.output_requirements,
            tuple,
        ):
            raise _error(
                "output_requirements_not_immutable",
                "output_requirements",
                (
                    "Stored output requirements "
                    "must be a tuple."
                ),
            )

        output_requirements = (
            _normalize_data_requirements(
                self.output_requirements,
                expected_direction=(
                    CapabilityDataDirection.OUTPUT
                ),
                field="output_requirements",
                require_nonempty=True,
            )
        )

        if (
            output_requirements
            != self.output_requirements
        ):
            raise _error(
                "output_requirements_not_canonical",
                "output_requirements",
                (
                    "Output requirements must "
                    "use canonical order."
                ),
            )

        all_data_codes = [
            requirement.code
            for requirement
            in (
                *input_requirements,
                *output_requirements,
            )
        ]

        if (
            len(set(all_data_codes))
            != len(all_data_codes)
        ):
            raise _error(
                "duplicate_cross_direction_data_code",
                "input_requirements",
                (
                    "Input and output requirement "
                    "codes must be globally unique."
                ),
            )

        if not isinstance(
            self.required_property_codes,
            tuple,
        ):
            raise _error(
                "required_property_codes_not_immutable",
                "required_property_codes",
                (
                    "Stored property codes "
                    "must be a tuple."
                ),
            )

        required_property_codes = (
            _normalize_codes(
                self.required_property_codes,
                field="required_property_codes",
                allow_empty=True,
            )
        )

        if (
            required_property_codes
            != self.required_property_codes
        ):
            raise _error(
                "required_property_codes_not_canonical",
                "required_property_codes",
                (
                    "Property codes must use "
                    "canonical order."
                ),
            )

        if not isinstance(
            self.acceptance_criteria,
            tuple,
        ):
            raise _error(
                "acceptance_criteria_not_immutable",
                "acceptance_criteria",
                (
                    "Stored acceptance criteria "
                    "must be a tuple."
                ),
            )

        acceptance_criteria = (
            _normalize_criteria(
                self.acceptance_criteria
            )
        )

        if (
            acceptance_criteria
            != self.acceptance_criteria
        ):
            raise _error(
                "acceptance_criteria_not_canonical",
                "acceptance_criteria",
                (
                    "Acceptance criteria must "
                    "use canonical order."
                ),
            )

        if not isinstance(
            self.uncertainty_codes,
            tuple,
        ):
            raise _error(
                "uncertainty_codes_not_immutable",
                "uncertainty_codes",
                (
                    "Stored uncertainty codes "
                    "must be a tuple."
                ),
            )

        uncertainty_codes = _normalize_codes(
            self.uncertainty_codes,
            field="uncertainty_codes",
            allow_empty=True,
        )

        if (
            uncertainty_codes
            != self.uncertainty_codes
        ):
            raise _error(
                "uncertainty_codes_not_canonical",
                "uncertainty_codes",
                (
                    "Uncertainty codes must "
                    "use canonical order."
                ),
            )

        if (
            self.metadata.contract_type
            != CAPABILITY_REQUIREMENT_TYPE
        ):
            raise _error(
                "capability_requirement_type_mismatch",
                "contract_type",
                (
                    "Metadata contract type "
                    "is incorrect."
                ),
            )

        if (
            self.metadata.schema_version
            != CAPABILITY_REQUIREMENT_SCHEMA_VERSION
        ):
            raise _error(
                "capability_requirement_schema_mismatch",
                "schema_version",
                (
                    "CapabilityRequirement must "
                    "use schema version 1.0.0."
                ),
            )

        if (
            self.metadata.authority_status
            != AuthorityStatus.NONE
        ):
            raise _error(
                "capability_requirement_authority_forbidden",
                "authority_status",
                (
                    "CapabilityRequirement "
                    "cannot carry authority."
                ),
            )

        if self.metadata.declared_effects:
            raise _error(
                "capability_requirement_effects_forbidden",
                "declared_effects",
                (
                    "CapabilityRequirement "
                    "cannot declare side effects."
                ),
            )

        if (
            self.metadata.parent is not None
            and (
                self.metadata
                .parent
                .contract_type
                != CAPABILITY_REQUIREMENT_TYPE
            )
        ):
            raise _error(
                "capability_requirement_parent_type_mismatch",
                "parent",
                (
                    "A CapabilityRequirement "
                    "parent must reference "
                    "CapabilityRequirement."
                ),
            )

        object.__setattr__(
            self,
            "producer_id",
            producer_id,
        )
        object.__setattr__(
            self,
            "requirement_code",
            requirement_code,
        )
        object.__setattr__(
            self,
            "behavior_description",
            behavior_description,
        )
        object.__setattr__(
            self,
            "behavior_statement_ids",
            behavior_statement_ids,
        )
        object.__setattr__(
            self,
            "side_effect_class",
            side_effect_class,
        )
        object.__setattr__(
            self,
            "required_property_codes",
            required_property_codes,
        )
        object.__setattr__(
            self,
            "uncertainty_codes",
            uncertainty_codes,
        )

        verify_contract_metadata(
            self.metadata,
            self.body(),
        )

    def body(
        self,
    ) -> dict[str, Any]:
        return _capability_requirement_body(
            request_contract=(
                self.request_contract
            ),
            context_manifest=(
                self.context_manifest
            ),
            producer_id=self.producer_id,
            requirement_code=(
                self.requirement_code
            ),
            behavior_description=(
                self.behavior_description
            ),
            behavior_statement_ids=(
                self.behavior_statement_ids
            ),
            side_effect_selection_id=(
                self.side_effect_selection_id
            ),
            side_effect_class=(
                self.side_effect_class
            ),
            input_requirements=(
                self.input_requirements
            ),
            output_requirements=(
                self.output_requirements
            ),
            required_property_codes=(
                self.required_property_codes
            ),
            acceptance_criteria=(
                self.acceptance_criteria
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
                "CapabilityRequirement did not "
                "serialize to a mapping."
            )

        return value


def _validate_statement_references(
    capability_requirement: CapabilityRequirement,
    request_contract: RequestContract,
) -> None:
    known = _request_statement_ids(
        request_contract
    )

    referenced: set[str] = set(
        capability_requirement
        .behavior_statement_ids
    )

    for requirement in (
        *capability_requirement.input_requirements,
        *capability_requirement.output_requirements,
    ):
        referenced.update(
            requirement.source_statement_ids
        )

    for criterion in (
        capability_requirement.acceptance_criteria
    ):
        referenced.update(
            criterion.source_statement_ids
        )

    unknown = sorted(referenced - known)

    if unknown:
        raise ContractIntegrityError(
            "unknown_request_statement_reference",
            "source_statement_ids",
            (
                "CapabilityRequirement references "
                "RequestStatement identities that "
                "do not exist in RequestContract: "
                + ", ".join(unknown)
            ),
        )


def create_capability_requirement(
    *,
    request_contract: RequestContract,
    context_manifest: ContextManifest,
    producer_id: str,
    requirement_code: str,
    behavior_description: str,
    behavior_statement_ids: Iterable[str],
    input_requirements: Iterable[
        CapabilityDataRequirement
    ],
    output_requirements: Iterable[
        CapabilityDataRequirement
    ],
    required_property_codes: Iterable[str],
    acceptance_criteria: Iterable[
        CapabilityAcceptanceCriterion
    ],
    uncertainty_codes: Iterable[str],
    created_at: datetime,
) -> CapabilityRequirement:
    """Create a provider-neutral behavior requirement."""

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

    verify_context_manifest(
        context_manifest,
        request_contract=request_contract,
    )

    normalized_producer = (
        _normalized_producer_id(
            producer_id
        )
    )
    normalized_requirement_code = (
        _normalized_code(
            requirement_code,
            field="requirement_code",
        )
    )
    normalized_behavior = _normalized_text(
        behavior_description,
        field="behavior_description",
        maximum_length=4096,
    )
    normalized_behavior_statements = (
        _normalize_statement_ids(
            behavior_statement_ids,
            field="behavior_statement_ids",
            allow_empty=False,
        )
    )
    normalized_inputs = (
        _normalize_data_requirements(
            input_requirements,
            expected_direction=(
                CapabilityDataDirection.INPUT
            ),
            field="input_requirements",
            require_nonempty=False,
        )
    )
    normalized_outputs = (
        _normalize_data_requirements(
            output_requirements,
            expected_direction=(
                CapabilityDataDirection.OUTPUT
            ),
            field="output_requirements",
            require_nonempty=True,
        )
    )
    normalized_properties = (
        _normalize_codes(
            required_property_codes,
            field="required_property_codes",
            allow_empty=True,
        )
    )
    normalized_criteria = (
        _normalize_criteria(
            acceptance_criteria
        )
    )
    normalized_uncertainty = (
        _normalize_codes(
            uncertainty_codes,
            field="uncertainty_codes",
            allow_empty=True,
        )
    )

    side_effect_selection = (
        _side_effect_selection(
            request_contract
        )
    )

    body = _capability_requirement_body(
        request_contract=(
            request_contract
            .metadata
            .to_reference()
        ),
        context_manifest=(
            context_manifest
            .metadata
            .to_reference()
        ),
        producer_id=normalized_producer,
        requirement_code=(
            normalized_requirement_code
        ),
        behavior_description=(
            normalized_behavior
        ),
        behavior_statement_ids=(
            normalized_behavior_statements
        ),
        side_effect_selection_id=(
            side_effect_selection.selection_id
        ),
        side_effect_class=(
            side_effect_selection.label
        ),
        input_requirements=(
            normalized_inputs
        ),
        output_requirements=(
            normalized_outputs
        ),
        required_property_codes=(
            normalized_properties
        ),
        acceptance_criteria=(
            normalized_criteria
        ),
        uncertainty_codes=(
            normalized_uncertainty
        ),
    )

    metadata = create_contract_metadata(
        schema_version=(
            CAPABILITY_REQUIREMENT_SCHEMA_VERSION
        ),
        contract_type=(
            CAPABILITY_REQUIREMENT_TYPE
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

    result = CapabilityRequirement(
        metadata=metadata,
        request_contract=(
            request_contract
            .metadata
            .to_reference()
        ),
        context_manifest=(
            context_manifest
            .metadata
            .to_reference()
        ),
        producer_id=normalized_producer,
        requirement_code=(
            normalized_requirement_code
        ),
        behavior_description=(
            normalized_behavior
        ),
        behavior_statement_ids=(
            normalized_behavior_statements
        ),
        side_effect_selection_id=(
            side_effect_selection.selection_id
        ),
        side_effect_class=(
            side_effect_selection.label
        ),
        input_requirements=(
            normalized_inputs
        ),
        output_requirements=(
            normalized_outputs
        ),
        required_property_codes=(
            normalized_properties
        ),
        acceptance_criteria=(
            normalized_criteria
        ),
        uncertainty_codes=(
            normalized_uncertainty
        ),
    )

    verify_capability_requirement(
        result,
        request_contract=request_contract,
        context_manifest=context_manifest,
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


def _data_requirement_from_dict(
    value: object,
) -> CapabilityDataRequirement:
    record = _exact_mapping(
        value,
        _DATA_REQUIREMENT_KEYS,
        field="capability_data_requirement",
    )

    try:
        direction = CapabilityDataDirection(
            record["direction"]
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise _error(
            "invalid_data_direction",
            "direction",
            (
                "Capability data direction "
                "is unknown."
            ),
        ) from error

    statement_ids = _sequence(
        record["source_statement_ids"],
        field="source_statement_ids",
    )

    return CapabilityDataRequirement(
        requirement_id=(
            record["requirement_id"]
        ),
        direction=direction,
        code=record["code"],
        description=record["description"],
        media_type=record["media_type"],
        schema_uri=record["schema_uri"],
        required=record["required"],
        source_statement_ids=tuple(
            statement_ids
        ),
    )


def _criterion_from_dict(
    value: object,
) -> CapabilityAcceptanceCriterion:
    record = _exact_mapping(
        value,
        _CRITERION_KEYS,
        field="capability_acceptance_criterion",
    )

    statement_ids = _sequence(
        record["source_statement_ids"],
        field="source_statement_ids",
    )

    return CapabilityAcceptanceCriterion(
        criterion_id=record["criterion_id"],
        code=record["code"],
        description=record["description"],
        source_statement_ids=tuple(
            statement_ids
        ),
    )


def capability_requirement_from_dict(
    value: object,
    *,
    request_contract: RequestContract,
    context_manifest: ContextManifest,
) -> CapabilityRequirement:
    """Decode an exact CapabilityRequirement."""

    top = _exact_mapping(
        value,
        _TOP_LEVEL_KEYS,
        field="capability_requirement",
    )
    body = _exact_mapping(
        top["body"],
        _BODY_KEYS,
        field="body",
    )

    input_values = _sequence(
        body["input_requirements"],
        field="input_requirements",
    )
    output_values = _sequence(
        body["output_requirements"],
        field="output_requirements",
    )
    criterion_values = _sequence(
        body["acceptance_criteria"],
        field="acceptance_criteria",
    )
    behavior_statement_values = (
        _sequence(
            body["behavior_statement_ids"],
            field="behavior_statement_ids",
        )
    )
    property_values = _sequence(
        body["required_property_codes"],
        field="required_property_codes",
    )
    uncertainty_values = _sequence(
        body["uncertainty_codes"],
        field="uncertainty_codes",
    )

    input_requirements = tuple(
        _data_requirement_from_dict(item)
        for item in input_values
    )
    output_requirements = tuple(
        _data_requirement_from_dict(item)
        for item in output_values
    )
    criteria = tuple(
        _criterion_from_dict(item)
        for item in criterion_values
    )

    for field, expected, observed in (
        (
            "input_requirement_count",
            body["input_requirement_count"],
            len(input_requirements),
        ),
        (
            "output_requirement_count",
            body["output_requirement_count"],
            len(output_requirements),
        ),
        (
            "acceptance_criterion_count",
            body["acceptance_criterion_count"],
            len(criteria),
        ),
    ):
        if (
            isinstance(expected, bool)
            or not isinstance(expected, int)
            or expected < 0
        ):
            raise _error(
                "invalid_count",
                field,
                (
                    "Recorded count must be a "
                    "non-negative integer."
                ),
            )

        if expected != observed:
            raise ContractIntegrityError(
                "recorded_count_mismatch",
                field,
                (
                    "Recorded count does not "
                    "match contained records."
                ),
            )

    result = CapabilityRequirement(
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
        context_manifest=(
            contract_reference_from_dict(
                body["context_manifest"]
            )
        ),
        producer_id=body["producer_id"],
        requirement_code=(
            body["requirement_code"]
        ),
        behavior_description=(
            body["behavior_description"]
        ),
        behavior_statement_ids=tuple(
            behavior_statement_values
        ),
        side_effect_selection_id=(
            body["side_effect_selection_id"]
        ),
        side_effect_class=(
            body["side_effect_class"]
        ),
        input_requirements=(
            input_requirements
        ),
        output_requirements=(
            output_requirements
        ),
        required_property_codes=tuple(
            property_values
        ),
        acceptance_criteria=criteria,
        uncertainty_codes=tuple(
            uncertainty_values
        ),
    )

    verify_capability_requirement(
        result,
        request_contract=request_contract,
        context_manifest=context_manifest,
    )

    return result


def verify_capability_requirement(
    capability_requirement: CapabilityRequirement,
    *,
    request_contract: RequestContract,
    context_manifest: ContextManifest,
) -> None:
    """Verify exact source and provider-neutral binding."""

    if not isinstance(
        capability_requirement,
        CapabilityRequirement,
    ):
        raise _error(
            "invalid_capability_requirement_type",
            "capability_requirement",
            (
                "Value must be "
                "CapabilityRequirement."
            ),
        )

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

    verify_context_manifest(
        context_manifest,
        request_contract=request_contract,
    )

    if (
        capability_requirement.request_contract
        != (
            request_contract
            .metadata
            .to_reference()
        )
    ):
        raise ContractIntegrityError(
            "capability_request_contract_mismatch",
            "request_contract",
            (
                "CapabilityRequirement does "
                "not reference the supplied "
                "RequestContract."
            ),
        )

    if (
        capability_requirement.context_manifest
        != (
            context_manifest
            .metadata
            .to_reference()
        )
    ):
        raise ContractIntegrityError(
            "capability_context_manifest_mismatch",
            "context_manifest",
            (
                "CapabilityRequirement does "
                "not reference the supplied "
                "ContextManifest."
            ),
        )

    _validate_statement_references(
        capability_requirement,
        request_contract,
    )

    side_effect_selection = (
        _side_effect_selection(
            request_contract
        )
    )

    if (
        capability_requirement
        .side_effect_selection_id
        != side_effect_selection.selection_id
        or capability_requirement
        .side_effect_class
        != side_effect_selection.label
    ):
        raise ContractIntegrityError(
            "side_effect_classification_mismatch",
            "side_effect_class",
            (
                "CapabilityRequirement does not "
                "preserve the selected request "
                "side-effect classification."
            ),
        )

    request_uncertainties = set(
        request_contract.uncertainty_codes
    )
    requirement_uncertainties = set(
        capability_requirement
        .uncertainty_codes
    )

    if not request_uncertainties.issubset(
        requirement_uncertainties
    ):
        raise ContractIntegrityError(
            "request_uncertainty_not_preserved",
            "uncertainty_codes",
            (
                "CapabilityRequirement lost "
                "RequestContract uncertainty."
            ),
        )

    verify_contract_metadata(
        capability_requirement.metadata,
        capability_requirement.body(),
    )


__all__ = (
    "CAPABILITY_ACCEPTANCE_CRITERION_ID_NAMESPACE",
    "CAPABILITY_DATA_REQUIREMENT_ID_NAMESPACE",
    "CAPABILITY_REQUIREMENT_SCHEMA_VERSION",
    "CAPABILITY_REQUIREMENT_TYPE",
    "CapabilityAcceptanceCriterion",
    "CapabilityDataDirection",
    "CapabilityDataRequirement",
    "CapabilityRequirement",
    "capability_requirement_from_dict",
    "create_capability_acceptance_criterion",
    "create_capability_data_requirement",
    "create_capability_requirement",
    "verify_capability_requirement",
)
