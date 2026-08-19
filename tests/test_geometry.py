"""Tests for Ecovacs coordinate parsing."""

from enum import Enum, auto
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "ecovacs_map_data"
    / "geometry.py"
)
SPEC = importlib.util.spec_from_file_location("ecovacs_map_geometry", MODULE_PATH)
assert SPEC and SPEC.loader
geometry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(geometry)


class RotationAngle(Enum):
    """Small stand-in for deebot-client's Rust enum."""

    DEG_0 = auto()
    DEG_90 = auto()
    DEG_180 = auto()
    DEG_270 = auto()


class GeometryTests(unittest.TestCase):
    """Verify the standalone coordinate helpers."""

    def test_parse_json_like_coordinates(self) -> None:
        """Coordinate arrays are converted to x/y pairs."""
        self.assertEqual(
            geometry.parse_coordinates("[-3900,668,-2133,668]"),
            [[-3900.0, 668.0], [-2133.0, 668.0]],
        )

    def test_parse_quoted_and_decimal_coordinates(self) -> None:
        """Quoted values, blanks and decimals remain usable."""
        self.assertEqual(
            geometry.parse_coordinates("['12023', '1979', '', 12135.5, -6720]"),
            [[12023.0, 1979.0], [12135.5, -6720.0]],
        )

    def test_rotation_enum_conversion(self) -> None:
        """All supported rotations convert to numeric degrees."""
        self.assertEqual(
            [geometry.rotation_degrees(value) for value in RotationAngle],
            [0, 90, 180, 270],
        )


if __name__ == "__main__":
    unittest.main()
