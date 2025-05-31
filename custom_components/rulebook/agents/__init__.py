"""Module for agents."""

import logging

from google.adk.agents import LlmAgent

from homeassistant.core import HomeAssistant

from custom_components.rulebook.const import RULEBOOK_AGENT_ID
from custom_components.rulebook.types import RulebookConfigEntry

from . import location_agent

_LOGGER = logging.getLogger(__name__)

_AGENT_FACTORIES = [
    location_agent.async_create_agent,
]

# For now we're using the built in model.
# _MODEL_NAME = RULEBOOK_AGENT_ID
_MODEL_NAME = "gemini-2.5-pro-preview-05-06"

async def async_create(
    hass: HomeAssistant, config_entry: RulebookConfigEntry
) -> LlmAgent:
    """Register all agents using the agent framework."""
    _LOGGER.debug("Registering Rulebook agents with ID %s", RULEBOOK_AGENT_ID)
    return LlmAgent(
        name="Coordinator",
        model=_MODEL_NAME,
        description="I coordinate greetings and tasks.",
        sub_agents=[func(hass, config_entry) for func in _AGENT_FACTORIES],
    )
