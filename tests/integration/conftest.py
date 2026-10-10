"""Shared fixtures for the Home Assistant integration tests."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_integration,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.ecovacs_map_data.const import DOMAIN, ECOVACS_DOMAIN

DEVICE_DID = "E0000001234567890001"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load the integration from custom_components in every test."""


def make_fake_device(did: str = DEVICE_DID) -> SimpleNamespace:
    """Return a stand-in for a deebot-client device with map support."""
    events = MagicMock()
    events.subscribe.side_effect = lambda *_args: MagicMock()
    return SimpleNamespace(
        device_info={"did": did},
        capabilities=SimpleNamespace(map=object()),
        events=events,
    )


@pytest.fixture
def unique_id() -> str:
    """Return the sensor unique ID for the fake device."""
    return f"{DEVICE_DID}_map_geometry"


@pytest.fixture
def device_factory() -> Callable[[], SimpleNamespace]:
    """Return a factory for fake Ecovacs devices."""
    return make_fake_device


@pytest.fixture
def fake_device() -> SimpleNamespace:
    """Return one fake Ecovacs device."""
    return make_fake_device()


@pytest.fixture
def ecovacs_entry(hass: HomeAssistant, fake_device: SimpleNamespace) -> MockConfigEntry:
    """Return a loaded Ecovacs config entry without loading the real integration."""
    mock_integration(hass, MockModule(ECOVACS_DOMAIN))
    entry = MockConfigEntry(domain=ECOVACS_DOMAIN, title="Ecovacs")
    entry.add_to_hass(hass)
    entry.runtime_data = SimpleNamespace(devices=[fake_device])
    entry.mock_state(hass, ConfigEntryState.LOADED)
    return entry


@pytest.fixture
def ecovacs_device(
    hass: HomeAssistant, ecovacs_entry: MockConfigEntry
) -> dr.DeviceEntry:
    """Return the device-registry entry that the Ecovacs integration owns."""
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=ecovacs_entry.entry_id,
        identifiers={(ECOVACS_DOMAIN, DEVICE_DID)},
        manufacturer="Ecovacs",
        name="Vacuum",
    )


@pytest.fixture
def map_data_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return the companion config entry, added but not set up."""
    entry = MockConfigEntry(domain=DOMAIN, title="Ecovacs Map Data", unique_id=DOMAIN)
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def setup_map_data(
    hass: HomeAssistant, map_data_entry: MockConfigEntry
) -> Callable[[], Any]:
    """Return a coroutine function that sets up the companion entry."""

    async def _setup() -> bool:
        """Set up the companion entry and wait until it settles."""
        result = await hass.config_entries.async_setup(map_data_entry.entry_id)
        await hass.async_block_till_done()
        return result

    return _setup
