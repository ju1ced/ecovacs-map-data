"""Tests for compact Ecovacs trace publishing."""

import importlib.util
import sys
import unittest
from enum import Enum, auto
from pathlib import Path

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "ecovacs_map_data"
    / "geometry.py"
)
SPEC = importlib.util.spec_from_file_location("ecovacs_map_trace", MODULE_PATH)
assert SPEC and SPEC.loader
geometry = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = geometry
SPEC.loader.exec_module(geometry)


class PositionType(Enum):
    """Small stand-in for deebot-client's Rust enum."""

    DEEBOT = auto()
    CHARGER = auto()


def encode_point(x: int, y: int, *, connected: bool = True) -> bytes:
    """Encode one point in deebot-client's five-byte trace format."""
    flag = 0 if connected else 0x80
    return x.to_bytes(2, "little", signed=True) + y.to_bytes(
        2, "little", signed=True
    ) + bytes([flag])


class TraceTests(unittest.TestCase):
    """Verify trace decoding, path generation and chunk handling."""

    def test_decode_trace_chunk(self) -> None:
        """Signed coordinates and connection flags are decoded."""
        raw = encode_point(-215, -70, connected=False) + encode_point(-212, -73)

        points = geometry.decode_trace_chunk("compressed", lambda _: raw)

        self.assertEqual(
            points,
            [
                geometry.TracePoint(-215, -70, False),
                geometry.TracePoint(-212, -73, True),
            ],
        )

    def test_decode_rejects_partial_point(self) -> None:
        """A corrupt chunk cannot silently produce a partial coordinate."""
        with self.assertRaisesRegex(ValueError, "Invalid trace points length"):
            geometry.decode_trace_chunk("compressed", lambda _: b"1234")

    def test_compact_svg_path(self) -> None:
        """Horizontal, vertical, diagonal and disconnected moves stay compact."""
        points = [
            geometry.TracePoint(10, 20, False),
            geometry.TracePoint(15, 20, True),
            geometry.TracePoint(15, 17, True),
            geometry.TracePoint(14, 16, True),
            geometry.TracePoint(20, 25, False),
        ]

        self.assertEqual(
            geometry.trace_points_to_svg_path(points),
            "M10 20h5v-3l-1 -1m6 9",
        )

    def test_accumulator_orders_and_replaces_chunks(self) -> None:
        """Out-of-order chunks do not create false path bridges."""
        trace = geometry.TraceAccumulator()
        first = [geometry.TracePoint(0, 0, False), geometry.TracePoint(1, 0, True)]
        second = [geometry.TracePoint(2, 0, True), geometry.TracePoint(3, 0, True)]

        trace.update(2, 4, second)
        self.assertEqual(trace.points, [])
        trace.update(0, 4, first)
        # start=0 begins a fresh response and intentionally drops stale chunks.
        self.assertEqual(trace.points, first)
        trace.update(2, 4, second)
        self.assertEqual(trace.points, first + second)
        self.assertTrue(trace.complete)

        replacement = [
            geometry.TracePoint(20, 0, True),
            geometry.TracePoint(30, 0, True),
        ]
        trace.update(2, 4, replacement)
        self.assertEqual(trace.points, first + replacement)
        self.assertEqual(trace.chunk_count, 2)

    def test_accumulator_resets_at_zero(self) -> None:
        """A new start=0 event removes the prior cleaning trace."""
        trace = geometry.TraceAccumulator()
        trace.update(
            0,
            2,
            [geometry.TracePoint(1, 1, False), geometry.TracePoint(2, 2, True)],
        )

        trace.update(0, 0, [])

        self.assertEqual(trace.points, [])
        self.assertEqual(trace.total, 0)
        self.assertEqual(trace.chunk_count, 0)
        self.assertTrue(trace.complete)

    def test_position_type_normalization(self) -> None:
        """Only stable public position names reach the sensor attributes."""
        self.assertEqual(
            geometry.normalize_position_type(PositionType.DEEBOT), "deebot"
        )
        self.assertEqual(
            geometry.normalize_position_type(PositionType.CHARGER), "charger"
        )
        self.assertEqual(geometry.normalize_position_type("robot"), "deebot")
        self.assertEqual(geometry.normalize_position_type("dock"), "charger")
        self.assertIsNone(geometry.normalize_position_type("unknown"))


if __name__ == "__main__":
    unittest.main()
