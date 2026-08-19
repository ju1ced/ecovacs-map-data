"""Pure geometry helpers for Ecovacs map data."""

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


@dataclass(frozen=True, slots=True)
class TracePoint:
    """A decoded Ecovacs cleaning trace point."""

    x: int
    y: int
    connected: bool


class TraceAccumulator:
    """Collect independently delivered trace chunks in point order."""

    def __init__(self) -> None:
        """Initialize an empty trace."""
        self._chunks: dict[int, tuple[TracePoint, ...]] = {}
        self._total = 0

    @property
    def total(self) -> int:
        """Return the point count announced by the vacuum."""
        return self._total

    @property
    def chunk_count(self) -> int:
        """Return the number of retained chunks."""
        return len(self._chunks)

    @property
    def points(self) -> list[TracePoint]:
        """Return the contiguous trace prefix, without bridging missing chunks."""
        points: list[TracePoint] = []
        expected_start = 0
        for start, chunk in sorted(self._chunks.items()):
            if start != expected_start:
                break
            points.extend(chunk)
            expected_start += len(chunk)
        return points

    @property
    def complete(self) -> bool:
        """Return whether all announced trace points are available."""
        return len(self.points) >= self._total

    def update(
        self, start: int, total: int, points: Iterable[TracePoint]
    ) -> None:
        """Insert or replace a trace chunk, resetting at the first chunk."""
        if start < 0 or total < 0:
            raise ValueError("Trace offsets and totals must not be negative")

        chunk = tuple(points)
        if start == 0:
            self._chunks.clear()
        self._total = total

        if chunk:
            self._chunks[start] = chunk

        # A shorter total means stale tail chunks must not survive.
        self._chunks = {
            chunk_start: chunk_points
            for chunk_start, chunk_points in self._chunks.items()
            if chunk_start < total
        }


def decode_trace_chunk(
    value: str, decompressor: Callable[[str], bytes]
) -> list[TracePoint]:
    """Decode an Ecovacs base64-compressed trace chunk."""
    if not value.strip():
        return []

    raw = decompressor(value)
    if len(raw) % 5:
        raise ValueError("Invalid trace points length")

    return [
        TracePoint(
            x=int.from_bytes(raw[index : index + 2], "little", signed=True),
            y=int.from_bytes(raw[index + 2 : index + 4], "little", signed=True),
            connected=(raw[index + 4] & 0x80) == 0,
        )
        for index in range(0, len(raw), 5)
    ]


def trace_points_to_svg_path(points: Iterable[TracePoint]) -> str | None:
    """Build a compact relative SVG path from decoded trace points."""
    trace = list(points)
    if len(trace) < 2:
        return None

    path = [f"M{trace[0].x} {trace[0].y}"]
    previous = trace[0]
    for point in trace[1:]:
        x = point.x - previous.x
        y = point.y - previous.y
        previous = point
        if x == 0 and y == 0:
            continue
        if not point.connected:
            path.append(f"m{x} {y}")
        elif x == 0:
            path.append(f"v{y}")
        elif y == 0:
            path.append(f"h{x}")
        else:
            path.append(f"l{x} {y}")
    return "".join(path)


def normalize_position_type(value: Any) -> str | None:
    """Normalize deebot-client position enum variants for consumers."""
    name = getattr(value, "name", str(value)).lower()
    if "charger" in name or "station" in name or "dock" in name:
        return "charger"
    if "deebot" in name or "vacuum" in name or "robot" in name:
        return "deebot"
    return None


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
