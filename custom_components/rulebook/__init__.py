"""rulebook custom component."""

from __future__ import annotations

import logging

from google import genai

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import agents
from .const import DOMAIN, CONF_API_KEY
from .storage import async_read_parsed_rulebook
from .types import RulebookConfigEntry, RulebookContext

__all__ = [
    DOMAIN,
]

_LOGGER = logging.getLogger(__name__)


PLATFORMS: tuple[Platform] = (Platform.CONVERSATION,)


async def async_setup_entry(hass: HomeAssistant, entry: RulebookConfigEntry) -> bool:
    """Set up a config entry."""

    # Verify the rulebook can be parsed made available if it exists
    await async_read_parsed_rulebook(hass)

    # Register all agents
    llm_agent = await agents.async_create(hass, entry)
    client = genai.Client(api_key=entry.options[CONF_API_KEY])
    entry.runtime_data = RulebookContext(
        agent=llm_agent,
        client=client,
    )

    await hass.config_entries.async_forward_entry_setups(
        entry,
        platforms=PLATFORMS,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RulebookConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
