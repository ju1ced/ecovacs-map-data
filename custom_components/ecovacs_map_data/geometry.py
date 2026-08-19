"""Pure geometry helpers for Ecovacs map data."""

import re
from typing import Any

_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


def parse_coordinates(value: str) -> list[list[float]]:
    """Parse an Ecovacs coordinate string into x/y pairs."""
    numbers = [float(item) for item in _NUMBER_PATTERN.findall(value)]
    return [numbers[index : index + 2] for index in range(0, len(numbers) - 1, 2)]


def rotation_degrees(angle: Any) -> int:
    """Convert deebot-client's RotationAngle to degrees."""
    name = getattr(angle, "name", str(angle)).upper()
    match = re.search(r"(?:DEG_)?(0|90|180|270)$", name)
    if match:
        return int(match.group(1))
    return 0
