"""Tests for the config flow."""

from unittest.mock import patch

import pytest

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.core import HomeAssistant

from custom_components.rulebook import DOMAIN
from custom_components.rulebook.const import CONF_RULEBOOK, CONF_API_KEY

from .conftest import (
    TEST_RULEBOOK,
    TEST_API_KEY,
)


@pytest.mark.parametrize(
    ("mock_entities"),
    [
        # ({"conversation": [FakeAgent(TEST_AGENT)]}),
        ({}),
    ],
)
async def test_config_flow(
    hass: HomeAssistant,
) -> None:
    """Test full config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") is None
    with (
        patch("google.genai.models.AsyncModels.list"),
        patch(
            f"custom_components.{DOMAIN}.async_setup_entry", return_value=True
        ) as mock_setup,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                # CONF_AGENT_ID: TEST_AGENT,
                CONF_API_KEY: TEST_API_KEY,
                CONF_RULEBOOK: TEST_RULEBOOK,
            },
        )
        await hass.async_block_till_done()

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("title") == "Rulebook Agent"
    assert result.get("data") == {}
    assert result.get("options") == {
        # CONF_AGENT_ID: TEST_AGENT,
        CONF_API_KEY: TEST_API_KEY,
        CONF_RULEBOOK: TEST_RULEBOOK,
    }
    assert len(mock_setup.mock_calls) == 1


async def test_options_flow(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
) -> None:
    """Test options flow."""
    assert config_entry.state is config_entries.ConfigEntryState.LOADED

    # Initiate the options flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] is None

    # Check that the form is pre-filled with the current rulebook
    schema = result["data_schema"]
    assert schema
    defaults = schema({})
    assert defaults[CONF_RULEBOOK] == TEST_RULEBOOK

    # Simulate user input with an updated rulebook
    updated_rulebook_text = "This is the updated rulebook text."
    with patch(
        f"custom_components.{DOMAIN}.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_RULEBOOK: updated_rulebook_text},
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == {  # Options are stored in result2.data for options flow
        CONF_API_KEY: TEST_API_KEY,  # API key should remain from initial options
        CONF_RULEBOOK: updated_rulebook_text,
    }

    # Verify the config entry options have been updated
    assert config_entry.options[CONF_RULEBOOK] == updated_rulebook_text
    assert (
        config_entry.options[CONF_API_KEY] == TEST_API_KEY
    )  # Ensure API key is preserved

    # Ensure setup is called again after options update
    assert len(mock_setup_entry.mock_calls) == 1
