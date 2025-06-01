"""Module for agents."""

import logging

from google.adk.agents import LlmAgent

from homeassistant.core import HomeAssistant

from custom_components.rulebook.const import RULEBOOK_AGENT_ID
from custom_components.rulebook.types import RulebookConfigEntry

from . import location_agent, rulebook_parser_agent
from .const import AGENT_MODEL

_LOGGER = logging.getLogger(__name__)

_AGENT_FACTORIES = [
    location_agent.async_create_agent,
    rulebook_parser_agent.async_create_agent,
]


async def async_create(
    hass: HomeAssistant, config_entry: RulebookConfigEntry
) -> LlmAgent:
    """Register all agents using the agent framework."""
    _LOGGER.debug("Registering Rulebook agents with ID %s", RULEBOOK_AGENT_ID)
    # Ensure all agents are created by calling the functions in _AGENT_FACTORIES
    # The LlmAgent constructor expects a list of agent instances.
    sub_agents_instances = [factory(hass, config_entry) for factory in _AGENT_FACTORIES]

    return LlmAgent(
        name="Coordinator",
        model=AGENT_MODEL,
        description="I coordinate greetings and tasks, including rulebook parsing.",  # Updated description
        sub_agents=sub_agents_instances,
    )
