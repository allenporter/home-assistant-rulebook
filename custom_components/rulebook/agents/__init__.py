"""Module for agents."""

import logging
from collections.abc import Callable  # Added import

from google.adk.agents import LlmAgent

from homeassistant.core import HomeAssistant

from custom_components.rulebook.const import RULEBOOK_AGENT_ID
from custom_components.rulebook.types import RulebookConfigEntry

from .const import AGENT_MODEL
from .rulebook_parser_agent import (
    async_create_agent as async_create_rulebook_parser_agent,
)
from .smart_home_rule_parser_agent import (
    async_create_agent as async_create_smart_home_rule_parser_agent,
)

_LOGGER = logging.getLogger(__name__)

_AGENT_FACTORIES: list[Callable[[HomeAssistant, RulebookConfigEntry], LlmAgent]] = [
    async_create_rulebook_parser_agent,
    async_create_smart_home_rule_parser_agent,  # Added factory
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
