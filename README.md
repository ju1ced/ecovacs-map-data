# Ecovacs Map Data

Optional Home Assistant companion integration for
[Robot Vacuum Dashboard](https://github.com/ju1ced/robot-vacuum-dashboard).

The official Ecovacs integration receives room subset coordinates from
`deebot-client`, but currently exposes only room names and segment IDs. This
integration subscribes to the existing local event stream and publishes room
geometry, map rotation, positions and the live cleaning trace as a diagnostic
sensor. It does not make additional cloud calls and does not control the vacuum.

## Installation

1. Install this repository as an **Integration** through HACS.
2. Restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration**.
4. Select **Ecovacs Map Data** and confirm.

One `sensor.*_map_geometry` entity is added to every compatible Ecovacs vacuum.
Robot Vacuum Dashboard discovers this entity automatically.

## Published schema

Version 0.2.0 publishes schema version 2. All version 1 fields remain available:

- `rooms`, `maps`, `active_map_id`, `active_map_name` and `rotation`;
- normalized `positions`, using only `deebot` and `charger` types;
- `trace_path`, a compact SVG path containing the contiguous cleaning trace;
- `trace_point_count`, `trace_total_points`, `trace_chunk_count` and
  `trace_complete` for update diagnostics;
- `trace_transform`, currently `scale(0.2 -0.2)`, which converts the raw trace
  coordinates to the native Ecovacs SVG coordinate system.

The trace is decoded locally with `deebot-client`'s public
`decompress_base64_data` helper. Chunks are keyed by their `start` offset, so a
duplicate chunk replaces its predecessor and a missing chunk never creates an
incorrect straight line. An event with `start == 0` starts a fresh trace.

Consumers that inspect `schema_version` must accept version 2 before installing
this release. The original schema fields themselves remain unchanged.

## Requirements

- Home Assistant 2026.8 or newer.
- The official Ecovacs integration must already be configured.
- A modern `deebot-client` device with map and room support.
- Trace data depends on the device exposing `MapTraceEvent`; unsupported models
  continue to publish rooms and positions with an empty trace.

