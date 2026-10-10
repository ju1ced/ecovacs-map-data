"""Ecovacs map geometry sensor."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from deebot_client.events import CachedMapInfoEvent, MapTraceEvent, RoomsEvent
from deebot_client.events.map import PositionsEvent
from deebot_client.rs.util import decompress_base64_data

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ECOVACS_DOMAIN
from .geometry import (
    TraceAccumulator,
    decode_trace_chunk,
    normalize_position_type,
    parse_coordinates,
    rotation_degrees,
    trace_points_to_svg_path,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create geometry sensors for modern Ecovacs devices with map support."""
    device_registry = dr.async_get(hass)
    entities: list[EcovacsMapGeometrySensor] = []
    for ecovacs_entry in hass.config_entries.async_loaded_entries(ECOVACS_DOMAIN):
        controller = getattr(ecovacs_entry, "runtime_data", None)
        for device in getattr(controller, "devices", []):
            capabilities = getattr(device, "capabilities", None)
            if getattr(capabilities, "map", None) is None:
                continue
            did = device.device_info["did"]
            device_entry = device_registry.async_get_device_by_identifier(
                (ECOVACS_DOMAIN, did), ecovacs_entry.entry_id
            )
            if device_entry is None:
                _LOGGER.debug("Skipping Ecovacs device %s without a device entry", did)
                continue
            entity = EcovacsMapGeometrySensor(device)
            entity.device_entry = device_entry
            entities.append(entity)
    async_add_entities(entities)


class EcovacsMapGeometrySensor(SensorEntity):
    """Publish room polygons, map rotation and live positions."""

    _attr_has_entity_name = True
    _attr_translation_key = "map_geometry"
    _attr_icon = "mdi:vector-polygon"
    _attr_should_poll = False
    _unrecorded_attributes = frozenset(
        {"rooms", "maps", "positions", "trace_path", "trace_transform"}
    )

    def __init__(self, device: Any) -> None:
        """Initialize the geometry sensor."""
        self._device = device
        self._rooms: list[dict[str, Any]] = []
        self._maps: list[dict[str, Any]] = []
        self._positions: list[dict[str, Any]] = []
        self._trace = TraceAccumulator()
        self._attr_unique_id = f"{device.device_info['did']}_map_geometry"

    @property
    def native_value(self) -> int:
        """Return the number of available rooms."""
        return len(self._rooms)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return geometry in a frontend-friendly schema."""
        active_map = next((item for item in self._maps if item["active"]), None)
        trace_points = self._trace.points
        return {
            "schema_version": 2,
            "rooms": self._rooms,
            "maps": self._maps,
            "active_map_id": active_map["id"] if active_map else None,
            "active_map_name": active_map["name"] if active_map else None,
            "rotation": active_map["rotation"] if active_map else 0,
            "positions": self._positions,
            "trace_path": trace_points_to_svg_path(trace_points),
            "trace_point_count": len(trace_points),
            "trace_total_points": self._trace.total,
            "trace_chunk_count": self._trace.chunk_count,
            "trace_complete": self._trace.complete,
            "trace_transform": "scale(0.2 -0.2)",
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to deebot-client's existing event stream."""
        await super().async_added_to_hass()

        async def on_rooms(event: RoomsEvent) -> None:
            self._rooms = [
                {
                    "id": room.id,
                    "name": room.name,
                    "coordinates": parse_coordinates(room.coordinates),
                }
                for room in event.rooms
            ]
            self.async_write_ha_state()

        async def on_maps(event: CachedMapInfoEvent) -> None:
            self._maps = [
                {
                    "id": map_info.id,
                    "name": map_info.name,
                    "active": map_info.using,
                    "rotation": rotation_degrees(map_info.angle),
                }
                for map_info in event.maps
            ]
            self.async_write_ha_state()

        async def on_positions(event: PositionsEvent) -> None:
            positions: list[dict[str, Any]] = []
            for position in event.positions:
                if (position_type := normalize_position_type(position.type)) is None:
                    _LOGGER.debug(
                        "Ignoring unknown map position type: %s", position.type
                    )
                    continue
                positions.append(
                    {
                        "type": position_type,
                        "x": position.x,
                        "y": position.y,
                        "angle": position.a,
                    }
                )
            self._positions = positions
            self.async_write_ha_state()

        async def on_trace(event: MapTraceEvent) -> None:
            try:
                points = decode_trace_chunk(event.data, decompress_base64_data)
                self._trace.update(event.start, event.total, points)
            except (TypeError, ValueError) as err:
                _LOGGER.warning(
                    "Unable to decode Ecovacs trace chunk at %s/%s: %s",
                    event.start,
                    event.total,
                    err,
                )
                return
            self.async_write_ha_state()

        events = self._device.events
        self.async_on_remove(events.subscribe(RoomsEvent, on_rooms))
        self.async_on_remove(events.subscribe(CachedMapInfoEvent, on_maps))
        self.async_on_remove(events.subscribe(PositionsEvent, on_positions))
        self.async_on_remove(events.subscribe(MapTraceEvent, on_trace))
        events.request_refresh(CachedMapInfoEvent)
        events.request_refresh(RoomsEvent)
        events.request_refresh(PositionsEvent)
        events.request_refresh(MapTraceEvent)
