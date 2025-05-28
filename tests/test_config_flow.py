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
