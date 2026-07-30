"""Deeply immutable canonical values for Forge 2."""

from __future__ import annotations

from collections.abc import (
    Iterable,
    Iterator,
    Mapping,
)
from typing import Any, TypeAlias

from .canonical import (
    CanonicalizationError,
    canonicalize,
)


FrozenCanonicalScalar: TypeAlias = (
    None | bool | int | str
)


class FrozenCanonicalList(tuple):
    """Immutable ordered canonical values."""

    __slots__ = ()

    def __new__(
        cls,
        values: Iterable[
            "FrozenCanonicalValue"
        ] = (),
    ) -> "FrozenCanonicalList":
        items = tuple(values)

        for item in items:
            if not is_frozen_canonical(item):
                raise TypeError(
                    "FrozenCanonicalList contains "
                    "a non-frozen canonical value."
                )

        return tuple.__new__(
            cls,
            items,
        )


class FrozenCanonicalMap(
    Mapping[str, "FrozenCanonicalValue"]
):
    """Immutable canonical mapping in key order."""

    __slots__ = ("_entries",)

    def __init__(
        self,
        entries: Iterable[
            tuple[
                str,
                "FrozenCanonicalValue",
            ]
        ] = (),
    ) -> None:
        values = tuple(entries)

        previous: str | None = None
        seen: set[str] = set()

        for key, item in values:
            if not isinstance(key, str):
                raise TypeError(
                    "Frozen canonical map keys "
                    "must be text."
                )

            if canonicalize(key) != key:
                raise ValueError(
                    "Frozen canonical map key is "
                    "not normalized."
                )

            if key in seen:
                raise ValueError(
                    "Frozen canonical map contains "
                    "a duplicate key."
                )

            if (
                previous is not None
                and key <= previous
            ):
                raise ValueError(
                    "Frozen canonical map keys "
                    "must use strict sorted order."
                )

            if not is_frozen_canonical(item):
                raise TypeError(
                    "Frozen canonical map contains "
                    "a non-frozen canonical value."
                )

            seen.add(key)
            previous = key

        object.__setattr__(
            self,
            "_entries",
            values,
        )

    def __setattr__(
        self,
        name: str,
        value: object,
    ) -> None:
        raise AttributeError(
            "FrozenCanonicalMap is immutable."
        )

    def __iter__(self) -> Iterator[str]:
        return (
            key
            for key, _ in self._entries
        )

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(
        self,
        key: str,
    ) -> "FrozenCanonicalValue":
        for current, value in self._entries:
            if current == key:
                return value

        raise KeyError(key)

    def __hash__(self) -> int:
        return hash(self._entries)

    def __eq__(self, other: object) -> bool:
        if isinstance(
            other,
            FrozenCanonicalMap,
        ):
            return self._entries == other._entries

        if isinstance(other, Mapping):
            return dict(self.items()) == dict(
                other.items()
            )

        return False

    def __repr__(self) -> str:
        return (
            "FrozenCanonicalMap("
            f"{self._entries!r})"
        )

    @property
    def entries(
        self,
    ) -> tuple[
        tuple[
            str,
            "FrozenCanonicalValue",
        ],
        ...,
    ]:
        return self._entries


FrozenCanonicalValue: TypeAlias = (
    FrozenCanonicalScalar
    | FrozenCanonicalList
    | FrozenCanonicalMap
)


def is_frozen_canonical(
    value: object,
) -> bool:
    """Return whether a value is deeply canonical."""

    if value is None:
        return True

    if isinstance(value, bool):
        return True

    if isinstance(value, int):
        try:
            return canonicalize(value) == value
        except CanonicalizationError:
            return False

    if isinstance(value, str):
        try:
            return canonicalize(value) == value
        except CanonicalizationError:
            return False

    if isinstance(
        value,
        FrozenCanonicalList,
    ):
        return all(
            is_frozen_canonical(item)
            for item in value
        )

    if isinstance(
        value,
        FrozenCanonicalMap,
    ):
        return all(
            is_frozen_canonical(item)
            for _, item in value.entries
        )

    return False


def _freeze_normalized(
    value: Any,
) -> FrozenCanonicalValue:
    if (
        value is None
        or isinstance(
            value,
            (bool, int, str),
        )
    ):
        return value

    if isinstance(value, list):
        return FrozenCanonicalList(
            _freeze_normalized(item)
            for item in value
        )

    if isinstance(value, dict):
        return FrozenCanonicalMap(
            (
                key,
                _freeze_normalized(item),
            )
            for key, item in value.items()
        )

    raise TypeError(
        "Normalized canonical value had "
        "an unsupported internal type."
    )


def freeze_canonical(
    value: Any,
) -> FrozenCanonicalValue:
    """Normalize and deeply freeze a canonical value."""

    return _freeze_normalized(
        canonicalize(value)
    )


def thaw_canonical(
    value: FrozenCanonicalValue,
) -> Any:
    """Return ordinary JSON-compatible containers."""

    if (
        value is None
        or isinstance(
            value,
            (bool, int, str),
        )
    ):
        return value

    if isinstance(
        value,
        FrozenCanonicalList,
    ):
        return [
            thaw_canonical(item)
            for item in value
        ]

    if isinstance(
        value,
        FrozenCanonicalMap,
    ):
        return {
            key: thaw_canonical(item)
            for key, item in value.entries
        }

    raise TypeError(
        "Value is not a frozen canonical value."
    )


__all__ = (
    "FrozenCanonicalList",
    "FrozenCanonicalMap",
    "FrozenCanonicalScalar",
    "FrozenCanonicalValue",
    "freeze_canonical",
    "is_frozen_canonical",
    "thaw_canonical",
)
