"""Tests for the rulebook component."""

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import TEST_AGENT, FakeAgent


@pytest.mark.parametrize(
    ("mock_entities"),
    [
        ({Platform.CONVERSATION: [FakeAgent(TEST_AGENT)]}),
    ],
)
async def test_init(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Test that a config entry is setup."""

    assert config_entry.state is ConfigEntryState.LOADED
