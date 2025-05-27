"""Module for agents."""

from google.adk.agents import LlmAgent

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.rulebook.const import RULEBOOK_AGENT_ID

from . import location_agent

_AGENT_FACTORIES = [
    location_agent.async_create_agent,
]


async def async_register(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Register all agents using the agent framework."""

    coordinator = LlmAgent(
        name="Coordinator",
        model=RULEBOOK_AGENT_ID,
        description="I coordinate greetings and tasks.",
        sub_agents=[func(hass, config_entry) for func in _AGENT_FACTORIES],
    )
    config_entry.runtime_data = {}
    config_entry.runtime_data["agent"] = coordinator
