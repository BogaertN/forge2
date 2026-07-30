"""Tests for deeply immutable canonical values."""

from __future__ import annotations

import unittest

from forge2.contracts import (
    CanonicalKeyCollisionError,
    FrozenCanonicalList,
    FrozenCanonicalMap,
    UnsupportedCanonicalTypeError,
    canonical_json,
    freeze_canonical,
    is_frozen_canonical,
    thaw_canonical,
)


class FrozenCanonicalValueTests(
    unittest.TestCase
):
    def test_deep_freeze(self) -> None:
        source = {
            "items": [
                {
                    "value": 1,
                }
            ]
        }

        frozen = freeze_canonical(source)

        self.assertIsInstance(
            frozen,
            FrozenCanonicalMap,
        )
        self.assertIsInstance(
            frozen["items"],
            FrozenCanonicalList,
        )
        self.assertTrue(
            is_frozen_canonical(frozen)
        )

    def test_original_mutation_has_no_effect(
        self,
    ) -> None:
        source = {
            "items": [1],
        }
        frozen = freeze_canonical(source)

        source["items"].append(2)
        source["other"] = True

        self.assertEqual(
            thaw_canonical(frozen),
            {
                "items": [1],
            },
        )

    def test_map_assignment_is_rejected(
        self,
    ) -> None:
        frozen = freeze_canonical(
            {
                "value": 1,
            }
        )

        with self.assertRaises(
            TypeError
        ):
            frozen["value"] = 2

    def test_attribute_assignment_rejected(
        self,
    ) -> None:
        frozen = freeze_canonical(
            {
                "value": 1,
            }
        )

        with self.assertRaises(
            AttributeError
        ):
            frozen._entries = ()

    def test_list_is_tuple_backed(
        self,
    ) -> None:
        frozen = freeze_canonical(
            [1, 2, 3]
        )

        self.assertIsInstance(
            frozen,
            tuple,
        )

        with self.assertRaises(
            AttributeError
        ):
            frozen.append(4)

    def test_mapping_order_is_canonical(
        self,
    ) -> None:
        first = freeze_canonical(
            {
                "beta": 2,
                "alpha": 1,
            }
        )
        second = freeze_canonical(
            {
                "alpha": 1,
                "beta": 2,
            }
        )

        self.assertEqual(first, second)
        self.assertEqual(
            first.entries,
            (
                ("alpha", 1),
                ("beta", 2),
            ),
        )

    def test_canonical_serializer_accepts_frozen(
        self,
    ) -> None:
        frozen = freeze_canonical(
            {
                "items": [1, 2],
            }
        )

        self.assertEqual(
            canonical_json(frozen),
            '{"items":[1,2]}',
        )

    def test_thaw_round_trip(self) -> None:
        value = {
            "a": [1, True, None],
            "b": {
                "text": "hello",
            },
        }

        self.assertEqual(
            thaw_canonical(
                freeze_canonical(value)
            ),
            value,
        )

    def test_float_is_rejected(self) -> None:
        with self.assertRaises(
            UnsupportedCanonicalTypeError
        ):
            freeze_canonical(
                {
                    "value": 1.5,
                }
            )

    def test_bytes_are_rejected(self) -> None:
        with self.assertRaises(
            UnsupportedCanonicalTypeError
        ):
            freeze_canonical(b"data")

    def test_normalized_key_collision_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            CanonicalKeyCollisionError
        ):
            freeze_canonical(
                {
                    "é": 1,
                    "e\u0301": 2,
                }
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
