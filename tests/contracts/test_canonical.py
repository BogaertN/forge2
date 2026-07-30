"""Invariant tests for canonical contract serialization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
import unittest
import unicodedata

from forge2.contracts import (
    CanonicalKeyCollisionError,
    CanonicalizationCycleError,
    CanonicalizationError,
    InvalidStableNamespaceError,
    MAX_SAFE_INTEGER,
    MutableDataclassError,
    UnsupportedCanonicalTypeError,
    canonical_bytes,
    canonical_json,
    canonical_sha256,
    canonicalize,
    stable_identifier,
)


class ExampleState(StrEnum):
    READY = "ready"


@dataclass(frozen=True, slots=True)
class FrozenRecord:
    schema_version: str
    name: str
    state: ExampleState


@dataclass
class MutableRecord:
    value: str


class HiddenConversionObject:
    def to_dict(self) -> dict[str, str]:
        return {"hidden": "conversion"}


class CanonicalSerializationTests(unittest.TestCase):
    def test_fixed_vector(self) -> None:
        value = {
            "schema_version": "1.0.0",
            "name": "café",
            "items": [3, 2, 1],
            "enabled": True,
            "none": None,
        }

        expected_json = (
            '{"enabled":true,"items":[3,2,1],'
            '"name":"café","none":null,'
            '"schema_version":"1.0.0"}'
        )

        self.assertEqual(
            canonical_json(value),
            expected_json,
        )
        self.assertEqual(
            canonical_bytes(value),
            expected_json.encode("utf-8"),
        )
        self.assertEqual(
            canonical_sha256(value),
            (
                "90ec26e3b46bc29f9a00493509f8dbb3"
                "8f072b701d32e3508502ac1e599d20bd"
            ),
        )

    def test_mapping_order_does_not_change_hash(self) -> None:
        first = {
            "alpha": 1,
            "beta": 2,
        }
        second = {
            "beta": 2,
            "alpha": 1,
        }

        self.assertEqual(
            canonical_json(first),
            canonical_json(second),
        )
        self.assertEqual(
            canonical_sha256(first),
            canonical_sha256(second),
        )

    def test_unicode_is_normalized_to_nfc(self) -> None:
        decomposed = "cafe\u0301"
        composed = unicodedata.normalize(
            "NFC",
            decomposed,
        )

        self.assertEqual(
            canonicalize(decomposed),
            composed,
        )
        self.assertEqual(
            canonical_sha256(decomposed),
            canonical_sha256(composed),
        )

    def test_normalized_key_collision_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            CanonicalKeyCollisionError
        ):
            canonicalize(
                {
                    "é": 1,
                    "e\u0301": 2,
                }
            )

    def test_timezone_datetime_is_utc(self) -> None:
        eastern = timezone(
            -timedelta(hours=4)
        )
        value = datetime(
            2026,
            7,
            30,
            15,
            49,
            tzinfo=eastern,
        )

        self.assertEqual(
            canonicalize(value),
            "2026-07-30T19:49:00.000000Z",
        )

    def test_naive_datetime_is_rejected(self) -> None:
        with self.assertRaises(
            CanonicalizationError
        ):
            canonicalize(
                datetime(2026, 7, 30, 15, 49)
            )

    def test_date_uses_iso_format(self) -> None:
        self.assertEqual(
            canonicalize(date(2026, 7, 30)),
            "2026-07-30",
        )

    def test_float_is_rejected(self) -> None:
        for value in (
            1.0,
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with self.subTest(value=value):
                with self.assertRaises(
                    UnsupportedCanonicalTypeError
                ):
                    canonicalize(value)

    def test_safe_integer_boundaries(self) -> None:
        self.assertEqual(
            canonicalize(MAX_SAFE_INTEGER),
            MAX_SAFE_INTEGER,
        )
        self.assertEqual(
            canonicalize(-MAX_SAFE_INTEGER),
            -MAX_SAFE_INTEGER,
        )

        with self.assertRaises(
            CanonicalizationError
        ):
            canonicalize(MAX_SAFE_INTEGER + 1)

        with self.assertRaises(
            CanonicalizationError
        ):
            canonicalize(-MAX_SAFE_INTEGER - 1)

    def test_non_string_mapping_key_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            UnsupportedCanonicalTypeError
        ):
            canonicalize({1: "value"})

    def test_bytes_and_sets_are_rejected(self) -> None:
        for value in (
            b"value",
            {"alpha", "beta"},
            frozenset({"alpha", "beta"}),
        ):
            with self.subTest(value=value):
                with self.assertRaises(
                    UnsupportedCanonicalTypeError
                ):
                    canonicalize(value)

    def test_recursive_container_is_rejected(
        self,
    ) -> None:
        value: list[object] = []
        value.append(value)

        with self.assertRaises(
            CanonicalizationCycleError
        ):
            canonicalize(value)

    def test_frozen_dataclass_is_supported(
        self,
    ) -> None:
        value = FrozenRecord(
            schema_version="1.0.0",
            name="example",
            state=ExampleState.READY,
        )

        self.assertEqual(
            canonicalize(value),
            {
                "name": "example",
                "schema_version": "1.0.0",
                "state": "ready",
            },
        )

    def test_mutable_dataclass_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            MutableDataclassError
        ):
            canonicalize(
                MutableRecord(value="example")
            )

    def test_hidden_custom_conversion_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            UnsupportedCanonicalTypeError
        ):
            canonicalize(
                HiddenConversionObject()
            )

    def test_stable_identifier_is_content_addressed(
        self,
    ) -> None:
        first = stable_identifier(
            "aiweb.contract",
            {"beta": 2, "alpha": 1},
        )
        second = stable_identifier(
            "aiweb.contract",
            {"alpha": 1, "beta": 2},
        )
        changed = stable_identifier(
            "aiweb.contract",
            {"alpha": 1, "beta": 3},
        )

        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertTrue(
            first.startswith(
                "aiweb.contract:sha256:"
            )
        )
        self.assertEqual(
            len(first.rsplit(":", 1)[1]),
            64,
        )

    def test_invalid_namespace_is_rejected(
        self,
    ) -> None:
        for namespace in (
            "",
            "AIWeb.Contract",
            "1contract",
            "contract space",
            "contract/unsafe",
        ):
            with self.subTest(namespace=namespace):
                with self.assertRaises(
                    InvalidStableNamespaceError
                ):
                    stable_identifier(
                        namespace,
                        {"value": 1},
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
