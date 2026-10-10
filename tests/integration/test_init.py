"""Tests for device linking, migration, recorder exclusion and reloads."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from types import SimpleNamespace

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_integration,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.ecovacs_map_data.const import DOMAIN, ECOVACS_DOMAIN
from custom_components.ecovacs_map_data.sensor import EcovacsMapGeometrySensor

type SetupMapData = Callable[[], Awaitable[bool]]


async def test_sensor_attaches_to_ecovacs_device(
    hass: HomeAssistant,
    ecovacs_device: dr.DeviceEntry,
    map_data_entry: MockConfigEntry,
    setup_map_data: SetupMapData,
    fake_device: SimpleNamespace,
    unique_id: str,
) -> None:
    """A new sensor joins the Ecovacs device and creates no device of its own."""
    assert await setup_map_data()
    assert map_data_entry.state is ConfigEntryState.LOADED

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id == "sensor.vacuum_map_geometry"
    entity = entity_registry.async_get(entity_id)
    assert entity is not None
    assert entity.device_id == ecovacs_device.id
    assert entity.translation_key == "map_geometry"

    device_registry = dr.async_get(hass)
    assert not dr.async_entries_for_config_entry(
        device_registry, map_data_entry.entry_id
    )

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "0"
    assert state.attributes["schema_version"] == 2
    assert fake_device.events.subscribe.call_count == 4


async def test_device_without_registry_entry_is_skipped(
    hass: HomeAssistant,
    ecovacs_entry: MockConfigEntry,
    map_data_entry: MockConfigEntry,
    setup_map_data: SetupMapData,
    unique_id: str,
) -> None:
    """No sensor and no device are created when the Ecovacs device is missing."""
    assert await setup_map_data()

    assert er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id) is None
    assert not dr.async_entries_for_config_entry(
        dr.async_get(hass), map_data_entry.entry_id
    )


async def test_companion_device_migration(
    hass: HomeAssistant,
    ecovacs_device: dr.DeviceEntry,
    map_data_entry: MockConfigEntry,
    setup_map_data: SetupMapData,
    unique_id: str,
) -> None:
    """An entity on the split companion device moves to the Ecovacs device."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    companion = device_registry.async_get_or_create(
        config_entry_id=map_data_entry.entry_id,
        identifiers=set(ecovacs_device.identifiers),
        name="Ecovacs Map Data",
    )
    assert companion.id != ecovacs_device.id
    registered = entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        unique_id,
        config_entry=map_data_entry,
        device_id=companion.id,
        suggested_object_id="ecovacs_map_data_map_geometry",
    )

    assert await setup_map_data()

    entity = entity_registry.async_get(registered.entity_id)
    assert entity is not None
    assert entity.entity_id == "sensor.ecovacs_map_data_map_geometry"
    assert entity.device_id == ecovacs_device.id
    assert device_registry.async_get(companion.id) is None
    assert device_registry.async_get(ecovacs_device.id) is not None
    assert hass.states.get(entity.entity_id) is not None

    # A second setup finds nothing to migrate and keeps the link.
    assert await hass.config_entries.async_reload(map_data_entry.entry_id)
    await hass.async_block_till_done()
    entity = entity_registry.async_get(registered.entity_id)
    assert entity is not None
    assert entity.device_id == ecovacs_device.id
    assert not dr.async_entries_for_config_entry(
        device_registry, map_data_entry.entry_id
    )


async def test_companion_device_without_match_is_kept(
    hass: HomeAssistant,
    ecovacs_entry: MockConfigEntry,
    map_data_entry: MockConfigEntry,
    setup_map_data: SetupMapData,
) -> None:
    """A companion device with no Ecovacs counterpart stays unchanged."""
    device_registry = dr.async_get(hass)
    companion = device_registry.async_get_or_create(
        config_entry_id=map_data_entry.entry_id,
        identifiers={(ECOVACS_DOMAIN, "unknown-did")},
    )

    assert await setup_map_data()

    assert device_registry.async_get(companion.id) is not None


def test_unrecorded_attributes() -> None:
    """Large attributes are excluded from the recorder."""
    assert EcovacsMapGeometrySensor._unrecorded_attributes == frozenset(
        {"rooms", "maps", "positions", "trace_path", "trace_transform"}
    )


async def test_not_ready_without_loaded_ecovacs(
    hass: HomeAssistant,
    map_data_entry: MockConfigEntry,
    setup_map_data: SetupMapData,
) -> None:
    """Setup is retried while no Ecovacs entry is loaded."""
    mock_integration(hass, MockModule(ECOVACS_DOMAIN))
    ecovacs_entry = MockConfigEntry(domain=ECOVACS_DOMAIN, title="Ecovacs")
    ecovacs_entry.add_to_hass(hass)
    ecovacs_entry.mock_state(hass, ConfigEntryState.SETUP_RETRY)

    await setup_map_data()

    assert map_data_entry.state is ConfigEntryState.SETUP_RETRY


async def test_reload_after_ecovacs_reload(
    hass: HomeAssistant,
    ecovacs_entry: MockConfigEntry,
    ecovacs_device: dr.DeviceEntry,
    map_data_entry: MockConfigEntry,
    setup_map_data: SetupMapData,
    fake_device: SimpleNamespace,
    device_factory: Callable[[], SimpleNamespace],
) -> None:
    """A new Ecovacs load makes the sensor subscribe to the new device object."""
    assert await setup_map_data()
    assert fake_device.events.subscribe.call_count == 4

    ecovacs_entry.mock_state(hass, ConfigEntryState.UNLOAD_IN_PROGRESS)
    ecovacs_entry.mock_state(hass, ConfigEntryState.NOT_LOADED)
    await hass.async_block_till_done()
    assert map_data_entry.state is ConfigEntryState.LOADED
    assert fake_device.events.subscribe.call_count == 4

    new_device = device_factory()
    ecovacs_entry.runtime_data = SimpleNamespace(devices=[new_device])
    ecovacs_entry.mock_state(hass, ConfigEntryState.SETUP_IN_PROGRESS)
    ecovacs_entry.mock_state(hass, ConfigEntryState.LOADED)
    await hass.async_block_till_done()

    assert map_data_entry.state is ConfigEntryState.LOADED
    assert new_device.events.subscribe.call_count == 4
    assert fake_device.events.subscribe.call_count == 4

    # The reload re-registers one listener; no further reloads follow.
    await hass.async_block_till_done()
    assert new_device.events.subscribe.call_count == 4
