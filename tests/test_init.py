"""Tests for the rulebook component."""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_init(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Test that a config entry is setup."""

    assert config_entry.state is ConfigEntryState.LOADED
