"""Module for agents."""

import logging
from collections.abc import Callable

from google.adk.agents import BaseAgent, LlmAgent

from homeassistant.core import HomeAssistant

from custom_components.rulebook.const import RULEBOOK_AGENT_ID
from custom_components.rulebook.types import RulebookConfigEntry

from .const import AGENT_MODEL
from .rulebook_parser_agent import (
    async_create_agent as async_create_rulebook_parser_agent,
)
from .area_agent import async_create_agent as async_create_area_agent
from .person_agent import (
    async_create_agent as async_create_person_agent,
)
from .location_agent import (
    async_create_agent as async_create_location_agent,
)

_LOGGER = logging.getLogger(__name__)

_AGENT_FACTORIES: list[Callable[[HomeAssistant, RulebookConfigEntry], BaseAgent]] = [
    async_create_rulebook_parser_agent,
    async_create_area_agent,
    async_create_person_agent,
    async_create_location_agent,
]


async def async_create(
    hass: HomeAssistant, config_entry: RulebookConfigEntry
) -> BaseAgent:
    """Register all agents using the agent framework."""
    _LOGGER.debug("Registering Rulebook agents with ID %s", RULEBOOK_AGENT_ID)

    sub_agents_instances = [factory(hass, config_entry) for factory in _AGENT_FACTORIES]

    return LlmAgent(
        name="Coordinator",
        model=AGENT_MODEL,
        description="I coordinate greetings and tasks, including rulebook parsing, area, person, and location management. After parsing the rulebook, review the output and determine if there were any significant changes that other sub-agents need to be made aware of. If so, inform the relevant sub-agents to take appropriate actions.",
        sub_agents=sub_agents_instances,
    )
