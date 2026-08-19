"""Ecovacs map geometry sensor."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from deebot_client.events import CachedMapInfoEvent, RoomsEvent
from deebot_client.events.map import PositionsEvent

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ECOVACS_DOMAIN
from .geometry import parse_coordinates, rotation_degrees


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create geometry sensors for modern Ecovacs devices with map support."""
    entities: list[EcovacsMapGeometrySensor] = []
    for ecovacs_entry in hass.config_entries.async_entries(ECOVACS_DOMAIN):
        controller = getattr(ecovacs_entry, "runtime_data", None)
        for device in getattr(controller, "devices", []):
            if getattr(device.capabilities, "map", None) is not None:
                entities.append(EcovacsMapGeometrySensor(device))
    async_add_entities(entities)


class EcovacsMapGeometrySensor(SensorEntity):
    """Publish room polygons, map rotation and live positions."""

    _attr_has_entity_name = True
    _attr_name = "Map geometry"
    _attr_icon = "mdi:vector-polygon"
    _attr_should_poll = False

    def __init__(self, device: Any) -> None:
        """Initialize the geometry sensor."""
        self._device = device
        self._rooms: list[dict[str, Any]] = []
        self._maps: list[dict[str, Any]] = []
        self._positions: list[dict[str, Any]] = []
        device_info = device.device_info
        self._attr_unique_id = f"{device_info['did']}_map_geometry"
        self._attr_device_info = DeviceInfo(
            identifiers={(ECOVACS_DOMAIN, device_info["did"])},
        )

    @property
    def native_value(self) -> int:
        """Return the number of available rooms."""
        return len(self._rooms)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return geometry in a frontend-friendly schema."""
        active_map = next((item for item in self._maps if item["active"]), None)
        return {
            "schema_version": 1,
            "rooms": self._rooms,
            "maps": self._maps,
            "active_map_id": active_map["id"] if active_map else None,
            "active_map_name": active_map["name"] if active_map else None,
            "rotation": active_map["rotation"] if active_map else 0,
            "positions": self._positions,
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
            self._positions = [
                {
                    "type": getattr(position.type, "name", str(position.type)).lower(),
                    "x": position.x,
                    "y": position.y,
                    "angle": position.a,
                }
                for position in event.positions
            ]
            self.async_write_ha_state()

        events = self._device.events
        self.async_on_remove(events.subscribe(RoomsEvent, on_rooms))
        self.async_on_remove(events.subscribe(CachedMapInfoEvent, on_maps))
        self.async_on_remove(events.subscribe(PositionsEvent, on_positions))
        events.request_refresh(CachedMapInfoEvent)
        events.request_refresh(RoomsEvent)
        events.request_refresh(PositionsEvent)
