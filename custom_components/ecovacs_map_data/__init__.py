"""Expose Ecovacs map geometry to Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import ECOVACS_DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ecovacs Map Data from a config entry."""
    ecovacs_entries = hass.config_entries.async_loaded_entries(ECOVACS_DOMAIN)
    if not ecovacs_entries:
        raise ConfigEntryNotReady("The Ecovacs integration is not loaded yet")

    async_migrate_companion_devices(hass, entry, ecovacs_entries)

    for ecovacs_entry in hass.config_entries.async_entries(ECOVACS_DOMAIN):
        entry.async_on_unload(
            ecovacs_entry.async_on_state_change(
                _reload_on_ecovacs_load(hass, entry, ecovacs_entry)
            )
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Ecovacs Map Data config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _reload_on_ecovacs_load(
    hass: HomeAssistant, entry: ConfigEntry, ecovacs_entry: ConfigEntry
) -> CALLBACK_TYPE:
    """Return a state listener that reloads this entry after an Ecovacs reload.

    The sensors keep references to the Ecovacs device objects. An Ecovacs
    reload replaces those objects, so this entry must reload as well. The
    listener reloads only this entry, which does not change the Ecovacs entry
    state, so it cannot cause a reload loop.
    """

    @callback
    def _async_on_state_change() -> None:
        """Schedule a reload when the Ecovacs entry is loaded again."""
        if (
            ecovacs_entry.state is ConfigEntryState.LOADED
            and entry.state is ConfigEntryState.LOADED
        ):
            _LOGGER.debug(
                "Ecovacs entry %s loaded again; reloading %s",
                ecovacs_entry.entry_id,
                entry.entry_id,
            )
            hass.config_entries.async_schedule_reload(entry.entry_id)

    return _async_on_state_change


@callback
def async_migrate_companion_devices(
    hass: HomeAssistant, entry: ConfigEntry, ecovacs_entries: list[ConfigEntry]
) -> None:
    """Move sensors from companion-owned devices to the Ecovacs devices.

    Version 0.2.0 linked the sensor through DeviceInfo identifiers. Since Home
    Assistant 2026.9 a device belongs to a single config entry, so this became
    a separate "Ecovacs Map Data" device owned by this entry. Each of our
    entities on such a device moves to the Ecovacs device with the same
    identifier, and the companion device is then removed. A companion device
    without a matching Ecovacs device stays unchanged. A second run finds no
    companion devices and does nothing.
    """
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    for companion in dr.async_entries_for_config_entry(
        device_registry, entry.entry_id
    ):
        target = _find_ecovacs_device(device_registry, companion, ecovacs_entries)
        if target is None:
            _LOGGER.debug(
                "No Ecovacs device matches companion device %s; keeping it",
                companion.id,
            )
            continue
        for entity in er.async_entries_for_device(
            entity_registry, companion.id, include_disabled_entities=True
        ):
            if entity.config_entry_id == entry.entry_id:
                entity_registry.async_update_entity(
                    entity.entity_id, device_id=target.id
                )
        _LOGGER.debug(
            "Moved entities from companion device %s to Ecovacs device %s",
            companion.id,
            target.id,
        )
        device_registry.async_remove_device(companion.id)


def _find_ecovacs_device(
    device_registry: dr.DeviceRegistry,
    companion: dr.DeviceEntry,
    ecovacs_entries: list[ConfigEntry],
) -> dr.DeviceEntry | None:
    """Return the Ecovacs device that shares an identifier with the companion."""
    for identifier in companion.identifiers:
        if identifier[0] != ECOVACS_DOMAIN:
            continue
        for ecovacs_entry in ecovacs_entries:
            if device := device_registry.async_get_device_by_identifier(
                identifier, ecovacs_entry.entry_id
            ):
                return device
    return None
