# Ecovacs Map Data

Optional Home Assistant companion integration for
[Robot Vacuum Dashboard](https://github.com/ju1ced/robot-vacuum-dashboard).

The official Ecovacs integration receives room subset coordinates from
`deebot-client`, but currently exposes only room names and segment IDs. This
integration subscribes to the existing local event stream and publishes room
geometry, map rotation and positions as a diagnostic sensor. It does not make
additional cloud calls and does not control the vacuum.

## Installation

1. Install this repository as an **Integration** through HACS.
2. Restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration**.
4. Select **Ecovacs Map Data** and confirm.

One `sensor.*_map_geometry` entity is added to every compatible Ecovacs vacuum.
Robot Vacuum Dashboard discovers this entity automatically.

## Requirements

- Home Assistant 2026.8 or newer.
- The official Ecovacs integration must already be configured.
- A modern `deebot-client` device with map and room support.

