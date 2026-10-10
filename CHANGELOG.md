# Changelog

## 0.3.0

- Attach the map geometry sensor to the existing Ecovacs vacuum device through
  `entity.device_entry`. Home Assistant 2026.9 gives each device a single
  config entry, so the identifier-based `DeviceInfo` link created a separate
  "Ecovacs Map Data" device.
- Migrate existing sensors from that separate device to the Ecovacs device and
  remove the empty companion device. Entity IDs and unique IDs are unchanged.
- Exclude `rooms`, `maps`, `positions`, `trace_path` and `trace_transform`
  from recorder history.
- Reload automatically when the Ecovacs integration reloads, so the sensor
  keeps receiving events from the new device objects.
- Retry setup until the Ecovacs integration is loaded.
- Translate the sensor name ("Map geometry", "Kaartgeometrie").
- Add Home Assistant integration tests and a CI workflow with hassfest, HACS
  validation and tests.

## 0.2.0

- Publish backwards-compatible map geometry schema version 2.
- Add a compact SVG cleaning trace assembled from `MapTraceEvent` chunks.
- Include trace completeness and point-count metadata for renderers.
- Normalize live positions to stable `deebot` and `charger` type names.
- Preserve version 1 room, map, rotation and position fields.

## 0.1.0

- Initial room geometry, map rotation and live position sensor.
